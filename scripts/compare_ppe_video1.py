"""Controlled PPE comparison on presentation videos using identical observed bodies/objects."""
from pathlib import Path
import sys,json,hashlib,copy,shutil,subprocess,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,torch
from src.ppe_events import PPEEvents
from src.ppe_final_detector import FinalPPEDetector
from src.ppe_person_crop import head_owner
from src.ppe_vehicle_guard import apply_ppe_vehicle_guard
from src.detection_review_profile import exclude_confirmed_equipment
from src.scenario_render import render, roi_overlay, COLORS
from src.feature_status import feature_status
from src.event_contract import export_events
from collections import Counter

VIDEO_SPECS={
 1:{
  'old':ROOT/'outputs/diagnostics/presentation1_equipment_corrected_2026-10-14/video1',
  'source':ROOT/'data/videos/1_forklift_worker_collision_risk.mp4',
  'review':ROOT/'configs/video1-object-review.json',
  'label':'VIDEO 1',
  'footer':'UNCALIBRATED DISTANCE',
  'preserve':'proximity',
  'use_equipment_filter':True,
  'use_vehicle_guard':True,
 },
 2:{
  'old':ROOT/'outputs/diagnostics/presentation2_intrusion_review_2026-10-14',
  'source':ROOT/'data/videos/2_restricted_zone_intrusion.mp4',
  'review':None,
  'label':'VIDEO 2',
  'footer':'AI-GENERATED DEMO',
  'preserve':'zone_access',
  'use_equipment_filter':False,
  'use_vehicle_guard':False,
 },
 3:{
  'old':ROOT/'outputs/diagnostics/presentation3_ppe_review_2026-10-14/video3',
  'source':ROOT/'data/videos/3_PPE_Helmet.mp4',
  'review':ROOT/'configs/video3-object-review.json',
  'label':'VIDEO 3',
  'footer':'PPE HELMET REVIEW',
  'preserve':None,
  'use_equipment_filter':True,
  'use_vehicle_guard':True,
 },
 4:{
  'old':ROOT/'outputs/diagnostics/presentation4_worker_corrected_final_2026-10-14/video4',
  'source':ROOT/'data/videos/4_hazard_zone_dwell.mp4',
  'review':ROOT/'configs/video4-object-review.json',
  'label':'VIDEO 4',
  'footer':'HAZARD ZONE DWELL',
  'preserve':['zone_access','zone_dwell'],
  'use_equipment_filter':True,
  'use_vehicle_guard':True,
 },
 5:{
  'old':ROOT/'outputs/diagnostics/presentation5_vehicle_rider_review_v2_2026-10-14/video5',
  'source':ROOT/'data/videos/5_Logistics Warehouse.mp4',
  'review':ROOT/'configs/video5-object-review.json',
  'label':'VIDEO 5',
  'footer':'WAREHOUSE INTEGRATED',
  'preserve':['zone_access','zone_dwell','proximity'],
  'use_equipment_filter':True,
  'use_vehicle_guard':True,
 },
}

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

def tracks_from_row(row):
 if row.get('ppe_tracks') is not None:return copy.deepcopy(row['ppe_tracks'])
 tracks=[]
 for e in row['feature_events']['ppe']:
  if e.get('reason')=='person_not_observed' or not e.get('person_bbox_xyxy'):continue
  tracks.append({'track_id':e['track_id'],'detected_bbox_xyxy':list(e['person_bbox_xyxy']),'bbox_xyxy':list(e['person_bbox_xyxy']),'ppe':{'state':e.get('ppe_state','unknown'),'head_candidates':copy.deepcopy(e.get('head_candidates',[])),'rejected_candidates':[]}})
 return tracks

