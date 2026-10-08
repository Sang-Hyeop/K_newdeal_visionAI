"""Evaluate a helmet-only specialist union at the demo inference threshold."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ppe_recall_ensemble import PPERecallEnsemble


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2-x1) * max(0, y2-y1)
    area_a = max(0, a[2]-a[0]) * max(0, a[3]-a[1])
    area_b = max(0, b[2]-b[0]) * max(0, b[3]-b[1])
    return inter / max(1e-9, area_a + area_b - inter)


def load_gt(label_path, shape):
    h, w = shape[:2]
    rows = []
    for line in label_path.read_text().splitlines():
        cls, xc, yc, bw, bh = map(float, line.split())
        rows.append((int(cls), [(xc-bw/2)*w, (yc-bh/2)*h,
                               (xc+bw/2)*w, (yc+bh/2)*h]))
    return rows


def score(model, image, gt, conf, imgsz, iou_threshold):
    result = model.predict(image, conf=conf, imgsz=imgsz, device='cpu', verbose=False)[0]
    pred = [(int(b.cls.item()), b.xyxy[0].tolist()) for b in result.boxes]
    used = set()
    counts = {0: {'tp': 0, 'fp': 0, 'fn': 0}, 1: {'tp': 0, 'fp': 0, 'fn': 0}}
    for cls in (0, 1):
        truth = [box for c, box in gt if c == cls]
        candidates = sorted([(iou(box, g), j) for j, (c, box) in enumerate(pred)
                             if c == cls for g in truth], reverse=True)
        matched_gt = set()
        matched_pred = set()
        for overlap, pred_index in candidates:
            # Greedy matching: use the best remaining truth for each prediction.
            if overlap < iou_threshold or pred_index in matched_pred:
                continue
            best_gt = max((k for k in range(len(truth)) if k not in matched_gt),
                          key=lambda k: iou(pred[pred_index][1], truth[k]), default=None)
            if best_gt is not None and iou(pred[pred_index][1], truth[best_gt]) >= iou_threshold:
                matched_pred.add(pred_index)
                matched_gt.add(best_gt)
        counts[cls]['tp'] = len(matched_pred)
        counts[cls]['fp'] = sum(1 for j, (c, _) in enumerate(pred) if c == cls and j not in matched_pred)
        counts[cls]['fn'] = len(truth) - len(matched_gt)
    return counts


def add(a, b):
    return {cls: {key: a[cls][key] + b[cls][key] for key in ('tp', 'fp', 'fn')}
            for cls in (0, 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, default=ROOT/'data/reviewed_pilot/ppe_color_expansion_v3')
    p.add_argument('--baseline', type=Path, default=ROOT/'models/pilot_v3_ppe_expansion/ppe.pt')
    p.add_argument('--supplement', type=Path, default=ROOT/'models/demo_ppe_interpolated_v4/ppe.pt')
    p.add_argument('--specialist', type=Path, default=ROOT/'outputs/training/ppe_color_expansion_v3/weights/best.pt')
    p.add_argument('--output', type=Path, default=ROOT/'outputs/training/ppe_color_expansion_v3/helmet_specialist_union.json')
    p.add_argument('--conf', type=float, default=.25)
    p.add_argument('--imgsz', type=int, default=640)
    p.add_argument('--iou', type=float, default=.5)
    args = p.parse_args()
    baseline, supplement, specialist = (YOLO(str(path)) for path in
                                         (args.baseline, args.supplement, args.specialist))
    current = PPERecallEnsemble(baseline, supplement, preserve_union=True,
                                helmet_specialist=YOLO(str(ROOT/'models/demo_ppe_failure_context_v3/last.pt')))
    candidate = PPERecallEnsemble(baseline, supplement, preserve_union=True,
                                  helmet_specialist=specialist)
    totals = {'current_demo_ensemble': {c: {'tp': 0, 'fp': 0, 'fn': 0} for c in (0, 1)},
              'candidate_helmet_specialist': {c: {'tp': 0, 'fp': 0, 'fn': 0} for c in (0, 1)}}
    image_count = 0
    for image_path in sorted((args.dataset/'test/images').glob('*')):
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        label_path = args.dataset/'test/labels'/f'{image_path.stem}.txt'
        gt = load_gt(label_path, image.shape)
        for name, model in [('current_demo_ensemble', current),
                            ('candidate_helmet_specialist', candidate)]:
            totals[name] = add(totals[name], score(model, image, gt, args.conf, args.imgsz, args.iou))
        image_count += 1
    report = {'status': 'development-only; no promotion',
              'dataset': str(args.dataset.resolve()), 'images': image_count,
              'inference': {'conf': args.conf, 'imgsz': args.imgsz, 'iou_match': args.iou},
              'classes': {'0': 'helmeted_head', '1': 'no_helmet_head'},
              'models': {'baseline': str(args.baseline), 'supplement': str(args.supplement),
                         'current_specialist': str(ROOT/'models/demo_ppe_failure_context_v3/last.pt'),
                         'candidate_specialist': str(args.specialist)},
              'counts': totals}
    for model_counts in totals.values():
        for counts in model_counts.values():
            denom_p = counts['tp'] + counts['fp']
            denom_r = counts['tp'] + counts['fn']
            counts['precision'] = counts['tp']/denom_p if denom_p else 0
            counts['recall'] = counts['tp']/denom_r if denom_r else 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
