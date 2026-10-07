"""Use real pre-confirmation body boxes for PPE, reusing same-frame head evidence."""
from pathlib import Path
import argparse,json,sys,hashlib,os,math
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,torch
from ultralytics import YOLO
from src.person_tracker import PersonTracker
from src.ppe_person_crop import infer_person_ppe,head_owner
from src.ppe_recall_ensemble import PPERecallEnsemble
from src.ppe_events import PPEEvents
from src.ppe_unassigned_heads import UnassignedHeadEvents
from src.event_contract import export_events

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--policy',type=Path,required=True);args=p.parse_args()
 if args.output.exists():raise ValueError('Protected output')
 torch.set_num_threads(4);summary=json.loads((args.run/'summary.json').read_text());source=Path(summary['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==summary['event_context']['source_sha256'];rows=[json.loads(v)for v in (args.run/'detections.jsonl').read_text().splitlines()];policy=json.loads(args.policy.read_text());objects=YOLO(summary['weights']['objects']);ppe=PPERecallEnsemble(YOLO(summary['weights']['ppe']),YOLO(summary['supplement_ppe_weights']),preserve_union=True,helmet_specialist=YOLO(summary['helmet_specialist_weights']))
 for key,path in [('objects',summary['weights']['objects']),('ppe',summary['weights']['ppe']),('ppe_supplement',summary['supplement_ppe_weights']),('helmet_specialist',summary['helmet_specialist_weights'])]:assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==summary['model_hashes'][key]
 tracker=PersonTracker(summary['processed_fps'],expose_current_candidates=True);rule=PPEEvents(policy);head_rule=UnassignedHeadEvents(summary['processed_fps'],policy);cap=cv2.VideoCapture(str(source));h,w=int(cap.get(4)),int(cap.get(3));result=[];candidate_count=0
 try:
  for row in rows:
   cap.set(1,row['frame_index']);ok,frame=cap.read();assert ok
   prediction=objects.predict(frame,classes=[0],conf=.1,imgsz=summary['object_imgsz'],device='cpu',verbose=False)[0];detections=[{'class':'person','confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()}for b in prediction.boxes];tracks,missing=tracker.update(row['timestamp_seconds'],detections,(h,w),scene_cut=row['scene_cut']);people=[t['detected_bbox_xyxy']for t in tracks];old={t['track_id']:t for t in row['tracks']};proposals=list(row['head_detections']);extra_crop=[]
   for t in row['tracks']:proposals.extend(t['ppe']['head_candidates']);proposals.extend(t['ppe']['rejected_candidates'])
   for track in tracks:
    if track['track_id']in old:
     assert max(abs(a-b)for a,b in zip(track['detected_bbox_xyxy'],old[track['track_id']]['detected_bbox_xyxy']))<1
    else:
     candidate_count+=1;observation=infer_person_ppe(frame,[track['detected_bbox_xyxy']],ppe,crop_height_fraction=summary['ppe_crop_height_fraction'])[0];extra_crop.extend(observation['head_candidates']);extra_crop.extend(observation['rejected_candidates'])
   proposals.extend(extra_crop)
   for i,track in enumerate(tracks):
    heads=[q for q in proposals if head_owner(q['bbox_xyxy'],people,h)==i];classes={q['class']for q in heads};state='helmet_detected' if classes=={'helmeted_head'}else'no_helmet_candidate' if classes=={'no_helmet_head'}else'conflicting_evidence' if len(classes)>1 else'unknown';track['ppe']={'person_index':i,'track_id':track['track_id'],'person_bbox_xyxy':track['detected_bbox_xyxy'],'head_candidates':heads,'rejected_candidates':[],'state':state,'risk_status':'not_evaluated','source':'same_frame_cached_heads_plus_real_candidate_crop'}
   events,transitions=rule.update(row['timestamp_seconds'],tracks,missing,scene_cut=row['scene_cut']);unassigned,changes=head_rule.update(row['timestamp_seconds'],proposals,people,(h,w),scene_cut=row['scene_cut'],body_events=events);events.extend(unassigned);transitions.extend(changes);result.append({**row,'tracks':tracks,'missing_tracks':missing,'head_detections':row['head_detections']+extra_crop,'object_detections':detections,'events':events,'transitions':transitions})
 finally:cap.release()
 context=dict(summary['event_context']);context['config_version']=hashlib.sha256(json.dumps({'parent_config_version':context['config_version'],'policy':policy,'current_candidate_tracks':True,'same_frame_cached_head_sha256':hashlib.sha256((args.run/'detections.jsonl').read_bytes()).hexdigest()},sort_keys=True).encode()).hexdigest();args.output.mkdir(parents=True);(args.output/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in result));export_events(result,args.output/'events_v1.jsonl',feature='ppe',context=context);summary.update(policy=policy,event_context=context,ppe_candidate_tracks=True,ppe_inference_mode='baseline_preserved_union_plus_helmet_specialist',candidate_replay={'parent':str(args.run.resolve()),'real_new_candidate_observations':candidate_count,'no_predicted_missing_bodies':True});(args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print({'source':source.name,'real_candidate_observations':candidate_count,'frames':len(result)})
if __name__=='__main__':main()
