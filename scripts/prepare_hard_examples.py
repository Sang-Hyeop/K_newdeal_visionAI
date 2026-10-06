"""Build a separately versioned, reviewed hard-example dataset from local ZIPs."""
from pathlib import Path
import json, shutil, zipfile, hashlib
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def main():
    config = json.loads((ROOT / 'configs/review/hard-examples-v1.json').read_text())
    base, dest = ROOT / config['base'], ROOT / config['output']
    if dest.exists():
        raise SystemExit(f'Existing dataset protected: {dest}')
    rows = json.loads((base / 'manifest.json').read_text())
    pool = {r['review_id']: r for r in json.loads((ROOT / 'data/training_review/train_archives_v1/candidates.json').read_text())}
    held = [r for r in rows if r['split'] in ['val', 'test']]
    for i in config['positive_ids']:
        # The old pool is pending review; this explicit reviewed recipe approves it.
        assert config['review_status'] == 'six_whole_frames_and_three_background_crops_visually_reviewed'
        assert pool[i]['split'] == 'train'
        assert all(pool[i]['site'] != r.get('site') and pool[i]['group'] != r.get('group') for r in held)
    shutil.copytree(base, dest)
    added = []
    for i in config['positive_ids']:
        source = pool[i]
        with zipfile.ZipFile(source['source_zip']) as archive:
            data = archive.read(source['image_member'])
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        h, w = image.shape[:2]
        assert [w, h] == source['resolution']
        boxes = [list(b) for b in source['boxes']]
        if str(i) in config['forklift_xyxy_corrections']:
            x1, y1, x2, y2 = config['forklift_xyxy_corrections'][str(i)]
            replacement = [1, x1*w/960, y1*h/540, (x2-x1)*w/960, (y2-y1)*h/540]
            indices = [j for j, b in enumerate(boxes) if b[0] == 1]
            assert len(indices) == 1
            boxes[indices[0]] = replacement
        variants = [(f'hard_full_{i}', image, boxes, None)]
        for crop in config['negative_crops']:
            if crop['id'] != i:
                continue
            x1,y1,x2,y2 = crop['xyxy']
            x1,x2 = int(x1*w/960),int(x2*w/960)
            y1,y2 = int(y1*h/540),int(y2*h/540)
            assert 0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h
            # Reject a crop intersecting any known object, even partly.
            for _,x,y,bw,bh in boxes:
                assert min(x2,x+bw) <= max(x1,x) or min(y2,y+bh) <= max(y1,y)
            variants.append((f'hard_background_{i}', image[y1:y2,x1:x2], [], [x1,y1,x2,y2]))
        for stem, im, labels, crop in variants:
            hh, ww = im.shape[:2]
            assert cv2.imwrite(str(dest/'train/images'/f'{stem}.jpg'), im)
            lines = []
            for c,x,y,bw,bh in labels:
                assert c in [0,1] and min(x,y) >= 0 and min(bw,bh) > 0 and x+bw <= ww+0.01 and y+bh <= hh+0.01
                lines.append(f'{int(c)} {(x+bw/2)/ww:.8f} {(y+bh/2)/hh:.8f} {bw/ww:.8f} {bh/hh:.8f}')
            (dest/'train/labels'/f'{stem}.txt').write_text('\n'.join(lines) + ('\n' if lines else ''))
            row = {**source, 'stem':stem, 'image':stem+'.jpg', 'split':'train', 'corrected_boxes':labels,
                   'source_member_sha256':hashlib.sha256(data).hexdigest(), 'crop_xyxy_original':crop,
                   'resolution':[ww,hh], 'qa_status':config['review_status'], 'training_eligible':True}
            rows.append(row); added.append(row)
    for split in ['val','test']:
        for folder in ['images','labels']:
            for p in (base/split/folder).iterdir():
                assert p.read_bytes() == (dest/split/folder/p.name).read_bytes()
    (dest/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    (dest/'dataset.yaml').write_text(f'path: {dest}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: person\n  1: forklift\n')
    report = {'added':added, 'counts':{s:len(list((dest/s/'images').glob('*.jpg'))) for s in ['train','val','test']},
              'held_sets_unchanged':True, 'status':'prepared_not_trained', 'demo_frames_added':0}
    (ROOT/'docs/checkpoints/2026-10-06/hard_examples_v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(report['counts'])

if __name__ == '__main__':
    main()
