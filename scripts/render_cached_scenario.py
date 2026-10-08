"""Re-render a saved scenario run without running any model inference."""
import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scenario_render import render


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview-indices', type=int, nargs='*', default=[])
    args = parser.parse_args()

    summary = json.loads((args.run / 'summary.json').read_text())
    rows = [json.loads(line) for line in (args.run / 'detections.jsonl').read_text().splitlines()]
    cap = cv2.VideoCapture(summary['source'])
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source video: {summary['source']}")
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*'mp4v'), summary['processed_fps'], (width, height))
    if not writer.isOpened():
        raise RuntimeError(f'Cannot create output video: {args.output}')

    previews = set(args.preview_indices)
    for row_index, row in enumerate(rows):
        cap.set(cv2.CAP_PROP_POS_FRAMES, row['frame_index'])
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot read source frame {row['frame_index']}")
        canvas = render(frame, row['feature_events'], detections=row['object_detections'],
                        proximity_warning_ratio=summary['camera_config'].get('warning_ratio', 1.6),
                        driver_overlap_threshold=summary['camera_config'].get('driver_overlap_exclusion_ratio', .8))
        cv2.putText(canvas, f"WARNING <= {summary['camera_config'].get('warning_ratio', 1.6):.2f} / CRITICAL <= {summary['camera_config'].get('critical_ratio', .8):.2f} person-height gap",
                    (12, height - 34), 0, .42, (230, 230, 230), 1)
        cv2.putText(canvas, f"VIDEO 1 / t={row['timestamp_seconds']:.2f}s / CACHED EVENTS / METERS UNCALIBRATED",
                    (12, height - 14), 0, .48, (0, 190, 255), 1)
        writer.write(canvas)
        if row_index in previews:
            preview = args.output.with_name(f'{args.output.stem}_sample_{row_index}.jpg')
            cv2.imwrite(str(preview), canvas)

    cap.release()
    writer.release()
    print(json.dumps({'samples': len(rows), 'output': str(args.output.resolve()),
                      'preview_indices': sorted(previews)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
