"""Compare PPE checkpoints on the same held-out split without promotion."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, default=ROOT / 'data/reviewed_pilot/ppe_color_expansion_v2')
    p.add_argument('--output', type=Path, default=ROOT / 'outputs/training/ppe_color_expansion_v2/test_comparison.json')
    p.add_argument('--weights', nargs=2, type=Path, default=[
        ROOT / 'outputs/training/ppe_failure_context_v3/weights/best.pt',
        ROOT / 'outputs/training/ppe_color_expansion_v2/weights/best.pt',
    ])
    p.add_argument('--names', nargs=2, default=['baseline_ppe_failure_context_v3', 'candidate_ppe_color_expansion_v2'])
    args = p.parse_args()
    if len(args.weights) != 2 or len(args.names) != 2:
        raise ValueError('Exactly two comparable model weights and names are required')
    torch.set_num_threads(4)
    report = {
        'dataset': str(args.dataset.resolve()), 'split': 'test',
        'status': 'development-only; no model promotion',
        'scope': 'same fixed nine-image test split; prior curated sources may be correlated by site/date',
        'imgsz': 640, 'device': 'cpu', 'models': {}
    }
    for name, weight in zip(args.names, args.weights):
        if not weight.is_file():
            raise FileNotFoundError(weight)
        model = YOLO(str(weight))
        result = model.val(data=str(args.dataset / 'dataset.yaml'), split='test', imgsz=640,
                           device='cpu', workers=0, batch=4, plots=False, verbose=False)
        per_class = {}
        for i, cls in enumerate(result.box.ap_class_index):
            per_class[result.names[int(cls)]] = {
                'precision': float(result.box.p[i]), 'recall': float(result.box.r[i]),
                'mAP50': float(result.box.ap50[i]), 'mAP50_95': float(result.box.ap[i]),
            }
        report['models'][name] = {
            'weights': str(weight.resolve()), 'weights_sha256': sha(weight),
            'per_class': per_class,
            'overall': {k: float(v) for k, v in result.results_dict.items()},
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