def draw_video2(frame,row,cfg,ppe_events,detections):
 polygon=[[x*frame.shape[1],y*frame.shape[0]] for x,y in cfg['polygon_normalized']]
 status=feature_status(row['feature_events']['zone_access'])
 canvas=roi_overlay(frame.copy(),polygon,[],status['severity'],alpha_safe=.08,alpha_alert=.15)
 canvas=render(canvas,{'ppe':ppe_events},detections=detections)
 for e in row['feature_events']['zone_access']:
  if not e.get('person_bbox_xyxy'):continue
  x,y,xx,yy=map(int,e['person_bbox_xyxy']);color=COLORS[e['severity']]
  cv2.rectangle(canvas,(x,y),(xx,yy),color,3)
  cv2.putText(canvas,'ROI '+str(e['severity'] or 'NOT OBSERVED'),(x,max(100,y-22)),0,.55,color,2)
  if e.get('anchor_xy'):cv2.circle(canvas,tuple(map(int,e['anchor_xy'])),6,color,-1)
 h,w=canvas.shape[:2]
 cv2.rectangle(canvas,(5,40),(min(w-5,1050),100),(20,20,20),-1)
 cv2.putText(canvas,'ROI ENTRY: '+status['dashboard_state'].upper(),(12,64),0,.7,COLORS[status['severity']],2)
 cv2.putText(canvas,'INSIDE = IMMEDIATE DANGER / FOOTPOINT RULE / ROI DRAFT',(12,88),0,.5,(230,230,230),1)
 return canvas

def draw_video4(frame,row,cfg,groups,detections):
 polygon=[[x*frame.shape[1],y*frame.shape[0]] for x,y in cfg['polygon_normalized']]
 dwell=feature_status(groups.get('zone_dwell',[]))
 canvas=roi_overlay(frame.copy(),polygon,[],dwell['severity'],alpha_safe=cfg.get('roi_alpha_safe',.15),alpha_alert=cfg.get('roi_alpha_alert',.2),unknown_color=cfg.get('roi_unknown_color'),alpha_unknown=cfg.get('roi_alpha_unknown',.2))
 return render(canvas,groups,detections=detections)

def draw_video5(frame,row,cfg,groups,detections):
 h,w=frame.shape[:2]
 outer=[[x*w,y*h] for x,y in cfg['monitor_floor_normalized']]
 safe=[[[x*w,y*h] for x,y in poly] for poly in cfg.get('safe_polygons_normalized',[])]
 movement=feature_status(groups.get('zone_dwell',[])+groups.get('proximity',[]))
 canvas=roi_overlay(frame.copy(),outer,safe,movement['severity'],alpha_safe=cfg.get('roi_alpha_safe',.05),alpha_alert=cfg.get('roi_alpha_alert',.08),unknown_color=cfg.get('roi_unknown_color'),alpha_unknown=cfg.get('roi_alpha_unknown',.05),draw_outer_boundary=cfg.get('roi_draw_outer_boundary',False))
 return render(canvas,groups,detections=detections,proximity_warning_ratio=cfg.get('warning_ratio',1.0),include_other_safe_people=True,vehicle_occupancy=(row.get('proximity_tracking') or {}).get('vehicle_occupancy'))

