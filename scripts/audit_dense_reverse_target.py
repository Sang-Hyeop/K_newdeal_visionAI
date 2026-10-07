"""Every-frame target diagnostic; interpolated reference boxes never enter inference."""
from pathlib import Path
import argparse,json,os,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,numpy as np,torch
from ultralytics import YOLO
from src.tracked_proximity import TrackedProximity
from src.object_recall_ensemble import ObjectRecallEnsemble,object_bundle_version
from scripts.evaluate_demo_adaptation import match

def main():
 p=argparse.ArgumentParser();p.add_argument('--weights',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--supplement-object-weights',type=Path);args=p.parse_args()
 if args.output.exists():raise ValueError('New output required')
 protocol=json.loads((ROOT/'configs/review/demo-adaptation-v1-protocol.json').read_text());cfg=json.loads((ROOT/'configs/cameras/reverse-proximity.json').read_text());source=ROOT/'data/videos/2_forklift_back.mp4';assert hashlib.sha256(source.read_bytes()).hexdigest()==protocol['target_source_sha256'];gt=protocol['target_frames'];idxs=[r['frame_index'] for r in gt]
 torch.set_num_threads(4);baseline=YOLO(str(args.weights));assert baseline.names=={0:'person',1:'forklift'}
 supplement_hash=hashlib.sha256(args.supplement_object_weights.read_bytes()).hexdigest() if args.supplement_object_weights else None
 model=ObjectRecallEnsemble(baseline,YOLO(str(args.supplement_object_weights))) if args.supplement_object_weights else baseline
 cap=cv2.VideoCapture(str(source));fps=cap.get(5);h,w=int(cap.get(4)),int(cap.get(3));pipeline=TrackedProximity(cfg,fps);report=[];args.output.mkdir(parents=True);start=250;end=345
 writer=cv2.VideoWriter(str(args.output/'dense_target.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
 if not writer.isOpened():cap.release();raise RuntimeError('Cannot open dense video writer')
 cap.set(1,start)
 try:
  for index in range(start,end+1):
   ok,frame=cap.read()
   if not ok:raise ValueError('Cannot read diagnostic frame')
   pred=model.predict(frame,conf=.1,imgsz=640,device='cpu',verbose=False)[0];d=[{'class':pred.names[int(b.cls.item())],'bbox_xyxy':b.xyxy[0].tolist(),'confidence':float(b.conf.item())} for b in pred.boxes];r=pipeline.update(index/fps,d,(h,w))
   if index<idxs[0]:continue
   boxes={key:[float(np.interp(index,idxs,[row[key][j] for row in gt])) for j in range(4)] for key in ['forklift_xyxy','worker_xyxy']}
   ds,dt=match([t for t in d if t['class']=='forklift'],boxes['forklift_xyxy']);fs,ft=match(r['forklifts'],boxes['forklift_xyxy'],'detected_bbox_xyxy');ps,pt=match(r['people'],boxes['worker_xyxy'],'detected_bbox_xyxy')
   report.append({'frame_index':index,'timestamp_seconds':index/fps,'vehicle_detected':ds>=.5,'vehicle_confidence':dt['confidence'] if dt else None,'vehicle_detection_iou':ds,'vehicle_tracked':fs>=.5,'vehicle_track_id':ft['track_id'] if fs>=.5 else None,'worker_tracked':ps>=.5,'matched_actual_pair_events':[e for e in r['events'] if ft and pt and e.get('forklift_track_id')==ft['track_id'] and e.get('person_track_id')==pt['track_id']] if fs>=.5 and ps>=.5 else []})
   canvas=frame.copy()
   for track in r['forklifts']+r['people']:
    a,b,c,d2=map(round,track['detected_bbox_xyxy']);cv2.rectangle(canvas,(a,b),(c,d2),(0,190,255),2)
    cv2.putText(canvas,track['track_id'],(a,max(40,b-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,190,255),1)
   label='DEMO BUNDLE' if args.supplement_object_weights else 'DEMO-ADAPTED'
   cv2.putText(canvas,f'{label} / ACTUAL OBSERVATIONS / t={index/fps:.2f}s',(15,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,190,255),2)
   writer.write(canvas)
   if index in idxs:
    for c,key in [(1,'forklift_xyxy'),(0,'worker_xyxy')]:
     a,b,c2,d2=map(round,boxes[key]);cv2.rectangle(frame,(a,b),(c2,d2),(0,255,255),2)
    for t in r['forklifts']+r['people']:
     a,b,c,d2=map(round,t['detected_bbox_xyxy']);cv2.rectangle(frame,(a,b),(c,d2),(0,255,0),2)
    cv2.imwrite(str(args.output/f'frame_{index}.jpg'),frame[:430,:620])
 finally:cap.release();writer.release()
 result={'weights_sha256':hashlib.sha256(args.weights.read_bytes()).hexdigest(),'supplement_sha256':supplement_hash,'model_version':object_bundle_version(hashlib.sha256(args.weights.read_bytes()).hexdigest(),supplement_hash),'source_sha256':protocol['target_source_sha256'],'source_fps':fps,'warmup_start_frame':start,'target_frames_count':len(report),'vehicle_detected':sum(r['vehicle_detected'] for r in report),'vehicle_tracked':sum(r['vehicle_tracked'] for r in report),'worker_tracked':sum(r['worker_tracked'] for r in report),'same_vehicle_id':all(r['vehicle_tracked'] for r in report) and len({r['vehicle_track_id'] for r in report})==1,'rows':report,'reference_origin':'Linear interpolation of eight reviewed reference boxes; intermediate boxes approximate, not independently labeled accuracy ground truth.','demo_training_exposed':True,'changes_production_inference':False}
 (args.output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'})
if __name__=='__main__':main()
