"""Reproduce the three-arm video1 PPE comparison using identical observed bodies/objects."""
from pathlib import Path
import sys,json,hashlib,copy,shutil,subprocess,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,torch
from src.ppe_events import PPEEvents
from src.ppe_final_detector import FinalPPEDetector
from src.ppe_person_crop import head_owner
from src.ppe_vehicle_guard import apply_ppe_vehicle_guard
from src.detection_review_profile import exclude_confirmed_equipment
from src.scenario_render import render
from src.feature_status import feature_status
from src.event_contract import export_events
from collections import Counter

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stats(rows):
 c=Counter();reasons=Counter();episodes=0;active={};held=0;changes=0;previous={}
 for row in rows:
  now={}
  for e in row['feature_events']['ppe']:
   k=e['track_id'];state=e.get('severity') if e.get('observation_status')=='confirmed' else None;c['total']+=1;c[state or 'unconfirmed']+=1
   if state is None:reasons[e.get('reason','unknown')]+=1
   if e.get('observation_held'):held+=1
   if state=='WARNING' and active.get(k)!='WARNING':episodes+=1
   if k in previous and previous[k]!=state:changes+=1
   now[k]=state
  active=now;previous=now
 return dict(counts=dict(c),unconfirmed_fraction=c['unconfirmed']/c['total'] if c['total'] else None,unconfirmed_reasons=dict(reasons),held_person_samples=held,warning_episode_starts=episodes,state_changes_between_adjacent_observations=changes,denominator='repeated person-time records, not unique people or actual violations')

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'outputs/diagnostics/ppe_compare_2026-10-15/video1');args=parser.parse_args()
 torch.set_num_threads(4)
 old=ROOT/'outputs/diagnostics/presentation1_equipment_corrected_2026-10-14/video1';summary=json.loads((old/'summary.json').read_text());original=[json.loads(l) for l in (old/'detections.jsonl').read_text().splitlines()]
 source=ROOT/'data/videos/1_forklift_worker_collision_risk.mp4';assert sha(source)==summary['source_sha256']
 policy=json.loads((ROOT/'configs/ppe-user-approved-policy-2026-10-15.json').read_text());policy['require_baseline_helmet_confirmation']=True
 review=json.loads((ROOT/'configs/video2-object-review.json').read_text());weights=ROOT/'models/experiments/ppe_head63_finetune/weights/best.pt'
 model=FinalPPEDetector(weights=weights)
 dest=args.output;dest.mkdir(parents=True,exist_ok=False)
 rules={n:PPEEvents(policy) for n in ['old_model_new_policy','head63_new_policy']};results={n:[] for n in rules}
 frames={a['frame_index']:a for a in original};cap=cv2.VideoCapture(str(source));fps=cap.get(cv2.CAP_PROP_FPS);h=int(cap.get(4));w=int(cap.get(3));rate=summary['processed_fps'];writers={}
 for n in rules:
  d=dest/n;d.mkdir();writers[n]=cv2.VideoWriter(str(d/'review_raw.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),rate,(w,h));assert writers[n].isOpened()
 idx=0
 try:
  while True:
   ok,frame=cap.read()
   if not ok:break
   if idx not in frames:idx+=1;continue
   oldrow=frames[idx];t=oldrow['timestamp_seconds'];boxes=[tr['detected_bbox_xyxy'] for tr in oldrow['ppe_tracks']]
   fresh=[{'class':model.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'source':'head63_full_frame','model_sources':['baseline','head63_finetuned']} for q in model.predict(frame)]
   fresh,_=exclude_confirmed_equipment(fresh,(h,w),review,frame)
   # Keep geometry fixed; recheck only people without sufficient head evidence.
   insufficient=[]
   for i,box in enumerate(boxes):
    hs=[q for q in fresh if head_owner(q['bbox_xyxy'],boxes,h,upper_fraction=.35)==i]
    valid={q['class'] for q in hs if q['confidence']>=policy['helmet_evidence_confidence' if q['class']=='helmeted_head' else 'no_helmet_evidence_confidence']}
    if len(valid)!=1:insufficient.append(box)
   if insufficient:
    extra=[{'class':model.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'source':'head63_person_context','model_sources':['baseline','head63_finetuned']} for q in model.predict_person_context(frame,insufficient)]
    extra,_=exclude_confirmed_equipment(extra,(h,w),review,frame);fresh+=extra
   for n,rule in rules.items():
    row=copy.deepcopy(oldrow);tracks=row['ppe_tracks'];current={tr['track_id'] for tr in tracks};missing=[{'track_id':e['track_id']} for e in oldrow['feature_events']['ppe'] if e.get('reason')=='person_not_observed' and e['track_id'] not in current]
    if n=='head63_new_policy':
     for i,tr in enumerate(tracks):
      selected=[q for q in fresh if head_owner(q['bbox_xyxy'],boxes,h,upper_fraction=.35)==i];classes={q['class'] for q in selected};tr['ppe']={'head_candidates':selected,'rejected_candidates':[],'state':'helmet_detected' if classes=={'helmeted_head'} else 'no_helmet_candidate' if classes=={'no_helmet_head'} else 'conflicting_evidence' if len(classes)>1 else 'unknown'}
     row['head_detections']=fresh
    events,_=rule.update(t,tracks,missing,oldrow.get('scene_cut',False));events=apply_ppe_vehicle_guard(events,[q['bbox_xyxy'] for q in row['object_detections'] if q['class']=='forklift'])
    row['feature_events']['ppe']=events;row['features']['ppe']=feature_status(events);results[n].append(row)
    canvas=render(frame.copy(),row['feature_events'],detections=row['object_detections'],proximity_warning_ratio=summary['camera_config'].get('warning_ratio',1.6),include_other_safe_people=True)
    cv2.putText(canvas,f'VIDEO 1 / {n} / t={t:.2f}s / UNCALIBRATED DISTANCE',(12,h-14),0,.5,(0,190,255),1)
    for e in events:
     if e.get('observation_held') and e.get('person_bbox_xyxy'):
      x,y,_,_=map(int,e['person_bbox_xyxy']);cv2.putText(canvas,'PPE HOLD <=0.6s',(x,max(140,y+30)),0,.45,(0,190,255),2)
    writers[n].write(canvas)
    if len(results[n]) in [1,26,51,76]:cv2.imwrite(str(dest/n/f'preview_{len(results[n])-1}.jpg'),canvas)
   if len(results['head63_new_policy'])%25==0:print(f'video1: {len(results["head63_new_policy"])} samples / {t:.1f}s',flush=True)
   idx+=1
 finally:
  cap.release()
  for writer in writers.values():writer.release()
 report={'source_sha256':sha(source),'old_run':str(old),'policy':policy,'policy_file_sha256':sha(ROOT/'configs/ppe-user-approved-policy-2026-10-15.json'),'new_model_sha256':sha(weights),'samples':len(original),'processed_fps':rate,'same_person_and_vehicle_observations':True,'scope':'PPE-only controlled comparison: old object/person detections reused with source hash and frame index checks; new PPE inference on original frames; existing proximity events unchanged. No independent correctness ground truth.','arms':{'original':stats(original)}}
 for n,rows in results.items():
  assert len(rows)==len(original)
  assert all(r['object_detections']==o['object_detections'] and r['feature_events']['proximity']==o['feature_events']['proximity'] for r,o in zip(rows,original))
  d=dest/n;(d/'detections.jsonl').write_text(''.join(json.dumps(a)+'\n' for a in rows));report['arms'][n]=stats(rows)
  records=[];previous={}
  for row in rows:
   transitions=[];now={}
   for e in row['feature_events']['ppe']:
    state=(e['severity'],e['ppe_state'],e['reason']);now[e['track_id']]=state
    if previous.get(e['track_id'])!=state:transitions.append(e)
   records.append({'frame_index':row['frame_index'],'timestamp_seconds':row['timestamp_seconds'],'events':row['feature_events']['ppe'],'transitions':transitions});previous=now
  context=dict(summary['context']);context['model_version']=sha(weights) if n=='head63_new_policy' else context['model_version'];context['config_version']=report['policy_file_sha256'];(d/'ppe').mkdir();export_events(records,d/'ppe/events_v1.jsonl',feature='ppe',context=context)
  ff=shutil.which('ffmpeg')
  if ff:
   subprocess.run([ff,'-y','-loglevel','error','-i',str(d/'review_raw.mp4'),'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(d/'review.mp4')],check=True);(d/'review_raw.mp4').unlink()
  else:(d/'review_raw.mp4').rename(d/'review.mp4')
 (dest/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['arms'],indent=2),flush=True)
if __name__=='__main__':main()
