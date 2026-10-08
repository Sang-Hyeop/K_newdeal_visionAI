"""Create a contact sheet of unused, distinct-group Roboflow PPE candidates."""
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/training_review/ppe_color_expansion_v3'


def main():
    if OUT.exists():
        raise RuntimeError(f'Protected existing review directory: {OUT}')
    OUT.mkdir(parents=True)
    index = json.loads((ROOT / 'data/training_review/full_audit/ppe-index.json').read_text())
    decisions = {r['id']: r for r in json.loads((ROOT / 'data/training_review/full_audit/ppe-review-decisions.json').read_text())}
    trained = {r['id'] for r in json.loads((ROOT / 'data/reviewed_pilot/expansion_v3/ppe/manifest.json').read_text())}
    by_group = defaultdict(list)
    for row in index:
        decision = decisions[row['id']]
        if row['id'] in trained or decision['status'] != 'screen_pass_candidate_needs_full_resolution_confirmation':
            continue
        image_path = Path(row['image'])
        if not image_path.is_file():
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        h, w = image.shape[:2]
        if not row.get('boxes'):
            continue
        by_group[decision['visual_group']].append((w * h, row, decision, image))

    selected = []
    for group, choices in by_group.items():
        _, row, decision, image = max(choices, key=lambda x: (x[0], len(x[1]['boxes'])))
        canvas = cv2.resize(image, (320, 300))
        h, w = image.shape[:2]
        for cls, x1, y1, x2, y2 in row['boxes']:
            color = (0, 255, 0) if cls == 0 else (0, 190, 255)
            cv2.rectangle(canvas, (round(x1 / w * 320), round(y1 / h * 300)),
                          (round(x2 / w * 320), round(y2 / h * 300)), color, 2)
        classes = sorted({b[0] for b in row['boxes']})
        label = f"id{row['id']} g{group} cls{','.join(map(str, classes))}"
        cv2.putText(canvas, label, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 0, 255), 1)
        overlay_name = f"candidate_{row['id']:03d}.jpg"
        cv2.imwrite(str(OUT / overlay_name), canvas)
        selected.append({'id': row['id'], 'visual_group': group, 'source': row['image'],
                         'label_source': row['label'], 'split': row['split'], 'boxes_xyxy': row['boxes'],
                         'classes': classes, 'overlay': overlay_name,
                         'review_status': decision['status'], 'training_eligible': False,
                         'requires_full_resolution_review': True})
    selected.sort(key=lambda x: x['id'])
    (OUT / 'candidates.json').write_text(json.dumps(selected, ensure_ascii=False, indent=2) + '\n')
    for offset in range(0, len(selected), 16):
        tiles = [cv2.imread(str(OUT / r['overlay'])) for r in selected[offset:offset + 16]]
        tiles += [np.zeros((300, 320, 3), np.uint8)] * (16 - len(tiles))
        sheet = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, 16, 4)])
        cv2.imwrite(str(OUT / f'roboflow_review_{offset // 16:02d}.jpg'), sheet)
    print('distinct_groups', len(selected), 'class_images', {
        str(cls): sum(cls in r['classes'] for r in selected) for cls in [0, 1]}, 'output', OUT)


if __name__ == '__main__':
    main()
