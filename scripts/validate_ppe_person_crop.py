"""Compare full-frame and person-crop PPE on a saved video; no risk alerts."""
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / 'outputs/runtime/yolo'))
import cv2
import torch
from ultralytics import YOLO
from src.ppe_person_crop import infer_person_ppe


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--objects-weights', type=Path, required=True)
    p.add_argument('--ppe-weights', type=Path, required=True)
    p.add_argument('--sample-fps', type=float, default=1)
    args = p.parse_args()
    if args.output.exists() or args.sample_fps <= 0:
        raise ValueError('Use a new output folder and positive sample FPS')
    torch.set_num_threads(4)
    objects, ppe = YOLO(str(args.objects_weights)), YOLO(str(args.ppe_weights))
    if objects.names != {0: 'person', 1: 'forklift'}:
        raise ValueError('Unexpected object classes')
    cap = cv2.VideoCapture(str(args.source))
    fps, w, h = cap.get(5), int(cap.get(3)), int(cap.get(4))
    if not cap.isOpened() or fps <= 0:
        raise ValueError('Cannot decode source')
    args.output.mkdir(parents=True)
    stride = max(1, round(fps / args.sample_fps))
    writer = cv2.VideoWriter(str(args.output / 'comparison.mp4'),
                            cv2.VideoWriter_fourcc(*'mp4v'), fps / stride, (2*w, h))
    if not writer.isOpened():
        raise RuntimeError('Cannot open video writer')
    idx, records = 0, []
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % stride == 0:
                detections = objects.predict(frame, conf=.25, device='cpu', verbose=False)[0]
                people = [b.xyxy[0].tolist() for b in detections.boxes if int(b.cls.item()) == 0]
                raw = ppe.predict(frame, conf=.25, device='cpu', verbose=False)[0]
                full_heads = [{'class':raw.names[int(b.cls.item())],
                               'confidence':float(b.conf.item()),
                               'bbox_xyxy':b.xyxy[0].tolist()} for b in raw.boxes]
                observations = infer_person_ppe(frame, people, ppe, full_frame_heads=full_heads)
                left, right = raw.plot(), frame.copy()
                for row in observations:
                    x1, y1, x2, y2 = map(int, row['person_bbox_xyxy'])
                    color = (0, 180, 0) if row['state'] == 'helmet_detected' else (0, 190, 255)
                    cv2.rectangle(right, (x1, y1), (x2, y2), color, 1)
                    cv2.putText(right, f"P{row['person_index']} {row['state']}",
                                (x1, max(45, y1-5)), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
                    for head in row['head_candidates']:
                        a, b, c, d = map(int, head['bbox_xyxy'])
                        cv2.rectangle(right, (a, b), (c, d), (255, 200, 0), 2)
                cv2.putText(left, 'FULL FRAME / RISK NOT EVALUATED', (15,25), cv2.FONT_HERSHEY_SIMPLEX,.65,(0,200,255),2)
                cv2.putText(right, 'PERSON CROP / RISK NOT EVALUATED', (15,25), cv2.FONT_HERSHEY_SIMPLEX,.65,(0,200,255),2)
                import numpy as np
                comparison = np.concatenate([left, right], axis=1)
                writer.write(comparison)
                if len(records) in {0,5}:
                    cv2.imwrite(str(args.output / f'preview_{len(records):04d}.jpg'), comparison)
                records.append({'frame_index':idx,'timestamp_seconds':idx/fps,
                                'people_detected':len(people),'observations':observations,
                                'full_frame_head_count':len(raw.boxes),'risk_status':'not_evaluated'})
            idx += 1
    finally:
        cap.release()
        writer.release()
    (args.output/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    summary = {'source':str(args.source.resolve()),'frames_sampled':len(records),
               'sample_stride':stride,'confidence_threshold':.25,
               'person_state_counts':{},'accuracy':'not measured; full ground truth absent',
               'limitations':'frame-local indices; missed people not examined; no tracking or automatic PPE violation',
               'weights':{'objects':str(args.objects_weights.resolve()),'ppe':str(args.ppe_weights.resolve())}}
    for record in records:
        for row in record['observations']:
            state=row['state']; summary['person_state_counts'][state]=summary['person_state_counts'].get(state,0)+1
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
