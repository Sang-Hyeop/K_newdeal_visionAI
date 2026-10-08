"""One saved-video workflow: independent rules, PPE on every scenario, real detections only."""
from pathlib import Path
import argparse,json,sys,os,hashlib,math
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import torch,cv2,numpy as np
from ultralytics import YOLO
from src.object_recall_ensemble import ObjectRecallEnsemble
from src.ppe_recall_ensemble import PPERecallEnsemble
from src.ppe_person_crop import infer_person_ppe,head_owner
from src.ppe_tiled_inference import infer_tiled_heads
from src.ppe_head_context import refine_weak_heads
from src.ppe_events import PPEEvents
from src.ppe_unassigned_heads import UnassignedHeadEvents
from src.person_tracker import PersonTracker
from src.tracked_proximity import TrackedProximity
from src.tracked_zone import TrackedZone
from src.scenario_zone import ScenarioZone,mark_uncertain_lane_events
from src.forklift_proximity import ForkliftProximity
from src.hoodie_guard import apply_hood_guard,predict_hood_detections
from src.ppe_vehicle_guard import apply_ppe_vehicle_guard
from src.scenario_render import exclude_driver_overlap_pairs, render
from src.feature_status import feature_status
from src.detection_review_profile import predict_review_objects,select_review_objects
from src.event_contract import export_events

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--forklift-specialist',type=Path);p.add_argument('--forklift-additional-weights',type=Path,nargs='+',default=[]);p.add_argument('--forklift-geometric-association',action='store_true');p.add_argument('--forklift-specialist-imgsz',type=int,nargs='+',default=[640]);p.add_argument('--object-review-cache',type=Path);p.add_argument('--ppe-profile',type=Path,default=ROOT/'configs/demo-ppe-model.json');p.add_argument('--videos',type=int,nargs='+',default=list(range(1,8)));p.add_argument('--output',type=Path,required=True);p.add_argument('--sample-fps',type=float,default=5);p.add_argument('--append',action='store_true');p.add_argument('--reuse-run',type=Path);p.add_argument('--ppe-search',choices=['full_recall','person_context'],default='full_recall');p.add_argument('--hood-auxiliary',action='store_true');p.add_argument('--reuse-hood-run',type=Path);a=p.parse_args()
 if (a.output.exists()and not a.append)or any((a.output/f'video{n}').exists()for n in a.videos)or len(set(a.videos))!=len(a.videos)or any(n not in range(1,8)for n in a.videos)or not math.isfinite(a.sample_fps)or a.sample_fps<=0:raise ValueError('New output, valid videos and positive FPS required')
 if any(size<=0 or size%32 for size in a.forklift_specialist_imgsz):raise ValueError('Specialist image sizes must be positive multiples of32')
 if a.forklift_specialist and not set(a.videos)<= {2,3}:raise ValueError('Factory specialist comparison is restricted to videos2/3; other camera routes remain unchanged')
 if a.forklift_additional_weights and not a.forklift_specialist:raise ValueError('Additional forklift weights require an explicit specialist route')
 if a.forklift_geometric_association and not set(a.videos)<= {2,3}:raise ValueError('Factory association review is restricted to videos2/3')
 if a.reuse_hood_run and not a.hood_auxiliary:raise ValueError('--reuse-hood-run requires --hood-auxiliary')
 torch.set_num_threads(4);manifest=json.load(open(ROOT/'configs/demo-scenarios.json'));obj=json.load(open(ROOT/'configs/demo-object-model.json'));profile=json.load(open(a.ppe_profile));policy=json.load(open(ROOT/'configs/ppe-recall-review-policy.json'));hood=json.load(open(ROOT/'configs/demo-hood-model.json'))if a.hood_auxiliary else None;paths=[obj['baseline_weights'],obj['supplement_weights'],*profile['weights'].values()];hashes={s:sha(ROOT/s)for s in paths};models=None;ppe=None;person_model=None;hood_model=None;a.output.mkdir(parents=True,exist_ok=a.append);totals=json.load(open(a.output/'manifest.json'))if a.append and (a.output/'manifest.json').exists()else []
 if hood:
  weights=ROOT/hood['weights'];assert sha(weights)==hood['weights_sha256'];hashes[hood['weights']]=hood['weights_sha256']
 specialist=None;additional_forklift_models=[]
 if a.forklift_specialist:
  from src.forklift_specialist_ensemble import supplement_forklift_records
  specialist_path=a.forklift_specialist.resolve();specialist=YOLO(str(specialist_path))
  if specialist.names!={0:'forklift'}:raise ValueError('Expected single-class forklift specialist')
  hashes[str(specialist_path.relative_to(ROOT))]=sha(specialist_path)
  for path in a.forklift_additional_weights:
   path=path.resolve();model=YOLO(str(path))
   if 'forklift'not in model.names.values():raise ValueError('Additional model must explicitly name forklift')
   hashes[str(path.relative_to(ROOT))]=sha(path);additional_forklift_models.append((model,str(path.relative_to(ROOT))))
 for n in a.videos:
  spec=next(s for s in manifest['scenarios']if s['video_number']==n);source=ROOT/'data/videos'/spec['source_name'];assert sha(source)==spec['source_sha256'];dest=a.output/f'video{n}';dest.mkdir();cap=cv2.VideoCapture(str(source));fps=cap.get(5);h,w=int(cap.get(4)),int(cap.get(3));stride=max(1,round(fps/a.sample_fps));rate=fps/stride;cached={};hood_saved={};use_hood=bool(hood and n in hood['demo_videos'])
  pcfg=json.load(open(ROOT/spec['camera_config']))if spec['camera_config']else None
  review=json.load(open(ROOT/pcfg['object_review_profile']))if n==1 and pcfg.get('object_review_profile')else None
  if review and review.get('vehicle_weights'):
   hashes[review['vehicle_weights']]=sha(ROOT/review['vehicle_weights'])
  review_rows=None;review_person_model=None
  if a.object_review_cache:
   if not review:raise ValueError('Object review cache requires a reviewed camera profile')
   metadata=json.load(open(a.object_review_cache/'metadata.json'));assert metadata['source_sha256']==spec['source_sha256']and all(hashes[k]==v for k,v in metadata['model_hashes'].items())and abs(metadata['processed_fps']-rate)<1e-9
   review_rows={r['frame_index']:r for r in map(json.loads,(a.object_review_cache/'highres.jsonl').read_text().splitlines())}
  if a.reuse_run:
   cache=a.reuse_run/f'video{n}';cs=json.load(open(cache/'summary.json'));assert cs['source_sha256']==spec['source_sha256'] and all(cs['model_hashes'].get(k)==hashes[k]for k in cs['model_hashes']if k in hashes and 'hoodie' not in k) and abs(cs['processed_fps']-rate)<1e-9;cached={r['frame_index']:{'events':r['feature_events']['ppe'],'tracks':r['ppe_tracks'],'head_detections':r['head_detections'],'object_detections':r['object_detections']}for r in map(json.loads,(cache/'detections.jsonl').read_text().splitlines())}
  elif n in[5,6]and a.sample_fps==5:
   cache=ROOT/f'outputs/diagnostics/ppe_recall_specialists_v1_video{n}_integrated';cs=json.load(open(cache/'summary.json'))
   if cs['event_context']['source_sha256']==spec['source_sha256']and all(cs['model_hashes'][k]==hashes[profile['weights'][q]]for k,q in[('objects','objects'),('ppe','ppe_baseline'),('ppe_supplement','ppe_supplement'),('helmet_specialist','helmet_specialist')]):cached={r['frame_index']:r for r in map(json.loads,(cache/'detections.jsonl').read_text().splitlines())}
  if use_hood and a.reuse_hood_run:
   prior=json.load(open(a.reuse_hood_run/f'video{n}'/'summary.json'));assert prior['source_sha256']==spec['source_sha256'] and prior['hood_weights_sha256']==hood['weights_sha256'];hood_saved={r['frame_index']:r['hood_detections']for r in map(json.loads,(a.reuse_hood_run/f'video{n}'/'detections.jsonl').read_text().splitlines())}
  if models is None and not a.reuse_run:models=ObjectRecallEnsemble(YOLO(ROOT/obj['baseline_weights']),YOLO(ROOT/obj['supplement_weights']))
  if not cached and ppe is None:
   person_model=YOLO(ROOT/profile['weights']['objects']);ppe=PPERecallEnsemble(YOLO(ROOT/profile['weights']['ppe_baseline']),YOLO(ROOT/profile['weights']['ppe_supplement']),preserve_union=True,helmet_specialist=YOLO(ROOT/profile['weights']['helmet_specialist']))
  if use_hood and hood_model is None and not hood_saved:hood_model=YOLO(str(ROOT/hood['weights']))
  pcfg=json.load(open(ROOT/spec['camera_config']))if spec['camera_config']else None
  if a.forklift_geometric_association and pcfg:pcfg={**pcfg,'forklift_tracker_fuse_score':False}
  zone=TrackedZone(pcfg,(h,w),rate)if n==4 else ScenarioZone(pcfg,(h,w),rate)if n==7 else None;prox=TrackedProximity(pcfg,rate)if n in[1,2]else TrackedProximity({**json.load(open(ROOT/'configs/cameras/forward-proximity.json')),'camera_id':'warehouse-conditional','warning_ratio':1.0,'critical_ratio':.3,'tracker_fuse_score':True},rate)if n==7 else None;vehicle_tracker=PersonTracker(rate,target_class='forklift',namespace='FF',fuse_score=not a.forklift_geometric_association)if n==3 else None;pair=ForkliftProximity()if n==3 else None;pt=PersonTracker(rate,expose_current_candidates=True);prule=PPEEvents(policy);hrule=UnassignedHeadEvents(rate,policy);rows=[];feature_rows={};laststate={};prev=None;idx=0;writer=cv2.VideoWriter(str(dest/'demo.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),rate,(w,h));hood_vetoes=0;hood_samples=0
  if not writer.isOpened():raise ValueError('Writer failed')
  try:
   while True:
    ok,frame=cap.read()
    if not ok:break
    if idx%stride:idx+=1;continue
    t=idx/fps;small=cv2.resize(frame,(96,54)).astype(np.float32)/255;cut=prev is not None and float(np.abs(small-prev).mean())>manifest['scene_cut_threshold'];prev=small;
    if a.reuse_run:assert idx in cached;detections=cached[idx]['object_detections']
    elif review:detections=[]
    else:
     prediction=models.predict(frame,conf=.1,imgsz=1280 if n in[4,7]else 640,device='cpu',verbose=False)[0];detections=[{'class':prediction.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()}for b in prediction.boxes]
    rejected_objects=[]
    if review:
     if review_rows:detections,rejected_objects=select_review_objects(review_rows[idx],(h,w),review)
     else:
      if models is None:models=ObjectRecallEnsemble(YOLO(ROOT/obj['baseline_weights']),YOLO(ROOT/obj['supplement_weights']))
      if review.get('vehicle_weights'):models.supplement=YOLO(ROOT/review['vehicle_weights']) if not getattr(models,'review_weight_loaded',False) else models.supplement;models.review_weight_loaded=True
      if review_person_model is None:review_person_model=YOLO(ROOT/profile['weights']['objects'])
      detections,rejected_objects=predict_review_objects(models,review_person_model,frame,review)
    if specialist:
     for model,model_source in [(specialist,str(a.forklift_specialist)),*additional_forklift_models]:
      for size in dict.fromkeys(a.forklift_specialist_imgsz):
       result=model.predict(frame,imgsz=size,conf=.1,device='cpu',verbose=False)[0]
       proposals=[{'class':'forklift','confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'inference_imgsz':size,'model_source':model_source}for b in result.boxes if result.names[int(b.cls.item())]=='forklift']
       detections=supplement_forklift_records(detections,proposals)
    groups={};zrow=zone.update(t,detections,(h,w),cut)if zone else None
    if zrow:mark_uncertain_lane_events(zrow['events'])
    if zrow:
     for kind in['zone_access','zone_dwell']:groups[kind]=[e for e in zrow['events']if e['event_type']==kind]
    if prox:
     proximity=prox.update(t,detections,(h,w),cut);events=proximity['events']
     if n==1:events=exclude_driver_overlap_pairs(events,pcfg.get('driver_overlap_exclusion_ratio',.8))
     if n==7:
      inside_boxes=[e['person_bbox_xyxy']for e in zrow['events']if e['event_type']=='zone_dwell'and e['inside']is True and e.get('person_bbox_xyxy')];present=bool(zrow['vehicle_lane_state']and zrow['vehicle_lane_state']['state']=='observed_in_lane')
      from src.ppe_tiled_inference import iou
      events=[e for e in events if present and e.get('person_bbox_xyxy')and any(iou(e['person_bbox_xyxy'],b)>.5 for b in inside_boxes)]
     groups['proximity']=events
    if pair:
     old=vehicle_tracker.scene;vehicles,_=vehicle_tracker.update(t,detections,(h,w),cut)
     if old!=vehicle_tracker.scene:pair.reset()
     groups['forklift_proximity']=pair.update(t,vehicles,(h,w))
    if idx in cached:
     ppe_tracks=cached[idx]['tracks'];heads=cached[idx]['head_detections'];current={v['track_id']for v in ppe_tracks};missing=[{'track_id':e['track_id']}for e in cached[idx]['events']if e.get('track_id') not in current and e.get('reason')=='person_not_observed'];ppe_events,_=prule.update(t,ppe_tracks,missing,cut);proposals=heads+[q for tr in ppe_tracks for q in tr['ppe']['head_candidates']];extra,_=hrule.update(t,proposals,[tr['detected_bbox_xyxy']for tr in ppe_tracks],(h,w),cut,body_events=ppe_events);ppe_events+=extra
    else:
     pp=person_model.predict(frame,classes=[0],conf=.1,imgsz=1280,device='cpu',verbose=False)[0];people=[{'class':'person','confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()}for b in pp.boxes];ppe_tracks,missing=pt.update(t,people,(h,w),cut);raw=ppe.predict(frame,conf=.25,imgsz=640,device='cpu',verbose=False)[0];heads=[{'class':ppe.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'source':'full_frame','model_sources':getattr(b,'model_sources',['single_ppe_model'])}for b in raw.boxes]
     if a.ppe_search=='full_recall':tiles,_=infer_tiled_heads(frame,ppe);heads+=tiles
     boxes=[v['detected_bbox_xyxy']for v in ppe_tracks];observations=infer_person_ppe(frame,boxes,ppe,full_frame_heads=heads,crop_height_fraction=1);proposals=heads+[q for o in observations for q in o['head_candidates']];heads+=refine_weak_heads(frame,proposals,ppe);proposals=heads+[q for o in observations for q in o['head_candidates']]
     for i,(track,obs)in enumerate(zip(ppe_tracks,observations)):
      selected=[q for q in proposals if head_owner(q['bbox_xyxy'],boxes,h)==i];classes={q['class']for q in selected};obs.update(head_candidates=selected,state='helmet_detected'if classes=={'helmeted_head'}else'no_helmet_candidate'if classes=={'no_helmet_head'}else'conflicting_evidence'if len(classes)>1 else'unknown');track['ppe']=obs
     ppe_events,_=prule.update(t,ppe_tracks,missing,cut);extra,_=hrule.update(t,proposals,boxes,(h,w),cut,body_events=ppe_events);ppe_events+=extra
    suppressed_ppe=[]
    if review and review.get('ppe_requires_observed_person'):
     observed_ids={tr['track_id']for tr in ppe_tracks};suppressed_ppe=[e for e in ppe_events if e.get('track_id')not in observed_ids];ppe_events=[e for e in ppe_events if e.get('track_id')in observed_ids]
    vehicle_boxes=[d['bbox_xyxy'] for d in detections if d.get('class')=='forklift']
    ppe_events=apply_ppe_vehicle_guard(ppe_events,vehicle_boxes)
    hood_detections=[]
    if use_hood:
     if hood_saved:hood_detections=hood_saved[idx]
     else:
      person_boxes=[tr.get('detected_bbox_xyxy')or tr.get('bbox_xyxy')for tr in ppe_tracks];hood_detections=predict_hood_detections(hood_model,frame,person_boxes,confidence=hood['confidence'])
     ppe_events=apply_hood_guard(ppe_events,hood_detections,minimum_confidence=hood['confidence'],minimum_iou=hood['matching_person_iou']);hood_samples+=sum(bool(e.get('hood_evidence'))for e in ppe_events);hood_vetoes+=sum(e.get('reason')=='hood_and_helmet_evidence_requires_review'for e in ppe_events)
    groups['ppe']=ppe_events;record={'frame_index':idx,'timestamp_seconds':t,'scene_cut':cut,'object_detections':detections,'ppe_tracks':ppe_tracks,'head_detections':heads,'features':{k:feature_status(v)for k,v in groups.items()},'feature_events':groups,'zone':zrow,'global_safety_status':'not_evaluated'}
    if review:record.update(rejected_object_proposals=rejected_objects,unassociated_ppe_review=suppressed_ppe)
    if use_hood:record.update(hood_detections=hood_detections,hood_auxiliary_status='experimental')
    rows.append(record)
    for feature,events in groups.items():
     old=laststate.setdefault(feature,{});transitions=[];now={}
     for e in events:
      identity=tuple(e.get('forklift_track_ids',[]))or tuple(str(e.get(k,''))for k in['track_id','person_track_id','forklift_track_id']);key=(e['event_type'],identity);state=(e.get('severity'),e.get('observation_status'),e.get('ppe_state'),e.get('inside'),e.get('reason'),e.get('risk_reason'),bool(e.get('hood_evidence')));now[key]=state
      if old.get(key)!=state:transitions.append(e)
     laststate[feature]=now;feature_rows.setdefault(feature,[]).append({'frame_index':idx,'timestamp_seconds':t,'events':events,'transitions':transitions,'scene_id':zrow['scene_id']if zrow else pt.scene,'roi_active':zrow['roi_active']if zrow else True})
    canvas=render(frame.copy(),groups,(zone,zrow)if zone else None,detections=detections if review or specialist else None,proximity_warning_ratio=pcfg.get('warning_ratio',1.6))
    if review:
     cv2.putText(canvas,f"WARNING <= {pcfg['warning_ratio']:.2f} / CRITICAL <= {pcfg['critical_ratio']:.2f} person-height gap",(12,h-34),0,.42,(230,230,230),1)
    if use_hood:
     for event in ppe_events:
      if event.get('hood_evidence'):
       d=max(event['hood_evidence'],key=lambda q:q['confidence']);x,y,aa,bb=map(int,d['bbox_xyxy']);cv2.rectangle(canvas,(x,y),(aa,bb),(255,180,0),2);cv2.putText(canvas,f"HOOD? REVIEW {d['confidence']:.2f}",(x,max(110,y-15)),0,.48,(255,180,0),1)
    cv2.putText(canvas,f'VIDEO {n} / t={t:.2f}s / DEMO-ADAPTED / METERS UNCALIBRATED',(12,h-14),0,.48,(0,190,255),1);writer.write(canvas)
    if len(rows)in[1,26,51,76]:cv2.imwrite(str(dest/f'preview_{len(rows)-1}.jpg'),canvas)
    if len(rows)%25==0:print(f'video{n}: {len(rows)} samples / {t:.1f}s',flush=True)
    idx+=1
  finally:cap.release();writer.release()
  (dest/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in rows));context={'camera_id':f'demo-video{n}','video':source.name,'source_sha256':spec['source_sha256'],'model_version':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),'config_version':hashlib.sha256(json.dumps({'spec':spec,'camera':pcfg,'ppe_policy':policy,'sample_fps':a.sample_fps,'ppe_search':a.ppe_search,'hood_auxiliary':use_hood,'object_review_profile':review,'forklift_specialist':str(a.forklift_specialist)if specialist else None,'forklift_specialist_imgsz':a.forklift_specialist_imgsz if specialist else None,'forklift_geometric_association':a.forklift_geometric_association,'forklift_additional_weights':[str(p)for p in a.forklift_additional_weights]},sort_keys=True).encode()).hexdigest()}
  if use_hood:context['config_version']='experimental_hood_safe_veto_v1';context['model_version']=hashlib.sha256((context['model_version']+hood['weights_sha256']).encode()).hexdigest()
  counts={}
  for feature,records in feature_rows.items():
   directory=dest/feature;directory.mkdir();export_events(records,directory/'events_v1.jsonl',feature=feature,context=context);counts[feature]={state:sum(feature_status(r['events'])['display_state']==state for r in records)for state in['SAFE','WARNING','CRITICAL','UNKNOWN']}
  summary={'source':str(source),'source_sha256':spec['source_sha256'],'video_number':n,'samples':len(rows),'processed_fps':rate,'ppe_enabled':True,'forklift_geometric_association':a.forklift_geometric_association,'ppe_cache_reused':bool(cached),'all_real_inference_reused_from':str(a.reuse_run)if a.reuse_run else None,'ppe_search':a.ppe_search,'features':counts,'context':context,'model_hashes':hashes,'camera_config':pcfg,'limitations':['Sampled frames; zero misses not proven for unseen scenes','No calibrated meter distance','Hoods and missing detections remain UNKNOWN','PPE WARNING is review candidate, not verified violation','ROI floor proxies and geometry require review; scene cuts disable ROI','Hood auxiliary is experimental; Normal never means PPE safe']}
  if specialist:summary.update(forklift_specialist=str(a.forklift_specialist),forklift_specialist_imgsz=a.forklift_specialist_imgsz,forklift_additional_weights=[str(p)for p in a.forklift_additional_weights],status='experimental_not_promoted',all_real_inference_reused_from=None,ppe_inference_reused_from=str(a.reuse_run)if a.reuse_run else None)
  if review:summary.update(object_review_profile=review,object_review_cache=str(a.object_review_cache)if a.object_review_cache else None)
  if use_hood:summary.update(status='experimental_not_promoted',hood_auxiliary=True,hood_weights_sha256=hood['weights_sha256'],hood_samples=hood_samples,hood_safe_vetoes=hood_vetoes)
  (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');totals.append(summary);(a.output/'manifest.json').write_text(json.dumps(totals,indent=2)+'\n');print(f'video{n} complete',flush=True)
if __name__=='__main__':main()
