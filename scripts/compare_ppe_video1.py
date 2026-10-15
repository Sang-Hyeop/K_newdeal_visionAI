"""Controlled PPE comparison on presentation videos using identical observed bodies/objects."""
from pathlib import Path
import sys,json,hashlib,copy,shutil,subprocess,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,torch
from src.ppe_events import PPEEvents
from src.ppe_final_detector import FinalPPEDetector
from src.ppe_person_crop import head_owner, head_matches_person
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
  for e in row['feature_events'].get('ppe', []):
   k=e['track_id'];state=e.get('severity') if e.get('observation_status')=='confirmed' else None;c['total']+=1;c[state or 'unconfirmed']+=1
   if state is None:reasons[e.get('reason','unknown')]+=1
   if e.get('observation_held'):held+=1
   if state=='WARNING' and active.get(k)!='WARNING':episodes+=1
   if k in previous and previous[k]!=state:changes+=1
   now[k]=state
  active=now;previous=now
 return dict(counts=dict(c),unconfirmed_fraction=c['unconfirmed']/c['total'] if c['total'] else None,unconfirmed_reasons=dict(reasons),held_person_samples=held,warning_episode_starts=episodes,state_changes_between_adjacent_observations=changes,denominator='repeated person-time records, not unique people or actual violations')

def tracks_from_row(row):
 if row.get('ppe_tracks'):return copy.deepcopy(row['ppe_tracks'])
 tracks=[]
 for e in row['feature_events'].get('ppe', []):
  if e.get('reason')=='person_not_observed' or not e.get('person_bbox_xyxy'):continue
  tracks.append({'track_id':e['track_id'],'detected_bbox_xyxy':list(e['person_bbox_xyxy']),'bbox_xyxy':list(e['person_bbox_xyxy']),'ppe':{'state':e.get('ppe_state','unknown'),'head_candidates':copy.deepcopy(e.get('head_candidates',[])),'rejected_candidates':[]}})
 return tracks

def assign_head_observations(tracks, heads, frame_height):
 updated=copy.deepcopy(tracks);boxes=[t['detected_bbox_xyxy'] for t in updated]
 for i,track in enumerate(updated):
  selected=[copy.deepcopy(q) for q in heads if head_owner(q['bbox_xyxy'],boxes,frame_height,upper_fraction=.35)==i]
  classes={q['class'] for q in selected}
  track['ppe']={'head_candidates':selected,'rejected_candidates':[],'state':'helmet_detected' if classes=={'helmeted_head'} else 'no_helmet_candidate' if classes=={'no_helmet_head'} else 'conflicting_evidence' if len(classes)>1 else 'unknown'}
 return updated


def save_ppe_observations(row, tracks, heads):
 # The persisted cache must contain the exact observations passed into the rule.
 row['ppe_tracks']=copy.deepcopy(tracks)
 row['head_detections']=copy.deepcopy(heads)


def detect_comparison_heads(model, frame, boxes, policy, review, tag):
 def proposals(raw, source):
  heads=[{'class':model.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'source':source,'model_sources':['baseline',tag]} for q in raw]
  return exclude_confirmed_equipment(heads,frame.shape[:2],review,frame)[0] if review else heads
 fresh=proposals(model.predict(frame),f'{tag}_full_frame');insufficient=[]
 for i,box in enumerate(boxes):
  hs=[q for q in fresh if head_owner(q['bbox_xyxy'],boxes,frame.shape[0],upper_fraction=.35)==i]
  valid={q['class'] for q in hs if q['confidence']>=policy['helmet_evidence_confidence' if q['class']=='helmeted_head' else 'no_helmet_evidence_confidence']}
  if len(valid)!=1:insufficient.append(box)
 if insufficient:fresh+=proposals(model.predict_person_context(frame,insufficient),f'{tag}_person_context')
 return fresh


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

