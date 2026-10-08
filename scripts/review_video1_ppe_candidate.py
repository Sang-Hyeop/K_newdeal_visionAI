"""Re-run only PPE on cached Video 1 person boxes and preserve proximity output."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.feature_status import feature_status
from src.ppe_events import PPEEvents
from src.ppe_recall_ensemble import PPERecallEnsemble
from src.ppe_tiled_inference import infer_tiled_heads
from src.ppe_head_context import refine_weak_heads
from src.ppe_unassigned_heads import UnassignedHeadEvents
from src.ppe_person_crop import infer_person_ppe, head_owner
from src.scenario_render import render


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-run', type=Path, default=ROOT/'outputs/diagnostics/video1_2026-10-08_review/video1')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate-specialist', type=Path, default=ROOT/'outputs/training/ppe_color_expansion_v3/weights/best.pt')
    parser.add_argument('--preview-indices', type=int, nargs='*', default=[0, 20, 40, 60, 75, 80])
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError(f'Output already exists: {args.output}')

    source_summary = json.loads((args.source_run/'summary.json').read_text())
    source = Path(source_summary['source'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_summary['source_sha256']:
        raise ValueError('Video 1 source hash does not match cached review')
    rows = [json.loads(line) for line in (args.source_run/'detections.jsonl').read_text().splitlines()]
    object_model = YOLO(str(ROOT/'models/pilot_v3_ppe_expansion/ppe.pt'))
    supplement_model = YOLO(str(ROOT/'models/demo_ppe_interpolated_v4/ppe.pt'))
    ppe = PPERecallEnsemble(object_model, supplement_model, preserve_union=True,
                            helmet_specialist=YOLO(str(args.candidate_specialist)))
    policy = json.loads((ROOT/'configs/ppe-recall-review-policy.json').read_text())
    rule, head_rule = PPEEvents(policy), UnassignedHeadEvents(source_summary['processed_fps'], policy)
    cap = cv2.VideoCapture(str(source))
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    args.output.mkdir(parents=True)
    writer = cv2.VideoWriter(str(args.output/'video1_ppe_v3_specialist_review.mp4'),
                             cv2.VideoWriter_fourcc(*'mp4v'), source_summary['processed_fps'], (width, height))
    if not cap.isOpened() or not writer.isOpened():
        raise RuntimeError('Could not open source video or output writer')
    ppe_feature_rows = []
    try:
        for row_index, row in enumerate(rows):
            cap.set(cv2.CAP_PROP_POS_FRAMES, row['frame_index'])
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not read frame {row['frame_index']}")
            tracks = row['ppe_tracks']
            people = [track['detected_bbox_xyxy'] for track in tracks]
            raw = ppe.predict(frame, conf=.25, imgsz=640, device='cpu', verbose=False)[0]
            heads = [{'class': ppe.names[int(box.cls.item())], 'confidence': float(box.conf.item()),
                      'bbox_xyxy': box.xyxy[0].tolist(), 'source': 'full_frame',
                      'model_sources': getattr(box, 'model_sources', ['candidate_union'])}
                     for box in raw.boxes]
            tiled, _ = infer_tiled_heads(frame, ppe)
            heads.extend(tiled)
            observations = infer_person_ppe(frame, people, ppe, full_frame_heads=heads,
                                            crop_height_fraction=1)
            proposals = heads + [candidate for observation in observations
                                 for candidate in observation['head_candidates']]
            heads.extend(refine_weak_heads(frame, proposals, ppe))
            proposals = heads + [candidate for observation in observations
                                 for candidate in observation['head_candidates']]
            for index, (track, observation) in enumerate(zip(tracks, observations)):
                selected = [candidate for candidate in proposals
                            if head_owner(candidate['bbox_xyxy'], people, height) == index]
                classes = {candidate['class'] for candidate in selected}
                observation.update(head_candidates=selected,
                                   state='helmet_detected' if classes == {'helmeted_head'} else
                                         'no_helmet_candidate' if classes == {'no_helmet_head'} else
                                         'conflicting_evidence' if len(classes) > 1 else 'unknown')
                track['ppe'] = observation
            missing = [{'track_id': event['track_id']}
                       for event in row['feature_events'].get('ppe', [])
                       if event.get('track_id') not in {track['track_id'] for track in tracks}
                       and event.get('reason') == 'person_not_observed']
            ppe_events, _ = rule.update(row['timestamp_seconds'], tracks, missing, row['scene_cut'])
            extra, _ = head_rule.update(row['timestamp_seconds'], heads, people, (height, width),
                                        row['scene_cut'], body_events=ppe_events)
            ppe_events.extend(extra)
            row['head_detections'] = heads
            row['feature_events']['ppe'] = ppe_events
            row['features']['ppe'] = feature_status(ppe_events)
            ppe_feature_rows.append({'frame_index': row['frame_index'],
                                     'timestamp_seconds': row['timestamp_seconds'],
                                     'events': ppe_events})
            groups = {'proximity': row['feature_events'].get('proximity', []), 'ppe': ppe_events}
            canvas = render(frame.copy(), groups, detections=row['object_detections'])
            cv2.putText(canvas, f"VIDEO 1 / t={row['timestamp_seconds']:.2f}s / PPE V3 SPECIALIST REVIEW",
                        (12, height-14), cv2.FONT_HERSHEY_SIMPLEX, .48, (0, 190, 255), 1)
            writer.write(canvas)
            if row_index in args.preview_indices:
                cv2.imwrite(str(args.output/f'preview_{row_index:03d}.jpg'), canvas)
    finally:
        cap.release()
        writer.release()

    (args.output/'detections.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    counts = {state: sum(feature_status(record['events'])['display_state'] == state
                         for record in ppe_feature_rows)
              for state in ('SAFE', 'WARNING', 'CRITICAL', 'UNKNOWN')}
    summary = {**source_summary, 'review': 'candidate helmet specialist; PPE rerun on cached Video 1 person boxes',
               'ppe_specialist_weights': str(args.candidate_specialist.resolve()),
               'ppe_specialist_sha256': hashlib.sha256(args.candidate_specialist.read_bytes()).hexdigest(),
               'ppe_feature_counts': counts, 'ppe_review_samples': len(rows),
               'proximity_reused_unchanged': True,
               'limitation': 'Video 1 development replay only; no independent field performance claim.'}
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({'output': str(args.output.resolve()), 'samples': len(rows),
                      'previews': args.preview_indices, 'ppe_feature_counts': counts,
                      'specialist_sha256': summary['ppe_specialist_sha256']}, indent=2))


if __name__ == '__main__':
    torch.set_num_threads(4)
    main()
