"""Saved-video ROI entry review with current detections and the shared event contract."""
from pathlib import Path
import argparse, hashlib, json, sys, os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2, numpy as np, torch
from ultralytics import YOLO
from src.person_tracker import PersonTracker
from src.zone_access import ZoneAccess
from src.ppe_final_detector import FinalPPEDetector
from src.ppe_person_crop import head_owner
from src.ppe_events import PPEEvents
from src.scenario_render import render, roi_overlay, COLORS
from src.feature_status import feature_status
from src.event_contract import export_events

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=ROOT/'configs/cameras/robot-intrusion.json');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 cfg=json.loads(a.config.read_text());source=ROOT/'data/videos'/cfg['source_name'];assert sha(source)==cfg['source_sha256'];a.output.mkdir(parents=True,exist_ok=False)
 torch.set_num_threads(4);model=YOLO(ROOT/cfg['person_weights']);ppe=FinalPPEDetector();policy=json.load(open(ROOT/'configs/ppe-recall-review-policy.json'));prule=PPEEvents(policy)
 cap=cv2.VideoCapture(str(source));fps=cap.get(5);w,h=int(cap.get(3)),int(cap.get(4));stride=max(1,round(fps/5));rate=fps/stride
 tracker=PersonTracker(rate,cfg['max_gap_seconds'],fuse_score=False);polygon=[[x*w,y*h]for x,y in cfg['polygon_normalized']];zone=ZoneAccess(polygon,min(w,h)*cfg['approach_margin_ratio'],cfg['max_gap_seconds'])
 writer=cv2.VideoWriter(str(a.output/'demo.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),rate,(w,h));assert writer.isOpened();records=[];logs={'zone_access':[],'ppe':[]};previous={'zone_access':{},'ppe':{}};idx=0;prev=None
 try:
  while True:
   ok,frame=cap.read()
   if not ok:break
   if idx%stride:idx+=1;continue
   t=idx/fps;small=cv2.resize(frame,(96,54)).astype(np.float32)/255;cut=prev is not None and float(np.abs(small-prev).mean())>.18;prev=small
   if cut:raise RuntimeError('Camera scene changed; ROI review required')
   result=model.predict(frame,classes=[0],conf=cfg['person_confidence'],imgsz=cfg['person_imgsz'],device='cpu',verbose=False)[0]
   detections=[{'class':'person','confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()}for b in result.boxes];tracks,missing=tracker.update(t,detections,(h,w));boxes=[tr['detected_bbox_xyxy']for tr in tracks]
   raw=ppe.predict(frame)+ppe.predict_person_context(frame,boxes);raw=ppe.filter(raw,cover=.8,overlap=.7);heads=[{'class':ppe.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'model_sources':['baseline','final_v6']}for q in raw]
   for i,tr in enumerate(tracks):
    selected=[q for q in heads if head_owner(q['bbox_xyxy'],boxes,h)==i];classes={q['class']for q in selected};tr['ppe']={'state':'helmet_detected'if classes=={'helmeted_head'}else'no_helmet_candidate'if classes=={'no_helmet_head'}else'conflicting_evidence'if len(classes)>1 else'unknown','head_candidates':selected}
   pe,_=prule.update(t,tracks,missing);usable=[{**tr,'bbox_xyxy':tr['detected_bbox_xyxy']}for tr in tracks if tr['detected_bbox_xyxy'][3]<h-1];events=zone.update(t,usable);byid={tr['track_id']:tr for tr in tracks}
   for e in events:
    e.update(roi_id=cfg['roi_id'],roi_polygon_normalized=cfg['polygon_normalized'],roi_review_status=cfg['roi_review_status'],reason='inside_restricted_robot_roi'if e['inside']else'approaching_restricted_robot_roi'if e['region']=='approach'else'outside_restricted_robot_roi'if e['inside']is False else'person_not_observed')
    if e['track_id']in byid:e['person_bbox_xyxy']=byid[e['track_id']]['detected_bbox_xyxy']
   groups={'zone_access':events,'ppe':pe};status=feature_status(events);canvas=roi_overlay(frame.copy(),polygon,[],status['severity'],alpha_safe=.08,alpha_alert=.15)
   canvas=render(canvas,{'ppe':pe},detections=detections)
   for e in events:
    if not e.get('person_bbox_xyxy'):continue
    x,y,xx,yy=map(int,e['person_bbox_xyxy']);color=COLORS[e['severity']];cv2.rectangle(canvas,(x,y),(xx,yy),color,3);cv2.putText(canvas,'ROI '+str(e['severity']or'NOT OBSERVED'),(x,max(100,y-22)),0,.55,color,2)
    if e.get('anchor_xy'):cv2.circle(canvas,tuple(map(int,e['anchor_xy'])),6,color,-1)
   cv2.rectangle(canvas,(5,40),(min(w-5,1050),100),(20,20,20),-1);cv2.putText(canvas,'ROI ENTRY: '+status['dashboard_state'].upper(),(12,64),0,.7,COLORS[status['severity']],2);cv2.putText(canvas,'INSIDE = IMMEDIATE DANGER / FOOTPOINT RULE / ROI DRAFT',(12,88),0,.5,(230,230,230),1)
   cv2.putText(canvas,f'VIDEO 2 / t={t:.2f}s / AI-GENERATED DEMO',(12,h-14),0,.5,(0,190,255),1);writer.write(canvas)
   records.append({'frame_index':idx,'timestamp_seconds':t,'object_detections':detections,'head_detections':heads,'feature_events':groups})
   for feature,es in groups.items():
    now={};trans=[]
    for e in es:
     key=e['track_id'];value=(e.get('severity'),e.get('observation_status'),e.get('reason'))
     if previous[feature].get(key)!=value:trans.append(e)
     now[key]=value
    previous[feature]=now;logs[feature].append({'frame_index':idx,'timestamp_seconds':t,'events':es,'transitions':trans,'scene_id':0,'roi_active':True})
   if len(records)%20==0:print(f'{len(records)} samples / {t:.1f}s',flush=True)
   idx+=1
 finally:cap.release();writer.release()
 hashes={cfg['person_weights']:sha(ROOT/cfg['person_weights']),'models/ppe_final/ppe_helmet_v6_960.pt':sha(ROOT/'models/ppe_final/ppe_helmet_v6_960.pt')};context=dict(camera_id=cfg['camera_id'],video=source.name,source_sha256=cfg['source_sha256'],model_version=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),config_version=hashlib.sha256(json.dumps({'camera':cfg,'ppe_policy':policy,'script_sha256':sha(__file__)},sort_keys=True).encode()).hexdigest())
 for feature,rows in logs.items():
  folder=a.output/feature;folder.mkdir();export_events(rows,folder/'events_v1.jsonl',feature=feature,context=context)
 (a.output/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in records));critical=[r['timestamp_seconds']for r in records if any(e['severity']=='CRITICAL'for e in r['feature_events']['zone_access'])];summary={'samples':len(records),'processed_fps':rate,'source':str(source),'context':context,'model_hashes':hashes,'camera_config':cfg,'first_critical_seconds':min(critical)if critical else None,'critical_sample_count':len(critical),'review_status':'awaiting_user_review'};(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
