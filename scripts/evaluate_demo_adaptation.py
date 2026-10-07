"""Evaluate a demo-adapted checkpoint with unchanged tracking/thresholds."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.audit_pilot_predictions import iou

def match(items,box,key='bbox_xyxy'):
    return max([(iou(t[key],box),t) for t in items],key=lambda p:p[0],default=(0,None))

def main():
    p=argparse.ArgumentParser();p.add_argument('--weights',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise ValueError('New output required')
    args.output.mkdir(parents=True);protocol=json.loads((ROOT/'configs/review/demo-adaptation-v1-protocol.json').read_text())
    with (args.output/'evaluation.log').open('w') as log:
        for camera,video in [('reverse','2_forklift_back.mp4'),('forward','1_forklift_forward.mp4')]:
            command=[sys.executable,'scripts/run_proximity_video.py','--source','data/videos/'+video,'--output',str(args.output/camera),'--weights',str(args.weights),'--config',f'configs/cameras/{camera}-proximity.json','--demo-adapted']
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        fixed={}
        for label,data in [('scaled','logistics_scaled_filtered_v1'),('old','logistics_v6_corrected_forklift')]:
            run=args.output.name+'_'+label
            subprocess.run([sys.executable,'scripts/audit_pilot_predictions.py','--task','logistics','--data-path','data/reviewed_pilot/'+data,'--weights',str(args.weights),'--run-name',run,'--report-name','demo_adaptation_fixed.json'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            fixed[label]=json.loads((ROOT/'outputs/training'/run/'demo_adaptation_fixed.json').read_text())['class_counts']
    summary=json.loads((args.output/'reverse/summary.json').read_text());assert summary['source_sha256']==protocol['target_source_sha256']
    obs={r['frame_index']:r for r in map(json.loads,(args.output/'reverse/observations.jsonl').read_text().splitlines())};target=[]
    for gt in protocol['target_frames']:
        r=obs[gt['frame_index']];raw=[d for d in r['detections'] if d['class']=='forklift'];d,dt=match(raw,gt['forklift_xyxy']);fs,ft=match(r['forklifts'],gt['forklift_xyxy'],'detected_bbox_xyxy');ps,pt=match(r['people'],gt['worker_xyxy'],'detected_bbox_xyxy')
        events=[e for e in r['events'] if ft and pt and e.get('forklift_track_id')==ft['track_id'] and e.get('person_track_id')==pt['track_id']] if fs>=.5 and ps>=.5 else []
        target.append({'frame_index':gt['frame_index'],'timestamp_seconds':r['timestamp_seconds'],'vehicle_detected':d>=.5,'vehicle_detection_iou':d,'vehicle_confidence':dt['confidence'] if dt else None,'vehicle_tracked':fs>=.5,'vehicle_track_id':ft['track_id'] if fs>=.5 else None,'worker_tracked':ps>=.5,'worker_track_id':pt['track_id'] if ps>=.5 else None,'matched_actual_pair_events':events})
    baseline=json.loads((ROOT/'outputs/diagnostics/targeted_failure_v17/final_gate.json').read_text())['before'];checks={'vehicle_detected_8_of_8':all(t['vehicle_detected'] for t in target),'vehicle_tracked_8_of_8':all(t['vehicle_tracked'] for t in target),'worker_tracked_8_of_8':all(t['worker_tracked'] for t in target),'same_real_vehicle_id':all(t['vehicle_tracked'] for t in target) and len({t['vehicle_track_id'] for t in target})==1}
    for split in fixed:
        for cls in ['person','forklift']:checks[f'{split}_{cls}_misses_not_worse']=fixed[split][cls]['FN']<=baseline['fixed_tests'][split][cls]['FN']
    report={'weights':str(args.weights.resolve()),'weights_sha256':hashlib.sha256(args.weights.read_bytes()).hexdigest(),'checks':checks,'demo_target_pass':all(checks[k] for k in ['vehicle_detected_8_of_8','vehicle_tracked_8_of_8','worker_tracked_8_of_8','same_real_vehicle_id']),'all_checks_pass':all(checks.values()),'target':target,'fixed_tests':fixed,'baseline_fixed_tests':baseline['fixed_tests'],'demo_target_training_exposed':True,'independent_site_accuracy_claim':False,'model_promoted':False,'proximity_thresholds_changed':False}
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'checks':checks,'demo_target_pass':report['demo_target_pass']}))

if __name__=='__main__':main()
