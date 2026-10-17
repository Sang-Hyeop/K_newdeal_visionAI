"""Initial video6 public-model review. Raw detections, no fire alarm certification."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / 'outputs/runtime/yolo'))
os.environ['YOLO_AUTOINSTALL'] = 'false'
sys.path.insert(0, str(ROOT))
from src.fire_detection import FireDetector, FireTemporal, SceneBoundary
from src.event_contract import export_events

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
    detector = FireDetector(model, config)
    temporal = FireTemporal(config['temporal'])
    boundary = SceneBoundary(config['scene_boundary'])
    records, previous = [], {}
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
            timestamp = index / fps
            cut = boundary.update(frame)
            raw, extra, visible = detector.predict(frame, timestamp, reset=bool(cut))
            events = temporal.update(timestamp, visible, reset=bool(cut))
            if cut:
                previous = {}
            transitions = [e for e in events if previous.get(e['track_id']) != (e['severity'], e['observation_status'])]
            previous = {e['track_id']:(e['severity'],e['observation_status']) for e in events}
            records.append({'timestamp_seconds':timestamp,'frame_index':index,'scene_id':temporal.scene,'events':events,'transitions':transitions})
            row = {'frame_index':index,'timestamp_seconds':timestamp,'scene_id':temporal.scene,'scene_boundary':cut,'detections':raw,'recovered_detections':extra,'display_detections':visible,'feature_events':{'fire':events},'alarm_eligible':any(e['severity']=='CRITICAL' for e in events),'assessment':'fire_suspected' if any(e['severity']=='CRITICAL' for e in events) else 'pending' if visible else 'no_current_detection_not_safe'}
            rows.append(row)
            canvas = frame.copy()
            cv2.rectangle(canvas, (0, 0), (width, 82), (0, 0, 0), -1)
            title = 'FIRE SUSPECTED / REPEATED EVIDENCE' if row['alarm_eligible'] else 'FIRE CANDIDATE / PENDING' if visible else 'NO CURRENT FIRE DETECTION / NOT SAFE'
            cv2.putText(canvas, title, (12, 25), 0, .65, (0, 180, 255) if visible else (220, 220, 220), 2)
            cv2.putText(canvas, 'HELD ALERT HAS NO OLD BOX / SMOKE NOT USED FOR ALARMS', (12, 49), 0, .48, (220, 220, 220), 1)
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
        subprocess.run([encoder, '-y', '-loglevel', 'error', '-i', str(temporary), '-c:v', 'libx264', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out / '.encoded.mp4')], check=True)
        os.replace(out / '.encoded.mp4', review)
    else:
        shutil.copy2(temporary, review)
    temporary.unlink()
    (out / 'detections.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    context = dict(camera_id=config['camera_id'],video=source.name,source_sha256=sha(source),model_version=sha(weights),config_version=hashlib.sha256(json.dumps({'settings':{k:config[k] for k in ['imgsz','proposal_confidence','display_confidence','sample_fps','recovery','temporal','scene_boundary']},'runner_sha256':sha(__file__),'fire_module_sha256':sha(ROOT/'src/fire_detection.py')},sort_keys=True).encode()).hexdigest())
    event_dir = ROOT / config['event_root']
    event_dir.mkdir(parents=True, exist_ok=True)
    exported = export_events(records,event_dir / 'events_v1.jsonl',feature='fire',context=context)
    summary = {'video_number' : 6, 'source_sha256': sha(source), 'model_sha256': sha(weights), 'samples': len(rows), 'decoded_source_frames': index, 'source_fps': fps, 'processed_fps': fps / stride, 'wall_seconds': time.monotonic() - started, 'display_confidence': config['display_confidence'], 'frames_with_detection': {label: sum(any(d['class'] == label for d in row['display_detections']) for row in rows) for label in ('fire', 'smoke')}, 'first_fire_detection_seconds': next((r['timestamp_seconds'] for r in rows if any(d['class'] == 'fire' for d in r['display_detections'])), None), 'review_sha256': sha(review), 'scope': config['event_status']}
    summary.update(first_fire_suspected_seconds=next((r['timestamp_seconds'] for r in rows if r['alarm_eligible']),None), confirmed_sample_count=sum(r['alarm_eligible'] for r in rows), scene_resets=[{'frame':r['frame_index'],'timestamp':r['timestamp_seconds'],'reason':r['scene_boundary']} for r in rows if r['scene_boundary']],risk_episode_count=len({e['track_ids'][0] for e in exported if e['alert_eligible']}), event_transition_count=len(exported))
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
