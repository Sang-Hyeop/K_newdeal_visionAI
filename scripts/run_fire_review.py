"""Initial video6 public-model review. Raw detections, no fire alarm certification."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / 'outputs/runtime/yolo'))
os.environ['YOLO_AUTOINSTALL'] = 'false'

def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()

def main():
    import cv2
    import torch
    from ultralytics import YOLO
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/review/fire-current.json')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    source, weights = ROOT / config['source_video'], ROOT / config['weights']
    assert sha(source) == config['source_sha256'], 'Source video changed'
    assert sha(weights) == config['model_sha256'], 'Model changed'
    torch.set_num_threads(4)
    model = YOLO(str(weights))
    assert {str(k): v.lower() for k, v in model.names.items()} == config['classes']
    out = ROOT / config['output_root']
    out.mkdir(parents=True, exist_ok=True)
    review = ROOT / config['review_video']
    review.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError('Cannot open video')
    fps = cap.get(cv2.CAP_PROP_FPS)
    width, height = int(cap.get(3)), int(cap.get(4))
    if fps <= 0:
        raise ValueError('Invalid source FPS')
    stride = max(1, round(fps / config['sample_fps']))
    temporary = out / '.review-build.mp4'
    writer = cv2.VideoWriter(str(temporary), cv2.VideoWriter_fourcc(*'mp4v'), fps / stride, (width, height))
    if not writer.isOpened():
        raise ValueError('Cannot create review')
    rows = []
    index = 0
    started = time.monotonic()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % stride:
                index += 1
                continue
            result = model.predict(frame, imgsz=config['imgsz'], conf=config['proposal_confidence'], device='cpu', verbose=False)[0]
            detections = [{'class': model.names[int(b.cls)], 'confidence': float(b.conf), 'bbox_xyxy': b.xyxy[0].tolist()} for b in result.boxes]
            visible = [d for d in detections if d['class'] in ('fire', 'smoke') and d['confidence'] >= config['display_confidence']]
            row = {'frame_index': index, 'timestamp_seconds': index / fps, 'detections': detections, 'display_detections': visible, 'alarm_eligible': False, 'assessment': 'raw_model_candidates_only'}
            rows.append(row)
            canvas = frame.copy()
            cv2.rectangle(canvas, (0, 0), (width, 82), (0, 0, 0), -1)
            title = 'FIRE / SMOKE CANDIDATE' if visible else 'NO CURRENT FIRE/SMOKE DETECTION'
            cv2.putText(canvas, title, (12, 25), 0, .65, (0, 180, 255) if visible else (220, 220, 220), 2)
            cv2.putText(canvas, 'PUBLIC MODEL REVIEW / NO TEMPORAL ALARM / NOT A SAFE VERDICT', (12, 49), 0, .48, (220, 220, 220), 1)
            cv2.putText(canvas, f'VIDEO 6 / t={index / fps:.2f}s / sampled {fps / stride:.2f} FPS', (12, 71), 0, .48, (220, 220, 220), 1)
            for d in visible:
                x1, y1, x2, y2 = map(int, d['bbox_xyxy'])
                color = (0, 80, 255) if d['class'] == 'fire' else (180, 180, 180)
                cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
                cv2.putText(canvas, f"{d['class'].upper()} {d['confidence']:.2f}", (x1, max(96, y1 - 6)), 0, .55, color, 2)
            writer.write(canvas)
            index += 1
    finally:
        cap.release()
        writer.release()
    if not rows:
        raise ValueError('No frames processed')
    encoder = shutil.which('ffmpeg')
    if encoder:
        subprocess.run([encoder, '-y', '-loglevel', 'error', '-i', str(temporary), '-c:v', 'libx264', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(review)], check=True)
    else:
        shutil.copy2(temporary, review)
    temporary.unlink()
    (out / 'detections.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    summary = {'video_number': 6, 'source_sha256': sha(source), 'model_sha256': sha(weights), 'samples': len(rows), 'decoded_source_frames': index, 'source_fps': fps, 'processed_fps': fps / stride, 'wall_seconds': time.monotonic() - started, 'display_confidence': config['display_confidence'], 'frames_with_detection': {label: sum(any(d['class'] == label for d in row['display_detections']) for row in rows) for label in ('fire', 'smoke')}, 'first_fire_detection_seconds': next((r['timestamp_seconds'] for r in rows if any(d['class'] == 'fire' for d in r['display_detections'])), None), 'review_sha256': sha(review), 'scope': config['event_status']}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
