"""Evaluate the precommitted target gate, without selecting or modifying weights."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,torch
from ultralytics import YOLO
from scripts.audit_pilot_predictions import iou

def best_match(items,box,key='bbox_xyxy'):
 return max([(iou(x[key],box),x) for x in items],key=lambda x:x[0],default=(0,None))
def detections(model,frame):
 r=model.predict(frame,imgsz=640,conf=.1,device='cpu',verbose=False)[0]
 return [{'class':r.names[int(b.cls.item())],'bbox_xyxy':b.xyxy[0].tolist(),'confidence':float(b.conf.item())} for b in r.boxes]
def main():
 p=argparse.ArgumentParser();p.add_argument('--weights',type=Path,required=True);p.add_argument('--name',required=True);p.add_argument('--baseline',action='store_true');args=p.parse_args()
 out=ROOT/'outputs/diagnostics/targeted_failure_v17'/args.name
 if out.exists():raise SystemExit('Existing evaluation protected')
 out.mkdir(parents=True);protocol=json.loads((ROOT/'configs/review/related-forklift-v17-protocol.json').read_text())
 src=ROOT/protocol['target_source'];assert hashlib.sha256(src.read_bytes()).hexdigest()==protocol['target_source_sha256']
 for camera,video in ([] if args.baseline else [('reverse','2_forklift_back.mp4'),('forward','1_forklift_forward.mp4')]):
  subprocess.run([sys.executable,'scripts/run_proximity_video.py','--source',f'data/videos/{video}','--weights',str(args.weights),'--output',str(out/camera),'--config',f'configs/cameras/{camera}-proximity.json'],cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
 model=YOLO(str(args.weights));torch.set_num_threads(4)
 observation_path=ROOT/'outputs/diagnostics/v16_related_validation/reverse_overlap_guard/observations.jsonl' if args.baseline else out/'reverse/observations.jsonl'
 obs={r['frame_index']:r for r in map(json.loads,observation_path.read_text().splitlines())}
 cap=cv2.VideoCapture(str(src));rows=[]
 for gt in protocol['target_frames']:
  idx=gt['frame_index'];cap.set(1,idx);ok,frame=cap.read();assert ok
  pred=detections(model,frame);d,found=best_match([x for x in pred if x['class']=='forklift'],gt['forklift_xyxy'])
  observation=obs[idx];fscore,ft=best_match(observation['forklifts'],gt['forklift_xyxy'],'detected_bbox_xyxy');pscore,pt=best_match(observation['people'],gt['worker_xyxy'],'detected_bbox_xyxy')
  matched_events=[e for e in observation['events'] if ft and pt and e['forklift_track_id']==ft['track_id'] and e['person_track_id']==pt['track_id']] if fscore>=.5 and pscore>=.5 else []
  rows.append({'frame_index':idx,'timestamp_seconds':idx/25,'forklift_detected':d>=.5,'forklift_detection_iou':d,'forklift_confidence':found['confidence'] if found else None,'forklift_tracked':fscore>=.5,'forklift_track_id':ft['track_id'] if fscore>=.5 else None,'actual_worker_tracked':pscore>=.5,'worker_track_id':pt['track_id'] if pscore>=.5 else None,'matched_actual_pair_events':matched_events})
  for label,box,color in [('GT_F',gt['forklift_xyxy'],(0,255,0)),('GT_P',gt['worker_xyxy'],(255,150,0))]:
   x1,y1,x2,y2=map(int,box);cv2.rectangle(frame,(x1,y1),(x2,y2),color,2);cv2.putText(frame,label,(x1,y1-5),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
  for x in pred:
   if x['class']=='forklift':
    x1,y1,x2,y2=map(int,x['bbox_xyxy']);cv2.rectangle(frame,(x1,y1),(x2,y2),(0,0,255),2);cv2.putText(frame,f"F {x['confidence']:.2f}",(x1,y1+20),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2)
  cv2.imwrite(str(out/f'target_{idx}.jpg'),frame[:430,:620])
 cap.release();reserved=[]
 for gt in json.loads((ROOT/'configs/review/related-forklift-v17-holdout.json').read_text()):
  path=ROOT/'data/training_review/related_forklift_v1'/gt['image'];assert hashlib.sha256(path.read_bytes()).hexdigest()==gt['source_frame_image_sha256'];frame=cv2.imread(str(path));box=[x*2 for x in gt['target_forklift_xyxy_960']]
  d,found=best_match([x for x in detections(model,frame) if x['class']=='forklift'],box)
  reserved.append({'candidate_id':gt['candidate_id'],'source_group':gt['video_group'],'target_detected':d>=.5,'iou':d,'confidence':found['confidence'] if found else None})
 fixed={}
 for label,data in [('scaled','logistics_scaled_filtered_v1'),('old','logistics_v6_corrected_forklift')]:
  run=f'logistics_{args.name}_{label}'
  if not args.baseline:subprocess.run([sys.executable,'scripts/audit_pilot_predictions.py','--task','logistics','--data-path',f'data/reviewed_pilot/{data}','--weights',str(args.weights),'--run-name',run,'--report-name','fixed_threshold_final.json'],cwd=ROOT,check=True)
  report_path=ROOT/f'outputs/training/logistics_v16_related_{label}/fixed_threshold_final.json' if args.baseline else ROOT/f'outputs/training/{run}/fixed_threshold_final.json'
  fixed[label]=json.loads(report_path.read_text())['class_counts']
 ids={r['forklift_track_id'] for r in rows if r['forklift_track_id']}
 report={'name':args.name,'weights':str(args.weights.resolve()),'weights_sha256':hashlib.sha256(args.weights.read_bytes()).hexdigest(),'target':rows,'target_detected':sum(r['forklift_detected'] for r in rows),'target_tracked':sum(r['forklift_tracked'] for r in rows),'target_worker_tracked':sum(r['actual_worker_tracked'] for r in rows),'target_same_vehicle_id':len(ids)==1 and all(r['forklift_tracked'] for r in rows),'reserved':reserved,'reserved_detected':sum(r['target_detected'] for r in reserved),'fixed_tests':fixed,'model_promoted':False,'limit':'same-camera development gate; reserved labels score target vehicle recall only'}
 (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['target','reserved','fixed_tests']}))
if __name__=='__main__':main()