def preserve_keys(spec):
 p=spec['preserve']
 if p is None:return []
 if isinstance(p,str):return [p]
 return list(p)

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--video',type=int,choices=sorted(VIDEO_SPECS),default=1)
 parser.add_argument('--output',type=Path,default=None)
 parser.add_argument('--weights',type=Path,default=ROOT/'models/experiments/ppe_expanded_1577/weights/best.pt')
 parser.add_argument('--candidate-arm',default='expanded1577_new_policy')
 args=parser.parse_args()
 spec=VIDEO_SPECS[args.video]
 out=args.output or (ROOT/f'outputs/diagnostics/ppe_compare_expanded1577_2026-10-15/video{args.video}')
 torch.set_num_threads(4)
 old=spec['old'];summary=json.loads((old/'summary.json').read_text());original=[json.loads(l) for l in (old/'detections.jsonl').read_text().splitlines()]
 source=spec['source']
 expected=summary.get('source_sha256') or summary.get('context',{}).get('source_sha256') or summary['camera_config']['source_sha256']
 assert sha(source)==expected, (sha(source), expected)
 policy=json.loads((ROOT/'configs/ppe-user-approved-policy-2026-10-15.json').read_text());policy['require_baseline_helmet_confirmation']=True
 review=json.loads(spec['review'].read_text()) if spec['review'] else None
 weights=args.weights.resolve();assert weights.exists(),weights
 candidate=args.candidate_arm;assert candidate!='old_model_new_policy'
 model=FinalPPEDetector(weights=weights)
 dest=out;dest.mkdir(parents=True,exist_ok=False)
 rules={n:PPEEvents(policy) for n in ['old_model_new_policy',candidate]};results={n:[] for n in rules}
 frames={a['frame_index']:a for a in original};cap=cv2.VideoCapture(str(source));h=int(cap.get(4));w=int(cap.get(3));rate=summary['processed_fps'];writers={}
 tag=candidate.replace('_new_policy','');cfg=summary['camera_config'];kept=preserve_keys(spec)
 for n in rules:
  d=dest/n;d.mkdir();writers[n]=cv2.VideoWriter(str(d/'review_raw.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),rate,(w,h));assert writers[n].isOpened()
 idx=0
 try:
  while True:
   ok,frame=cap.read()
   if not ok:break
   if idx not in frames:idx+=1;continue
   oldrow=frames[idx];t=oldrow['timestamp_seconds'];tracks0=tracks_from_row(oldrow);boxes=[tr['detected_bbox_xyxy'] for tr in tracks0]
   fresh=[{'class':model.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'source':f'{tag}_full_frame','model_sources':['baseline',tag]} for q in model.predict(frame)]
   if review:fresh,_=exclude_confirmed_equipment(fresh,(h,w),review,frame)
   # Keep geometry fixed; recheck only people without sufficient head evidence.
   insufficient=[]
   for i,box in enumerate(boxes):
    hs=[q for q in fresh if head_owner(q['bbox_xyxy'],boxes,h,upper_fraction=.35)==i]
    valid={q['class'] for q in hs if q['confidence']>=policy['helmet_evidence_confidence' if q['class']=='helmeted_head' else 'no_helmet_evidence_confidence']}
    if len(valid)!=1:insufficient.append(box)
   if insufficient:
    extra=[{'class':model.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'source':f'{tag}_person_context','model_sources':['baseline',tag]} for q in model.predict_person_context(frame,insufficient)]
    if review:extra,_=exclude_confirmed_equipment(extra,(h,w),review,frame)
    fresh+=extra
   for n,rule in rules.items():
    row=copy.deepcopy(oldrow);tracks=tracks_from_row(oldrow);current={tr['track_id'] for tr in tracks}
    missing=[{'track_id':e['track_id']} for e in oldrow['feature_events']['ppe'] if e.get('reason')=='person_not_observed' and e['track_id'] not in current]
    if n==candidate:
     for i,tr in enumerate(tracks):
      selected=[q for q in fresh if head_owner(q['bbox_xyxy'],boxes,h,upper_fraction=.35)==i];classes={q['class'] for q in selected}
      tr['ppe']={'head_candidates':selected,'rejected_candidates':[],'state':'helmet_detected' if classes=={'helmeted_head'} else 'no_helmet_candidate' if classes=={'no_helmet_head'} else 'conflicting_evidence' if len(classes)>1 else 'unknown'}
     row['head_detections']=fresh
    events,_=rule.update(t,tracks,missing,oldrow.get('scene_cut',False))
    if spec['use_vehicle_guard']:
     events=apply_ppe_vehicle_guard(events,[q['bbox_xyxy'] for q in row['object_detections'] if q['class']=='forklift'])
    row['feature_events']['ppe']=events
    row['features']=row.get('features') or {}
    row['features']['ppe']=feature_status(events)
    if args.video==2:
     canvas=draw_video2(frame,row,cfg,events,row['object_detections'])
    elif args.video in {4,5}:
     groups={**{k:row['feature_events'][k] for k in kept},'ppe':events}
     canvas=(draw_video5 if args.video==5 else draw_video4)(frame,row,cfg,groups,row['object_detections'])
    else:
     groups={'ppe':events}
     if args.video==1 and 'proximity' in row['feature_events']:groups=row['feature_events']
     canvas=render(frame.copy(),groups,detections=row['object_detections'],proximity_warning_ratio=cfg.get('warning_ratio',1.6),include_other_safe_people=True)
    cv2.putText(canvas,f"{spec['label']} / {n} / t={t:.2f}s / {spec['footer']}",(12,h-14),0,.5,(0,190,255),1)
    for e in events:
     if e.get('observation_held') and e.get('person_bbox_xyxy'):
      x,y,_,_=map(int,e['person_bbox_xyxy']);cv2.putText(canvas,'PPE HOLD <=0.6s',(x,max(140,y+30)),0,.45,(0,190,255),2)
    writers[n].write(canvas)
    previews={1:[1,26,51,76],2:[1,15,30,45],3:[1,15,30,45],4:[1,24,48,72],5:[1,218,435,653]}.get(args.video,[1,26,51,76])
    if len(results[n])+1 in previews:cv2.imwrite(str(dest/n/f'preview_{len(results[n])}.jpg'),canvas)
    results[n].append(row)
   if len(results[candidate])%25==0:print(f"video{args.video}: {len(results[candidate])} samples / {t:.1f}s",flush=True)
   idx+=1
 finally:
  cap.release()
  for writer in writers.values():writer.release()
 kept_label=', '.join(kept) if kept else 'object detections only'
 scope=f"PPE-only controlled comparison on presentation video {args.video}: old person/object detections reused; new PPE inference on original frames; existing {kept_label} unchanged. No independent correctness ground truth."
 report={'presentation_video':args.video,'source_sha256':sha(source),'old_run':str(old),'policy':policy,'policy_file_sha256':sha(ROOT/'configs/ppe-user-approved-policy-2026-10-15.json'),'new_model':str(weights),'new_model_sha256':sha(weights),'samples':len(original),'processed_fps':rate,'same_person_and_vehicle_observations':True,'scope':scope,'arms':{'original':stats(original)}}
 for n,rows in results.items():
  assert len(rows)==len(original)
  assert all(r['object_detections']==o['object_detections'] for r,o in zip(rows,original))
  for key in kept:assert all(r['feature_events'][key]==o['feature_events'][key] for r,o in zip(rows,original))
  d=dest/n;(d/'detections.jsonl').write_text(''.join(json.dumps(a)+'\n' for a in rows));report['arms'][n]=stats(rows)
  records=[];previous={}
  for row in rows:
   transitions=[];now={}
   for e in row['feature_events']['ppe']:
    state=(e['severity'],e['ppe_state'],e['reason']);now[e['track_id']]=state
    if previous.get(e['track_id'])!=state:transitions.append(e)
   records.append({'frame_index':row['frame_index'],'timestamp_seconds':row['timestamp_seconds'],'events':row['feature_events']['ppe'],'transitions':transitions});previous=now
  context=dict(summary['context']);context['model_version']=sha(weights) if n==candidate else context['model_version'];context['config_version']=report['policy_file_sha256'];(d/'ppe').mkdir();export_events(records,d/'ppe/events_v1.jsonl',feature='ppe',context=context)
  ff=shutil.which('ffmpeg')
  if ff:
   subprocess.run([ff,'-y','-loglevel','error','-i',str(d/'review_raw.mp4'),'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(d/'review.mp4')],check=True);(d/'review_raw.mp4').unlink()
  else:(d/'review_raw.mp4').rename(d/'review.mp4')
 (dest/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['arms'],indent=2),flush=True)
if __name__=='__main__':main()
