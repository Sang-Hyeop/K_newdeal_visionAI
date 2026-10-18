"""Review current supplementary vehicle observations, then rebuild events separately."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.vehicle_recovery import VehicleRecovery, review_recovered_vehicles


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recovery_review_inputs(row, verify_body_context=False):
    """Fresh recovery candidates outrank the older movement input cache."""
    if verify_body_context:
        return row.get('movement_input_detections', row['object_detections'])
    return row['object_detections']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-body-context', action='store_true',
                        help='Recheck an older cache against wider current source images.')
    args = parser.parse_args()
    summary = json.loads((args.input / 'summary.json').read_text())
    source = Path(summary['source'])
    if sha(source) != summary['source_sha256']:
        raise ValueError('Source video changed')
    cap = cv2.VideoCapture(str(source))
    shape = (int(cap.get(4)), int(cap.get(3)))
    if min(shape) <= 0:
        raise ValueError('Cannot decode source video')
    engine = None
    if args.verify_body_context:
        import torch
        from ultralytics import YOLO
        torch.set_num_threads(4)
        profile = summary['object_review_profile']
        paths = [ROOT / profile[k] for k in ('vehicle_weights', 'vehicle_support_weights')]
        for path in paths:
            if sha(path) != summary['model_hashes'][str(path.relative_to(ROOT))]:
                raise ValueError('Vehicle model changed: ' + str(path))
        engine = VehicleRecovery(*(YOLO(path) for path in paths), profile)
    args.output.mkdir(parents=True, exist_ok=False)
    count = added = rejected = checked = vetoed = 0
    with (args.input / 'detections.jsonl').open() as src, (args.output / 'detections.jsonl').open('w') as dst:
        for line in src:
            row = json.loads(line)
            # A finalized cache retains the pre-cleanup people used by fresh recovery.
            detections = recovery_review_inputs(row, args.verify_body_context)
            if engine:
                cap.set(cv2.CAP_PROP_POS_FRAMES, row['frame_index'])
                ok, frame = cap.read()
                if not ok:
                    raise ValueError('Source ended before cached frame')
                detections = engine.verify_body_context(frame, detections)
            checked += sum('recovery_context_verification' in d for d in detections)
            detections, rejects = review_recovered_vehicles(detections, shape)
            row['object_detections'] = detections
            row['movement_input_detections'] = detections
            row.setdefault('vehicle_recovery', {})['consensus_rejected'] = rejects
            row.setdefault('rejected_object_proposals', []).extend(rejects)
            dst.write(json.dumps(row) + '\n')
            count += 1
            added += sum(d.get('model_source') == 'vehicle_recovery_current_image' for d in detections)
            rejected += len(rejects)
            vetoed += sum(d['review_reason'] == 'recovery_body_without_wider_context' for d in rejects)
            if count % 100 == 0:
                print('samples', count, 'body checks', checked, 'vetoed', vetoed, flush=True)
    cap.release()
    summary.update(status='current_vehicle_recovery', vehicle_recovery_provenance={
        **summary.get('vehicle_recovery_provenance', {}),
        'source_cache': str(args.input), 'candidate_log_sha256': sha(args.input / 'detections.jsonl'),
        'recovery_code_sha256': sha(ROOT / 'src/vehicle_recovery.py'), 'samples': count,
        'added_observations': added, 'consensus_rejected': rejected,
        'primary_minimum_confidence': .2, 'support_minimum_confidence': .25,
        'minimum_geometric_mean': .3, 'minimum_height_fraction': .08,
        'requires_current_person_context': True, 'history_is_search_only': True,
        'body_context_version': 'body-context-v1', 'body_context_checked': checked,
        'body_context_vetoed': vetoed, 'no_new_training': True})
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(count, added, rejected)


if __name__ == '__main__':
    main()