def matched_existing(args):
 spec=VIDEO_SPECS[args.video];dest=args.output or ROOT/f'outputs/diagnostics/ppe_compare_expanded1577_2026-10-15/video{args.video}'
 report=json.loads((dest/'comparison.json').read_text());policy_file=ROOT/'configs/ppe-user-approved-policy-2026-10-15.json';weights=args.weights.resolve();baseline_weights=ROOT/'models/ppe_final/ppe_helmet_v6_960.pt'
 assert sha(spec['source'])==report['source_sha256']
 assert sha(weights)==report['new_model_sha256'] and sha(policy_file)==report['policy_file_sha256']
 policy=json.loads(policy_file.read_text());policy['require_baseline_helmet_confirmation']=True
 assert policy==report['policy'], 'Saved comparison policy differs from locked policy'
 candidate_dir=dest/args.candidate_arm;candidate_path=candidate_dir/'detections.jsonl';candidate_rows=[json.loads(l)for l in candidate_path.read_text().splitlines()]
 original=[json.loads(l)for l in (dest/'old_model_new_policy/detections.jsonl').read_text().splitlines()]
 assert len(original)==len(candidate_rows)==report['samples']
 # Repair only storage; the original rule result and review video remain byte-identical.
 repaired=0
 for row in candidate_rows:
  tracks=tracks_from_row(row);by_id={e['track_id']:e for e in row['feature_events']['ppe']}
  for track in tracks:
   event=by_id.get(track['track_id']);assert event is not None
   heads=copy.deepcopy(event.get('head_candidates',[]));classes={q['class']for q in heads}
   obs={'head_candidates':heads,'rejected_candidates':[],'state':'helmet_detected' if classes=={'helmeted_head'} else 'no_helmet_candidate' if classes=={'no_helmet_head'} else 'conflicting_evidence' if len(classes)>1 else 'unknown'}
   if track['ppe']!=obs:repaired+=1
   track['ppe']=obs
  save_ppe_observations(row,tracks,row.get('head_detections',[]))
 candidate_path.write_text(''.join(json.dumps(row)+'\n'for row in candidate_rows))
 assert stats(candidate_rows)==report['arms'][args.candidate_arm]
 fresh_name='old_model_fresh_new_policy';d=dest/fresh_name;d.mkdir(exist_ok=True)
 assert not (d/'comparison_complete.json').exists(),'Matched baseline already complete; do not overwrite it'
 torch.set_num_threads(4);baseline=FinalPPEDetector(weights=baseline_weights);candidate=FinalPPEDetector(weights=weights)
 review=json.loads(spec['review'].read_text())if spec['review']else None;tag=args.candidate_arm.replace('_new_policy','');cap=cv2.VideoCapture(str(spec['source']));h,w=int(cap.get(4)),int(cap.get(3));rate=report['processed_fps']
 frame_rows={row['frame_index']:(row,candidate_rows[i])for i,row in enumerate(original)};spot_indices={original[i]['frame_index']for i in {0,len(original)//2,len(original)-1}}
 rule=PPEEvents(policy);candidate_replay=PPEEvents(policy);rows=[];checked=[];idx=0;writer=cv2.VideoWriter(str(d/'review_raw.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),rate,(w,h));assert writer.isOpened()
 try:
  while True:
   ok,frame=cap.read()
   if not ok:break
   if idx not in frame_rows:idx+=1;continue
   oldrow,cached_candidate=frame_rows[idx];t=oldrow['timestamp_seconds'];tracks0=tracks_from_row(oldrow);boxes=[tr['detected_bbox_xyxy']for tr in tracks0]
   assert oldrow['object_detections']==cached_candidate['object_detections']
   assert [(x['track_id'],x['detected_bbox_xyxy'])for x in tracks0]==[(x['track_id'],x['detected_bbox_xyxy'])for x in cached_candidate['ppe_tracks']]
   missing=[{'track_id':e['track_id']}for e in oldrow['feature_events'].get('ppe',[])if e.get('reason')=='person_not_observed']
   # Replay every repaired candidate cache row to prove it reproduces saved events.
   replay,_=candidate_replay.update(t,cached_candidate['ppe_tracks'],missing,oldrow.get('scene_cut',False))
   vehicles=[x['bbox_xyxy']for x in oldrow['object_detections']if x['class']=='forklift']
   if spec['use_vehicle_guard']:replay=apply_ppe_vehicle_guard(replay,vehicles)
   assert replay==cached_candidate['feature_events']['ppe'],f'Candidate cache replay mismatch at {idx}'
   if idx in spot_indices:
    observed=detect_comparison_heads(candidate,frame,boxes,policy,review,tag)
    assert observed==cached_candidate['head_detections'],f'Candidate re-inference mismatch at {idx}'
    checked.append(idx)
   heads=detect_comparison_heads(baseline,frame,boxes,policy,review,'final_v6');tracks=assign_head_observations(tracks0,heads,h);row=copy.deepcopy(oldrow);save_ppe_observations(row,tracks,heads)
   events,_=rule.update(t,tracks,missing,oldrow.get('scene_cut',False))
   if spec['use_vehicle_guard']:events=apply_ppe_vehicle_guard(events,vehicles)
   row['feature_events']['ppe']=events;row.setdefault('features',{})['ppe']=feature_status(events);rows.append(row)
   groups={'ppe':events};canvas=render(frame.copy(),groups,detections=row['object_detections'])
   cv2.putText(canvas,f'VIDEO {args.video} / FRESH v6 / MATCHED PPE REVIEW / t={t:.2f}s',(12,h-14),0,.48,(0,190,255),1);writer.write(canvas)
   if len(rows)%25==0:print(f'video{args.video}: fresh baseline {len(rows)}/{len(original)}',flush=True)
   idx+=1
 finally:cap.release();writer.release()
 assert len(rows)==len(original) and len(checked)==len(spot_indices)
 (d/'detections.jsonl').write_text(''.join(json.dumps(row)+'\n'for row in rows));ff=shutil.which('ffmpeg')
 if ff:
  subprocess.run([ff,'-y','-loglevel','error','-i',str(d/'review_raw.mp4'),'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(d/'review.mp4')],check=True);(d/'review_raw.mp4').unlink()
 else:(d/'review_raw.mp4').replace(d/'review.mp4')
 records=[];previous={}
 for row in rows:
  transitions=[];now={}
  for e in row['feature_events']['ppe']:
   state=(e['severity'],e['ppe_state'],e['reason']);now[e['track_id']]=state
   if previous.get(e['track_id'])!=state:transitions.append(e)
  records.append({'frame_index':row['frame_index'],'timestamp_seconds':row['timestamp_seconds'],'events':row['feature_events']['ppe'],'transitions':transitions});previous=now
 summary=json.loads((spec['old']/'summary.json').read_text());context=dict(summary['context']);context.update(model_version=sha(baseline_weights),config_version=sha(policy_file));(d/'ppe').mkdir(exist_ok=True);export_events(records,d/'ppe/events_v1.jsonl',feature='ppe',context=context)
 report['arms'][fresh_name]=stats(rows);report['matched_search_audit']={'baseline':'fresh original frames, full-frame + conditional person context','candidate':'previous fresh inference cache; all frames replayed; fresh beginning/middle/end inference identical','candidate_cache_tracks_repaired':repaired,'candidate_replay_rows':len(rows),'candidate_fresh_verified_frames':checked,'baseline_sha256':sha(baseline_weights),'candidate_sha256':sha(weights),'policy_sha256':sha(policy_file),'non_ppe_events_preserved':all({k:v for k,v in row['feature_events'].items()if k!='ppe'}=={k:v for k,v in old['feature_events'].items()if k!='ppe'}for row,old in zip(rows,original)),'candidate_cache_sha256':sha(candidate_path),'baseline_cache_sha256':sha(d/'detections.jsonl'),'scope':'fixed pre-feature-split observed people; no correctness ground truth; videos1/4 diagnostic only'}
 (dest/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');(d/'comparison_complete.json').write_text(json.dumps(report['matched_search_audit'],indent=2)+'\n');print(json.dumps({fresh_name:report['arms'][fresh_name],args.candidate_arm:report['arms'][args.candidate_arm]},indent=2),flush=True)


def conservative_extra_heads(original_heads, extended_heads):
 # Extra crops may add reviewable no-helmet evidence, but cannot alone certify a helmet.
 kept=copy.deepcopy(original_heads);blocked=[]
 for head in extended_heads:
  if head in original_heads:continue
  if head.get('source')!='experimental_v6_upper_body':continue
  if head['class']=='helmeted_head':blocked.append(copy.deepcopy(head))
  else:kept.append(copy.deepcopy(head))
 return kept,blocked


def upper_body_audit(args):
 if args.video not in (3,5):raise ValueError('Current PPE improvement audit is restricted to videos3/5')
 spec=VIDEO_SPECS[args.video];base=ROOT/f'outputs/diagnostics/ppe_compare_expanded1577_2026-10-15/video{args.video}';comparison=json.loads((base/'comparison.json').read_text());source=spec['source'];policy_file=ROOT/'configs/ppe-user-approved-policy-2026-10-15.json';policy=json.loads(policy_file.read_text());policy['require_baseline_helmet_confirmation']=True
 assert sha(source)==comparison['source_sha256'] and sha(policy_file)==comparison['policy_file_sha256']
 baseline_dir=base/'old_model_fresh_new_policy';original=[json.loads(l)for l in(baseline_dir/'detections.jsonl').read_text().splitlines()];dest=args.output or base/'upper_body_recheck_v6';dest.mkdir(exist_ok=False)
 weights=ROOT/'models/ppe_final/ppe_helmet_v6_960.pt';assert sha(weights)==comparison['matched_search_audit']['baseline_sha256'];torch.set_num_threads(4);model=FinalPPEDetector(weights=weights);review=json.loads(spec['review'].read_text());rule=PPEEvents(policy);cap=cv2.VideoCapture(str(source));h,w=int(cap.get(4)),int(cap.get(3));rate=comparison['processed_fps'];frames={r['frame_index']:r for r in original};rows=[];trace=[];writer=cv2.VideoWriter(str(dest/'review_raw.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),rate,(1280,360));assert writer.isOpened()
 idx=0;births=0;possible_id_switches=[];previous_tracks={};warmup=Counter();seen=Counter();first={};association_issues=Counter();extra_calls=0;extra_candidates=0;original_hash=sha(baseline_dir/'detections.jsonl')
 def iou(a,b):
  area=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return area/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-area)
 try:
  while True:
   ok,frame=cap.read()
   if not ok:break
   if idx not in frames:idx+=1;continue
   old=frames[idx];t=old['timestamp_seconds'];tracks0=tracks_from_row(old);boxes=[tr['detected_bbox_xyxy']for tr in tracks0];heads=copy.deepcopy(old['head_detections']);insufficient=[]
   for i,track in enumerate(tracks0):
    hs=track['ppe']['head_candidates'];valid={q['class']for q in hs if q['confidence']>=policy['helmet_evidence_confidence'if q['class']=='helmeted_head'else'no_helmet_evidence_confidence']}
    if len(valid)!=1:insufficient.append(boxes[i])
    if not hs:
     for q in heads:
      if head_matches_person(q['bbox_xyxy'],boxes[i],h) and head_owner(q['bbox_xyxy'],boxes,h)!=i:association_issues['compatible_head_owned_elsewhere']+=1
    key=track['track_id'];seen[key]+=1
    if key not in first:
     births+=1;first[key]=t
     if not old.get('scene_cut',False):
      matches=[(old_id,iou(boxes[i],b))for old_id,b in previous_tracks.items()if old_id not in {tr['track_id']for tr in tracks0} and iou(boxes[i],b)>.5]
      if len(matches)==1:possible_id_switches.append({'timestamp_seconds':t,'old_id':matches[0][0],'new_id':key,'iou':matches[0][1]})
   if insufficient:
    extra_calls+=len(insufficient);extra=[{'class':model.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'source':'experimental_v6_upper_body','model_sources':['baseline','final_v6']}for q in model.predict_upper_body_context(frame,insufficient)];extra,_=exclude_confirmed_equipment(extra,(h,w),review,frame);extra_candidates+=len(extra);heads+=extra
   tracks=assign_head_observations(tracks0,heads,h);missing=[{'track_id':e['track_id']}for e in old['feature_events']['ppe']if e.get('reason')=='person_not_observed'];events,_=rule.update(t,tracks,missing,old.get('scene_cut',False));events=apply_ppe_vehicle_guard(events,[x['bbox_xyxy']for x in old['object_detections']if x['class']=='forklift']);row=copy.deepcopy(old);save_ppe_observations(row,tracks,heads);row['feature_events']['ppe']=events;row['features']['ppe']=feature_status(events);rows.append(row)
   by={e['track_id']:e for e in events}
   for e in old['feature_events']['ppe']:
    if e['observation_status']!='confirmed':warmup['initial_lt3_body_observations'if seen[e['track_id']]<3 else'after_body_warmup']+=1
    q=by[e['track_id']]
    if (e['severity'],e['observation_status'])!=(q['severity'],q['observation_status']):trace.append({'frame_index':idx,'timestamp_seconds':t,'track_id':e['track_id'],'baseline':e,'upper_body':q})
   previous_tracks={tr['track_id']:tr['detected_bbox_xyxy']for tr in tracks0}
   left=render(frame.copy(),{'ppe':old['feature_events']['ppe']},detections=old['object_detections']);right=render(frame.copy(),{'ppe':events},detections=old['object_detections']);canvas=__import__('numpy').hstack([cv2.resize(left,(640,360)),cv2.resize(right,(640,360))]);cv2.rectangle(canvas,(0,0),(1280,27),(15,15,15),-1);cv2.putText(canvas,f'v6 MATCHED BASELINE / t={t:.2f}',(8,19),0,.5,(255,255,255),1);cv2.putText(canvas,'v6 + UPPER BODY / SAME RULES',(648,19),0,.5,(255,255,255),1);writer.write(canvas)
   if len(rows)%100==0:print(f'video{args.video}: upper body {len(rows)}/{len(original)}',flush=True)
   idx+=1
 finally:cap.release();writer.release()
 assert len(rows)==len(original) and sha(baseline_dir/'detections.jsonl')==original_hash
 assert all({k:v for k,v in row['feature_events'].items()if k!='ppe'}=={k:v for k,v in old['feature_events'].items()if k!='ppe'}and row['object_detections']==old['object_detections']for row,old in zip(rows,original))
 for row in rows:
  by={e['track_id']:e for e in row['feature_events']['ppe']}
  for tr in row['ppe_tracks']:assert tr['ppe']['head_candidates']==by[tr['track_id']].get('head_candidates',[])
 (dest/'detections.jsonl').write_text(''.join(json.dumps(row)+'\n'for row in rows));(dest/'changes.json').write_text(json.dumps(trace,indent=2)+'\n')
 changes=Counter()
 for case in trace:
  a,b=case['baseline'],case['upper_body'];changes['coverage_gain'if a['observation_status']!='confirmed'and b['observation_status']=='confirmed'else'coverage_loss'if a['observation_status']=='confirmed'and b['observation_status']!='confirmed'else'confirmed_class_change']+=1
 report={'status':'experimental_not_promoted','presentation_video':args.video,'baseline':stats(original),'upper_body':stats(rows),'changes':dict(changes),'crop_rule':{'left_right_person_width':.4,'top_person_height':.15,'bottom_from_person_top_height':.6,'imgsz':640,'proposal_confidence':.15,'only_insufficient_current_heads':True},'head_owner_geometry_changed':False,'body_ids_changed':False,'policy_sha256':sha(policy_file),'model_sha256':sha(weights),'source_sha256':sha(source),'extra_person_crop_calls':extra_calls,'extra_raw_head_candidates':extra_candidates,'person_track_births':births,'possible_adjacent_id_switches':possible_id_switches,'unconfirmed_body_warmup':dict(warmup),'association_diagnostic':dict(association_issues),'limitations':'Same repeatedly observed development videos; unknown reduction is not correctness. Adjacent ID switches are IoU hypotheses, not verified identity. No policy thresholds, model, body geometry or IDs changed.'}
 (dest/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');ff=shutil.which('ffmpeg')
 if ff:
  subprocess.run([ff,'-y','-loglevel','error','-i',str(dest/'review_raw.mp4'),'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(dest/'review.mp4')],check=True);(dest/'review_raw.mp4').unlink()
 else:(dest/'review_raw.mp4').replace(dest/'review.mp4')
 print(json.dumps(report,indent=2),flush=True)


def stability_audit(args):
 from src.person_tracker import PersonTracker
 if args.video not in (3,5):raise ValueError('Stability audit uses current PPE videos3/5')
 spec=VIDEO_SPECS[args.video];base=ROOT/f'outputs/diagnostics/ppe_compare_expanded1577_2026-10-15/video{args.video}';source=spec['source'];original=[json.loads(l)for l in(base/'old_model_fresh_new_policy/detections.jsonl').read_text().splitlines()];upper=[json.loads(l)for l in(base/'upper_body_recheck_v6/detections.jsonl').read_text().splitlines()];summary=json.loads((base/'comparison.json').read_text());policy_file=ROOT/'configs/ppe-user-approved-policy-2026-10-15.json';policy=json.loads(policy_file.read_text());policy['require_baseline_helmet_confirmation']=True
 assert sha(policy_file)==summary['policy_file_sha256']and sha(source)==summary['source_sha256'];assert len(original)==len(upper)
 dest=args.output or base/'stability_guard_v6';dest.mkdir(exist_ok=False);cap=cv2.VideoCapture(str(source));h,w=int(cap.get(4)),int(cap.get(3));rate=summary['processed_fps'];torch.set_num_threads(4)
 arms={'score_fused_baseline':(True,False),'geometry_tracking_only':(False,False),'guarded_crop_only':(True,True),'geometry_tracking_guarded_crop':(False,True)}
 trackers={k:PersonTracker(rate,expose_current_candidates=True,fuse_score=fuse)for k,(fuse,_)in arms.items()};rules={k:PPEEvents(policy)for k in arms};rows={k:[]for k in arms};ids={k:set()for k in arms};associations=[];blocked_count=0;frames={row['frame_index']:i for i,row in enumerate(original)};idx=0;writer=cv2.VideoWriter(str(dest/'review_raw.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),rate,(1280,360));assert writer.isOpened()
 try:
  while True:
   ok,frame=cap.read()
   if not ok:break
   if idx not in frames:idx+=1;continue
   i=frames[idx];old=original[i];t=old['timestamp_seconds'];people=[{'class':'person','confidence':tr.get('confidence',1.),'bbox_xyxy':tr['detected_bbox_xyxy']}for tr in old['ppe_tracks']];guarded,blocked=conservative_extra_heads(old['head_detections'],upper[i]['head_detections']);blocked_count+=len(blocked)
   for arm,(_,use_crop)in arms.items():
    tracks,_=trackers[arm].update(t,people,(h,w),old.get('scene_cut',False));assert sorted(tr['detected_bbox_xyxy']for tr in tracks)==sorted(tr['bbox_xyxy']for tr in people),'Tracking changed observed bodies'
    heads=guarded if use_crop else old['head_detections'];tracks=assign_head_observations(tracks,heads,h);events,_=rules[arm].update(t,tracks,(),old.get('scene_cut',False));events=apply_ppe_vehicle_guard(events,[d['bbox_xyxy']for d in old['object_detections']if d['class']=='forklift']);row=copy.deepcopy(old);save_ppe_observations(row,tracks,heads);row['feature_events']['ppe']=events;row['features']['ppe']=feature_status(events);rows[arm].append(row);ids[arm].update(tr['track_id']for tr in tracks)
    associations.extend({'frame_index':idx,'timestamp_seconds':t,'arm':arm,'old_track_id':p['track_id'],'new_track_id':q['track_id'],'bbox_xyxy':p['detected_bbox_xyxy']}for p in old['ppe_tracks']for q in tracks if p['detected_bbox_xyxy']==q['detected_bbox_xyxy'])
   left=render(frame.copy(),{'ppe':rows['score_fused_baseline'][-1]['feature_events']['ppe']},detections=old['object_detections']);right=render(frame.copy(),{'ppe':rows['geometry_tracking_guarded_crop'][-1]['feature_events']['ppe']},detections=old['object_detections']);canvas=__import__('numpy').hstack([cv2.resize(left,(640,360)),cv2.resize(right,(640,360))]);cv2.rectangle(canvas,(0,0),(1280,27),(15,15,15),-1);cv2.putText(canvas,f'v6 CONTROL / t={t:.2f}',(8,19),0,.5,(255,255,255),1);cv2.putText(canvas,'GEOMETRY TRACKING + GUARDED CROP',(648,19),0,.5,(255,255,255),1);writer.write(canvas)
   if i%200==0:print(f'video{args.video}: stability {i}/{len(original)}',flush=True)
   idx+=1
 finally:cap.release();writer.release()
 assert stats(rows['score_fused_baseline'])==stats(original),'Control replay differs from original baseline'
 changes=[]
 for old,new in zip(rows['score_fused_baseline'],rows['geometry_tracking_guarded_crop']):
  by={tuple(e['person_bbox_xyxy']):e for e in new['feature_events']['ppe']}
  for e in old['feature_events']['ppe']:
   q=by[tuple(e['person_bbox_xyxy'])]
   if(e['severity'],e['observation_status'])!=(q['severity'],q['observation_status']):changes.append({'frame_index':old['frame_index'],'timestamp_seconds':old['timestamp_seconds'],'baseline':e,'combined':q})
 (dest/'changes.json').write_text(json.dumps(changes,indent=2)+'\n');(dest/'id_associations.jsonl').write_text(''.join(json.dumps(x)+'\n'for x in associations))
 report={'status':'experimental_not_promoted','video':args.video,'policy_sha256':sha(policy_file),'source_sha256':sha(source),'body_observations_identical':True,'model_weights_changed':False,'PPE_thresholds_changed':False,'helmet_guard':'Experimental crop-only helmet evidence is retained as blocked diagnostics, never used to create SAFE. Original source helmet evidence remains available.','blocked_crop_helmet_proposals':blocked_count,'arms':{},'limitations':['Lower ID count is continuity evidence, not IDF1/identity accuracy. Tracking association can still swap nearby people.','No transfer or merge of stored PPE states between IDs. Every arm replays the original timeline and resets normally.','Fixed observed person boxes and all proposals reused; candidate geometry and source times do not change.']}
 for arm,arm_rows in rows.items():
  d=dest/arm;d.mkdir();(d/'detections.jsonl').write_text(''.join(json.dumps(row)+'\n'for row in arm_rows));report['arms'][arm]={**stats(arm_rows),'unique_track_ids':len(ids[arm])}
 for name in ['new_safe','new_warning','coverage_loss','confirmed_class_change']:report[name]=sum((c['combined']['severity']=='SAFE'and c['baseline']['severity']!='SAFE')if name=='new_safe'else(c['combined']['severity']=='WARNING'and c['baseline']['severity']!='WARNING')if name=='new_warning'else(c['combined']['observation_status']!='confirmed'and c['baseline']['observation_status']=='confirmed')if name=='coverage_loss'else(c['combined']['observation_status']=='confirmed'and c['baseline']['observation_status']=='confirmed'and c['combined']['severity']!=c['baseline']['severity'])for c in changes)
 (dest/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');ff=shutil.which('ffmpeg')
 if ff:
  subprocess.run([ff,'-y','-loglevel','error','-i',str(dest/'review_raw.mp4'),'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(dest/'review.mp4')],check=True);(dest/'review_raw.mp4').unlink()
 else:(dest/'review_raw.mp4').replace(dest/'review.mp4')
 print(json.dumps(report,indent=2),flush=True)


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--video',type=int,choices=sorted(VIDEO_SPECS),default=1)
 parser.add_argument('--output',type=Path,default=None)
 parser.add_argument('--weights',type=Path,default=ROOT/'models/experiments/ppe_expanded_1577/weights/best.pt')
 parser.add_argument('--candidate-arm',default='expanded1577_new_policy')
 parser.add_argument('--stability-audit',action='store_true',help='Four-arm controlled tracking continuity and crop-only helmet guard audit')
 parser.add_argument('--upper-body-audit',action='store_true',help='Experimental v6 upper-body recheck with locked policy, fixed bodies and unchanged head assignment')
 parser.add_argument('--matched-existing',action='store_true',help='Repair saved candidate observations, verify fresh candidate samples and add a fully re-inferred baseline to the existing comparison')
 args=parser.parse_args()
 if args.stability_audit:return stability_audit(args)
 if args.upper_body_audit:return upper_body_audit(args)
 if args.matched_existing:return matched_existing(args)
 if args.video in (1,4):parser.error('PPE is disabled in current presentation videos 1/4; use --matched-existing for the preserved diagnostic comparison')
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
 baseline_weights=ROOT/'models/ppe_final/ppe_helmet_v6_960.pt'
 baseline_model=FinalPPEDetector(weights=baseline_weights)
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
   for n,rule in rules.items():
    row=copy.deepcopy(oldrow);tracks=tracks_from_row(oldrow);current={tr['track_id'] for tr in tracks}
    missing=[{'track_id':e['track_id']} for e in oldrow['feature_events'].get('ppe', []) if e.get('reason')=='person_not_observed' and e['track_id'] not in current]
    active_model=model if n==candidate else baseline_model
    active_tag=tag if n==candidate else 'final_v6'
    fresh=detect_comparison_heads(active_model,frame,boxes,policy,review,active_tag)
    tracks=assign_head_observations(tracks,fresh,h)
    save_ppe_observations(row,tracks,fresh)
    events,_=rule.update(t,tracks,missing,oldrow.get('scene_cut',False))
    if spec['use_vehicle_guard']:
     events=apply_ppe_vehicle_guard(events,[q['bbox_xyxy'] for q in row['object_detections'] if q['class']=='forklift'])
    row['feature_events']['ppe']=events
    row['features']=row.get('features') or {}
    row['features']['ppe']=feature_status(events)
    if args.video==2:
     canvas=draw_video2(frame,row,cfg,events,row['object_detections'])
    elif args.video in {4,5}:
     groups={**{k:row['feature_events'][k] for k in kept if k in row['feature_events']},'ppe':events}
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
 scope=f"Both PPE models freshly inferred with identical full-frame and conditional person-context search. PPE-only controlled comparison on presentation video {args.video}: old person/object detections reused; new PPE inference on original frames; existing {kept_label} unchanged. No independent correctness ground truth."
 report={'presentation_video':args.video,'source_sha256':sha(source),'old_run':str(old),'policy':policy,'policy_file_sha256':sha(ROOT/'configs/ppe-user-approved-policy-2026-10-15.json'),'new_model':str(weights),'new_model_sha256':sha(weights),'samples':len(original),'processed_fps':rate,'same_person_and_vehicle_observations':True,'scope':scope,'both_models_fresh_same_search':True,'baseline_model_sha256':sha(baseline_weights),'arms':{'original':stats(original)}}
 for n,rows in results.items():
  assert len(rows)==len(original)
  assert all(r['object_detections']==o['object_detections'] for r,o in zip(rows,original))
  for key in kept:assert all(r['feature_events'][key]==o['feature_events'][key] for r,o in zip(rows,original))
  d=dest/n;(d/'detections.jsonl').write_text(''.join(json.dumps(a)+'\n' for a in rows));report['arms'][n]=stats(rows)
  records=[];previous={}
  for row in rows:
   transitions=[];now={}
   for e in row['feature_events'].get('ppe', []):
    state=(e['severity'],e['ppe_state'],e['reason']);now[e['track_id']]=state
    if previous.get(e['track_id'])!=state:transitions.append(e)
   records.append({'frame_index':row['frame_index'],'timestamp_seconds':row['timestamp_seconds'],'events':row['feature_events']['ppe'],'transitions':transitions});previous=now
  context=dict(summary['context']);context['model_version']=sha(weights) if n==candidate else sha(baseline_weights);context['config_version']=report['policy_file_sha256'];(d/'ppe').mkdir();export_events(records,d/'ppe/events_v1.jsonl',feature='ppe',context=context)
  ff=shutil.which('ffmpeg')
  if ff:
   subprocess.run([ff,'-y','-loglevel','error','-i',str(d/'review_raw.mp4'),'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(d/'review.mp4')],check=True);(d/'review_raw.mp4').unlink()
  else:(d/'review_raw.mp4').rename(d/'review.mp4')
 (dest/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['arms'],indent=2),flush=True)
if __name__=='__main__':main()
