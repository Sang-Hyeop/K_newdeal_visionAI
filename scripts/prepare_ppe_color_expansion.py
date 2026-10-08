"""Sample additional, group-disjoint AI Hub PPE crops for human review."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATASET = Path('/Users/sanghyeopkim/Desktop/비전AI안전관제(26_7 ~ 11)/datasets/aihub_smartyard')
OUT = ROOT / 'data/training_review/ppe_color_expansion_v2'
PER_CLASS = 120
MIN_FRAME_GAP = 120
SEED = 20261008


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def helmet_color(image: np.ndarray, box: list[float]) -> tuple[str, float, float]:
    x1, y1, x2, y2 = map(int, box)
    crop = image[max(0, y1):max(y1 + 1, y1 + int((y2 - y1) * .48)), max(0, x1):max(x1 + 1, x2)]
    if crop.size == 0:
        return 'unknown', 0.0, 0.0
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    valid = (hsv[:, 2] > 45) & (hsv[:, 2] < 250)
    if not valid.any():
        return 'unknown', 0.0, 0.0
    sat = hsv[valid, 1]
    hue = hsv[valid, 0]
    median_sat = float(np.median(sat))
    median_hue = float(np.median(hue[sat > 35])) if np.any(sat > 35) else 0.0
    if median_sat < 35:
        name = 'white_gray'
    elif median_hue < 10 or median_hue >= 170:
        name = 'red_or_orange'
    elif median_hue < 32:
        name = 'yellow'
    elif median_hue < 85:
        name = 'green'
    elif median_hue < 135:
        name = 'blue'
    else:
        name = 'purple_other'
    return name, median_hue, median_sat


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f'Protected existing review directory: {OUT}')
    OUT.mkdir(parents=True)
    rng = random.Random(SEED)
    accepted = []
    prior_support = json.loads((ROOT / 'configs/review/ppe-remaining-support-v2.json').read_text())
    used_frames: dict[tuple[str, str], list[int]] = {}
    for row in prior_support:
        stem = Path(row['source']).stem
        try:
            frame_id = int(stem.rsplit('_', 1)[1])
        except (IndexError, ValueError):
            continue
        used_frames.setdefault((row['class_folder'], row['group']), []).append(frame_id)

    for folder, class_id, limit in [('helmet_worn', 0, PER_CLASS), ('helmet_missing', 1, PER_CLASS)]:
        labels = list((DATASET / 'training/labels' / folder).glob('*.json'))
        rng.shuffle(labels)
        class_frame_ids = {key: list(frames) for key, frames in used_frames.items() if key[0] == folder}
        class_rows = []
        for label_path in labels:
            group = label_path.stem.rsplit('_', 1)[0]
            try:
                frame_id = int(label_path.stem.rsplit('_', 1)[1])
            except ValueError:
                continue
            frame_ids = class_frame_ids.setdefault((folder, group), [])
            if any(abs(frame_id - prior) < MIN_FRAME_GAP for prior in frame_ids):
                continue
            image_path = DATASET / 'training/source' / folder / f'{label_path.stem}.jpg'
            if not image_path.is_file():
                continue
            try:
                annotation = json.loads(label_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            width = int(annotation['images']['width'])
            height = int(annotation['images']['height'])
            boxes = [a['bbox'] for a in annotation.get('annotations', [])
                     if a.get('object_class') == 0 and isinstance(a.get('bbox'), list)
                     and len(a['bbox']) == 4]
            boxes = [b for b in boxes if 32 <= b[2] - b[0] <= 300 and 32 <= b[3] - b[1] <= 300
                     and b[0] > 20 and b[1] > 20 and b[2] < width - 20 and b[3] < height - 20]
            if not boxes:
                continue
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            h, w = image.shape[:2]
            box = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            x, y, x2, y2 = map(float, box)
            pad_x, pad_y = x2 - x, y2 - y
            left, top = max(0, int(x - pad_x)), max(0, int(y - pad_y))
            right, bottom = min(w, int(x2 + pad_x)), min(h, int(y2 + pad_y))
            crop = image[top:bottom, left:right]
            if crop.size == 0:
                continue
            color, hue, saturation = helmet_color(image, box) if class_id == 0 else ('not_applicable', 0.0, 0.0)
            stem = f'{folder}_{len(class_rows):03d}'
            crop_path = OUT / f'{stem}.jpg'
            if not cv2.imwrite(str(crop_path), crop):
                continue
            crop_boxes = []
            for b in boxes:
                bx, by, bx2, by2 = map(float, b)
                if bx2 <= left or bx >= right or by2 <= top or by >= bottom:
                    continue
                crop_boxes.append([class_id, max(bx, left) - left, max(by, top) - top,
                                   min(bx2, right) - left, min(by2, bottom) - top])
            overlay = cv2.resize(crop, (320, 300))
            ch, cw = crop.shape[:2]
            for c, bx, by, bx2, by2 in crop_boxes:
                cv2.rectangle(overlay, (round(bx / cw * 320), round(by / ch * 300)),
                              (round(bx2 / cw * 320), round(by2 / ch * 300)),
                              (0, 255, 0) if c == 0 else (0, 190, 255), 2)
            cv2.putText(overlay, f'{stem} {color}', (5, 18), cv2.FONT_HERSHEY_SIMPLEX, .48, (0, 0, 255), 1)
            cv2.imwrite(str(OUT / f'{stem}_overlay.jpg'), overlay)
            class_rows.append({
                'image': crop_path.name, 'source': str(image_path), 'label_source': str(label_path),
                'source_sha256': sha(image_path), 'label_sha256': sha(label_path), 'group': group,
                'class_folder': folder, 'class_id': class_id, 'crop_xyxy': [left, top, right, bottom],
                'crop_boxes_xyxy': crop_boxes, 'helmet_color_estimate': color,
                'top_head_median_hue': hue, 'top_head_median_saturation': saturation,
                'overlay': f'{stem}_overlay.jpg', 'source_frame_id': frame_id,
                'review_status': 'candidate_not_yet_approved',
            })
            frame_ids.append(frame_id)
            if len(class_rows) >= limit:
                break
        accepted.extend(class_rows)
        print(folder, 'candidates', len(class_rows), 'sequence_groups', len({r['group'] for r in class_rows}), flush=True)

    manifest = {'seed': SEED, 'source': str(DATASET), 'purpose': 'human review only; not yet training eligible',
                'candidates': accepted}
    (OUT / 'candidates.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    for cls in ['helmet_worn', 'helmet_missing']:
        rows = [r for r in accepted if r['class_folder'] == cls]
        if cls == 'helmet_worn':
            rows.sort(key=lambda r: (r['helmet_color_estimate'], r['top_head_median_hue']))
        for offset in range(0, len(rows), 16):
            tiles = []
            for row in rows[offset:offset + 16]:
                tiles.append(cv2.imread(str(OUT / row['overlay'])))
            blank = np.zeros((300, 320, 3), np.uint8)
            tiles.extend([blank] * (16 - len(tiles)))
            sheet = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, 16, 4)])
            cv2.imwrite(str(OUT / f'{cls}_review_{offset // 16:02d}.jpg'), sheet)
    print('output', OUT)


if __name__ == '__main__':
    main()
