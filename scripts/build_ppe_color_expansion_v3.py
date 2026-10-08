"""Build a reviewed PPE color/no-helmet expansion while preserving fixed holdouts."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/reviewed_pilot/ppe_remaining_v2'
OUT = ROOT / 'data/reviewed_pilot/ppe_color_expansion_v3'
AIHUB_REVIEW = ROOT / 'data/training_review/ppe_color_expansion_v2'
ROBOFLOW_REVIEW = ROOT / 'data/training_review/ppe_color_expansion_v3'

# Original-resolution review: visually clear, train-split scenes only.
# Color notes describe visible hardhat colors, not a model-derived estimate.
ROBOFLOW_IDS = {
    91: {'helmet_colors': ['orange', 'white'], 'note': 'visible construction workers'},
    120: {'helmet_colors': ['yellow', 'red'], 'note': 'two clear hardhats'},
    180: {'helmet_colors': ['blue', 'yellow', 'red'], 'note': 'three distinct hardhat colors'},
    185: {'helmet_colors': ['red_or_orange'], 'note': 'construction hardhats'},
    187: {'helmet_colors': ['blue'], 'note': 'elevated electrical workers'},
    238: {'helmet_colors': ['yellow'], 'note': 'mixed class scene; visible yellow hardhat'},
    267: {'helmet_colors': ['yellow'], 'note': 'clear close hardhat'},
    269: {'helmet_colors': ['yellow'], 'note': 'clear hardhat'},
    274: {'helmet_colors': ['yellow'], 'note': 'clear close hardhat'},
    281: {'helmet_colors': ['yellow'], 'note': 'forklift operator hardhat'},
    292: {'helmet_colors': ['yellow'], 'note': 'warehouse workers with hardhats'},
    48: {'helmet_colors': ['white'], 'note': 'clear white hardhat; also one no-helmet head'},
    30: {'helmet_colors': [], 'note': 'no-helmet heads visible'},
    33: {'helmet_colors': [], 'note': 'multiple no-helmet heads visible'},
    41: {'helmet_colors': [], 'note': 'clear uncovered head in warehouse'},
    45: {'helmet_colors': [], 'note': 'clear uncovered head in warehouse'},
    67: {'helmet_colors': [], 'note': 'clear uncovered head'},
    69: {'helmet_colors': [], 'note': 'two uncovered heads'},
    221: {'helmet_colors': [], 'note': 'uncovered head at workbench'},
    234: {'helmet_colors': [], 'note': 'multiple uncovered heads'},
    245: {'helmet_colors': [], 'note': 'uncovered head beside forklift'},
    246: {'helmet_colors': [], 'note': 'uncovered heads in warehouse'},
    265: {'helmet_colors': [], 'note': 'uncovered head in warehouse'},
    285: {'helmet_colors': [], 'note': 'uncovered head in warehouse'},
    289: {'helmet_colors': [], 'note': 'multiple uncovered heads'},
    297: {'helmet_colors': [], 'note': 'multiple uncovered heads'},
    300: {'helmet_colors': [], 'note': 'uncovered head in warehouse'},
    308: {'helmet_colors': [], 'note': 'multiple uncovered heads'},
    312: {'helmet_colors': [], 'note': 'uncovered heads in warehouse'},
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def yolo(boxes, width, height):
    lines = []
    for cls, x1, y1, x2, y2 in boxes:
        if not (cls in (0, 1) and 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError(f'invalid box: {cls, x1, y1, x2, y2, width, height}')
        lines.append(f'{cls} {(x1+x2)/2/width:.8f} {(y1+y2)/2/height:.8f} '
                     f'{(x2-x1)/width:.8f} {(y2-y1)/height:.8f}')
    return '\n'.join(lines) + '\n'


def add_image(src: Path, boxes, name: str, meta: dict, rows: list):
    image = cv2.imread(str(src))
    if image is None:
        raise ValueError(f'cannot decode {src}')
    h, w = image.shape[:2]
    target = OUT / 'train/images' / f'{name}.jpg'
    label = OUT / 'train/labels' / f'{name}.txt'
    shutil.copy2(src, target)
    label.write_text(yolo(boxes, w, h))
    rows.append({**meta, 'image': target.name, 'split': 'train', 'training_eligible': True,
                 'image_sha256': sha(target), 'label_sha256': sha(label)})


def main():
    if OUT.exists():
        raise RuntimeError(f'Protected existing dataset: {OUT}')
    if not BASE.is_dir():
        raise FileNotFoundError(BASE)
    for split in ('train', 'val', 'test'):
        (OUT / split / 'images').mkdir(parents=True)
        (OUT / split / 'labels').mkdir(parents=True)
    rows = json.loads((BASE / 'manifest.json').read_text())
    prior = json.loads((ROOT / 'data/reviewed_pilot/expansion_v3/ppe/manifest.json').read_text())
    blocked_visual_groups = {r['visual_group'] for r in prior
                             if 'visual_group' in r and r.get('split') != 'train'}
    blocked_aihub_groups = {r['group'] for r in prior
                            if 'group' in r and r.get('split') != 'train'}
    blocked_aihub_dates = {r['split_group'].rsplit('/', 1)[-1] for r in prior
                           if r.get('split') in ('val', 'test') and r.get('split_group')}
    for row in rows:
        if not row.get('training_eligible'):
            continue
        name = row.get('image') or (Path(row['stem']).with_suffix('.jpg').name if row.get('stem') else '')
        if not name:
            raise ValueError(f'manifest row has no image name: {row}')
        for folder in ('images', 'labels'):
            suffix = '.jpg' if folder == 'images' else '.txt'
            src = BASE / row['split'] / folder / (Path(name).stem + suffix)
            if not src.is_file():
                raise FileNotFoundError(src)
            shutil.copy2(src, OUT / row['split'] / folder / src.name)

    # Add reviewed Roboflow full images. Head annotations match the established
    # project pilot mapping; validation/test records are prohibited here.
    candidates = json.loads((ROBOFLOW_REVIEW / 'candidates.json').read_text())
    excluded_roboflow_holdout_groups = []
    excluded_roboflow_class_scope = []
    for r in candidates:
        if r['id'] not in ROBOFLOW_IDS:
            continue
        if r['split'] != 'train':
            raise ValueError(f'non-train source was selected: {r["id"]} {r["split"]}')
        if r['visual_group'] in blocked_visual_groups:
            excluded_roboflow_holdout_groups.append(r['id'])
            continue
        # The source class "No Helmet" contains person-sized boxes in this
        # review pool, which do not match our no_helmet_head class. Keep only
        # verified helmeted-head-only images; bare-head samples come from AIHub.
        if set(r['classes']) != {0}:
            excluded_roboflow_class_scope.append(r['id'])
            continue
        src = Path(r['source'])
        image = cv2.imread(str(src))
        h, w = image.shape[:2]
        boxes = [(int(c), float(x1), float(y1), float(x2), float(y2))
                 for c, x1, y1, x2, y2 in r['boxes_xyxy']]
        add_image(src, boxes, f'roboflow_{r["id"]:03d}', {
            'source_type': 'roboflow_hard_hat_detection_mhumb_v1',
            'source_id': r['id'], 'source_group': r['visual_group'],
            'source_image': str(src), 'source_label': r['label_source'],
            'source_image_sha256': sha(src), 'source_label_sha256': sha(Path(r['label_source'])),
            'manual_review': 'original-resolution visual review; only helmeted-head boxes retained',
            'visible_hardhat_colors': ROBOFLOW_IDS[r['id']]['helmet_colors'],
            'review_note': ROBOFLOW_IDS[r['id']]['note'],
            'status': 'training_eligible_after_visual_review'
        }, rows)

    # AIHub head-level support: select samples across groups and spaced frames,
    # rather than importing the large repetitive corpus wholesale.
    d = json.loads((AIHUB_REVIEW / 'candidates.json').read_text())
    for cls_folder, class_id, per_group in [('helmet_worn', 0, 3), ('helmet_missing', 1, 3)]:
        group_rows = {}
        for r in d['candidates']:
            if r['class_folder'] != cls_folder:
                continue
            # Never add a source sequence or site/day held out by the previous
            # expansion's val/test assignment, even if its original split says train.
            date = r['group'].split('_D', 1)[-1][:10] if '_D' in r['group'] else ''
            if r['group'] in blocked_aihub_groups or date in blocked_aihub_dates:
                continue
            group_rows.setdefault(r['group'], []).append(r)
        selected = []
        for group, items in sorted(group_rows.items()):
            items.sort(key=lambda x: x['source_frame_id'])
            # Limit dense repeated sequences; select temporally spread examples.
            n = min(per_group, len(items))
            indexes = [round(i * (len(items) - 1) / max(1, n - 1)) for i in range(n)]
            selected.extend(items[i] for i in sorted(set(indexes)))
        selected = selected[:30]
        for i, r in enumerate(selected):
            src = AIHUB_REVIEW / r['image']
            image = cv2.imread(str(src))
            h, w = image.shape[:2]
            boxes = [(class_id, float(x1), float(y1), float(x2), float(y2))
                     for c, x1, y1, x2, y2 in r['crop_boxes_xyxy'] if int(c) == class_id]
            add_image(src, boxes, f'aihub_{cls_folder}_{i:03d}', {
                'source_type': 'aihub_smartyard_training', 'source_image': r['source'],
                'source_label': r['label_source'], 'source_image_sha256': r['source_sha256'],
                'source_label_sha256': r['label_sha256'], 'source_group': r['group'],
                'source_frame_id': r['source_frame_id'], 'class_folder': cls_folder,
                'manual_review': 'head-level source label visually spot-checked; source annotation retained',
                'status': 'training_eligible_after_visual_review'
            }, rows)

    # Keep original fixed validation/test byte-identical and record hashes.
    holdout_hashes = {}
    for split in ('val', 'test'):
        for folder in ('images', 'labels'):
            for src in sorted((BASE / split / folder).glob('*.jpg' if folder == 'images' else '*.txt')):
                dst = OUT / src.relative_to(BASE)
                if not dst.is_file() or sha(src) != sha(dst):
                    raise AssertionError(f'holdout changed or missing: {src}')
                holdout_hashes[str(src.relative_to(BASE))] = sha(dst)
    added = [r for r in rows if r.get('source_type') in
             ('roboflow_hard_hat_detection_mhumb_v1', 'aihub_smartyard_training')]
    report = {
        'status': 'reviewed_data_expansion_ready_for_training',
        'base_dataset': str(BASE),
        'added_by_source': {
            'roboflow_full_images': sum(r.get('source_type', '').startswith('roboflow') for r in added),
            'aihub_helmet_worn_context_crops': sum(r.get('class_folder') == 'helmet_worn' for r in added),
            'aihub_helmet_missing_context_crops': sum(r.get('class_folder') == 'helmet_missing' for r in added),
        },
        'counts': {s: sum(r['split'] == s and r.get('training_eligible', False) for r in rows)
                   for s in ('train', 'val', 'test')},
        'training_eligible_count': sum(bool(r.get('training_eligible')) for r in rows),
        'excluded_roboflow_holdout_visual_groups': excluded_roboflow_holdout_groups,
        'excluded_roboflow_incompatible_class_scope': excluded_roboflow_class_scope,
        'blocked_aihub_holdout_dates': sorted(blocked_aihub_dates),
        'old_holdouts_byte_identical': True,
        'holdout_files_sha256': holdout_hashes,
        'roboflow_color_notes_are_manual': True,
        'aihub_automatic_color_estimates_not_used': True,
        'limitations': [
            'AIHub support has repeated views from a limited number of source sequences.',
            'Roboflow full-image labels preserve the established project pilot class mapping.',
            'Metrics remain development-only; no independent new-site test is created here.'
        ]
    }
    (OUT / 'manifest.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'dataset.yaml').write_text(yaml.safe_dump({
        'path': str(OUT), 'train': 'train/images', 'val': 'val/images', 'test': 'test/images',
        'names': {0: 'helmeted_head', 1: 'no_helmet_head'}
    }, sort_keys=False))
    (OUT / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
