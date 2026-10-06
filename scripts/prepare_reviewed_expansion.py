"""Apply explicitly reviewed expansion decisions; preserve sources and earlier datasets."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, shutil, zipfile
import cv2
import yaml

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / 'configs/review/expansion-v3-candidates.json'
OUT = ROOT / 'data/reviewed_pilot/expansion_v3'
PPE_OK = {1, 3, 7, 9, 12, *range(13, 27)}
LOG_OK = {8, 9, 11, 14, 15, 16, 18, 19, 21, 22, 30, 31, 32, 33, 34, 35, 36}
# Coordinates are XYXY on the reviewed 960x540 overlay, not original pixels.
DRIVERS = {11: [208, 246, 238, 312], 16: [694, 245, 719, 284],
           22: [252, 216, 294, 268]}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if OUT.exists():
        raise SystemExit(f'Existing output protected: {OUT}')
    decisions = {}
    candidates = json.loads(CANDIDATES.read_text())
    for kind, accepted in [('ppe', PPE_OK), ('logistics', LOG_OK)]:
        rows = candidates[kind]
        for index, row in enumerate(rows, 1):
            row['expansion_review_id'] = index
            row['training_eligible'] = index in accepted
            row['review_method'] = 'visual audit of 960x540 full-frame annotation overlay'
            row['reason'] = ('visible labels accepted; corrections recorded separately'
                             if index in accepted else
                             'held: ambiguous/occluded head or incomplete/loose object labels; requires further review')
            if kind == 'ppe':
                date = row['metadata']['date'][:10]
                row['split'] = ('test' if date in {'2023-09-07', '2023-09-20'} else
                                'val' if date in {'2023-10-12', '2023-10-13'} else 'train')
                row['split_group'] = row['metadata']['location'] + '/' + date
                row['corrected_boxes'] = list(row['boxes'])
                if index == 21:
                    row['corrected_boxes'].append([0, 1758, 284, 1880, 424])
                    row['reason'] = 'added omitted orange hardhat/head on right-hand worker'
            else:
                row['split_group'] = row['site']
                row['corrected_boxes'] = list(row['boxes'])
                if index in DRIVERS:
                    x1, y1, x2, y2 = DRIVERS[index]
                    row['corrected_boxes'].append([0, x1*2, y1*2, (x2-x1)*2, (y2-y1)*2])
                    row['reason'] = 'added omitted visible forklift driver'
                if index == 36:
                    # Last box labels empty pavement as person; keep actual operator.
                    assert len(row['boxes']) == 3 and row['boxes'][-1][0] == 0
                    row['corrected_boxes'] = row['boxes'][:-1]
                    row['reason'] = 'removed person box on empty pavement'
        decisions[kind] = rows
    # Separate output; existing approved sources keep their original split.
    for kind, base in [('ppe', 'ppe'), ('logistics', 'logistics_v2')]:
        target = OUT / kind
        shutil.copytree(ROOT / 'data/reviewed_pilot' / base, target)
        old = json.loads((target / 'manifest.json').read_text())
        for row in decisions[kind]:
            if not row['training_eligible']:
                continue
            split = row['split']
            name = ('smartyard_' + Path(row['image']).name if kind == 'ppe'
                    else row['stem'] + '.jpg')
            image_path = target / split / 'images' / name
            if image_path.exists():
                raise ValueError(f'Duplicate source: {name}')
            image_path.parent.mkdir(parents=True, exist_ok=True)
            if kind == 'ppe':
                shutil.copy2(row['image'], image_path)
            else:
                with zipfile.ZipFile(row['source_zip']) as archive:
                    image_path.write_bytes(archive.read(row['image_member']))
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f'Undecodable: {image_path}')
            h, w = image.shape[:2]
            if (w, h) != (1920, 1080):
                raise ValueError(f'Unexpected resolution: {(w,h)}')
            lines = []
            for cls, x, y, a, b in row['corrected_boxes']:
                x2, y2 = (a, b) if kind == 'ppe' else (x+a, y+b)
                assert cls in {0, 1} and 0 <= x < x2 <= w and 0 <= y < y2 <= h
                lines.append(f'{cls} {(x+x2)/2/w:.8f} {(y+y2)/2/h:.8f} {(x2-x)/w:.8f} {(y2-y)/h:.8f}')
            label_path = target / split / 'labels' / (Path(name).stem + '.txt')
            label_path.parent.mkdir(parents=True, exist_ok=True)
            label_path.write_text('\n'.join(lines) + '\n')
            if kind == 'ppe':
                row['source_image'] = row['image']
            row['image'] = name
            row['image_sha256'] = digest(image_path)
            row['label_sha256'] = digest(label_path)
        merged = old + decisions[kind]
        (target / 'manifest.json').write_text(json.dumps(merged, ensure_ascii=False, indent=2))
        names = {0:'helmeted_head',1:'no_helmet_head'} if kind == 'ppe' else {0:'person',1:'forklift'}
        (target / 'dataset.yaml').write_text(yaml.safe_dump({'path':str(target),'train':'train/images','val':'val/images','test':'test/images','names':names}))
        # Validate all merged pairs, labels, exact content separation and group separation.
        hashes, groups = defaultdict(set), defaultdict(set)
        counts = Counter()
        for row in merged:
            if row['training_eligible']:
                group = row.get('split_group', row.get('group'))
                if group:
                    groups[group].add(row['split'])
        for split in ['train','val','test']:
            for path in (target/split/'images').glob('*'):
                img = cv2.imread(str(path)); assert img is not None
                label = target/split/'labels'/(path.stem+'.txt'); assert label.exists()
                for line in label.read_text().splitlines():
                    cls, x, y, w, h = map(float, line.split())
                    assert cls in names and w > 0 and h > 0
                    assert -1e-6 <= x-w/2 <= x+w/2 <= 1+1e-6
                    assert -1e-6 <= y-h/2 <= y+h/2 <= 1+1e-6
                hashes[digest(path)].add(split); counts[split] += 1
        assert all(len(splits)==1 for splits in groups.values()), 'Group leakage'
        assert all(len(splits)==1 for splits in hashes.values()), 'Exact-image leakage'
        # Old validation results are stale after expansion.
        for stale in ['validation.json','validation-report.json']:
            (target/stale).unlink(missing_ok=True)
        report = {'images':dict(counts),'decoded_and_labels_checked':True,
                  'cross_split_exact_duplicates':0,'cross_split_group_overlap':0,
                  'status':'development_dataset_not_independent_benchmark',
                  'limitation':'same location/worker can recur across dates; date split is not unseen-site evaluation'}
        (target/'expansion-validation.json').write_text(json.dumps(report,indent=2))
        print(kind, report)
    (OUT/'review-decisions.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
