"""Evaluate the externally trained hood model on the reviewed source6 hood track."""
from pathlib import Path
import json,os,sys,hashlib,argparse
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'outputs/runtime/cache'))
import torch,cv2
from ultralytics import YOLO

def iou(a,b):
 x=max(0,min(a[2],b[2])-max(a[0],b[0]));y=max(0,min(a[3],b[3])-max(a[1],b[1]));inter=x*y
 return inter/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--weights',type=Path,default=ROOT/'models/hoodie_auxiliary_v1/hoodie.pt');parser.add_argument('--output',type=Path,default=ROOT/'outputs/diagnostics/hoodie_auxiliary_v1_video6');parser.add_argument('--skip-test-validation',action='store_true');args=parser.parse_args()
 torch.set_num_threads(2);weights=args.weights;model=YOLO(str(weights));source=ROOT/'data/videos/6_Helmet_forklift.mp4';cap=cv2.VideoCapture(str(source));out=args.output;out.mkdir(parents=True,exist_ok=True);rows=[]
 cached=ROOT/'outputs/diagnostics/scenario_plan_v2_conservative_ppe/video6/detections.jsonl'
 for row in map(json.loads,cached.read_text().splitlines()):
  cap.set(cv2.CAP_PROP_POS_FRAMES,row['frame_index']);ok,frame=cap.read()
  if not ok:raise RuntimeError('source read failed')
  result=model.predict(frame,imgsz=640,conf=.1,verbose=False)[0];pred=[]
  for b in result.boxes:
   pred.append({'class_id':int(b.cls.item()),'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()})
  target=next((t for t in row['ppe_tracks']if t['track_id']=='1:1'),None)
  if target:
   x,y,a,b=target['bbox_xyxy'];pad=.25*max(a-x,b-y);h,w=frame.shape[:2];left=max(0,int(x-pad));top=max(0,int(y-pad));right=min(w,int(a+pad));bottom=min(h,int(b+pad))
   cropped=model.predict(frame[top:bottom,left:right],imgsz=640,conf=.1,verbose=False)[0]
   for box in cropped.boxes:
    xx,yy,aa,bb=box.xyxy[0].tolist();pred.append({'class_id':int(box.cls.item()),'confidence':float(box.conf.item()),'bbox_xyxy':[xx+left,yy+top,aa+left,bb+top],'inference_source':'actual_person_context_crop'})
  matches=[p for p in pred if p['class_id']==0 and target and iou(p['bbox_xyxy'],target['bbox_xyxy'])>=.3]
  score=max([p['confidence']for p in matches],default=0)
  rows.append({'frame_index':row['frame_index'],'timestamp_seconds':row['timestamp_seconds'],'reviewed_hood_target_present':bool(target),'hood_target_confidence':score,'hood_target_full_frame_confidence':max([p['confidence']for p in matches if p.get('inference_source')!='actual_person_context_crop'],default=0),'predictions':pred})
  if row['frame_index'] in (150,200,255,270):
   for p in pred:
    box=list(map(int,p['bbox_xyxy']));c=(0,0,255)if p['class_id']==0 else (0,255,0);cv2.rectangle(frame,box[:2],box[2:],c,2);cv2.putText(frame,f"{'HOOD'if p['class_id']==0 else 'NORMAL (NOT PPE SAFE)'} {p['confidence']:.2f}",box[:2],0,.5,c,1)
   cv2.imwrite(str(out/f"frame_{row['frame_index']}.jpg"),frame)
 cap.release();(out/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in rows));targets=[r for r in rows if r['reviewed_hood_target_present']]
 report={'status':'experimental_not_promoted','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'weights_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),'reviewed_target':'scene1 track1:1 blue hood; body boxes from cached real person detections','target_samples':len(targets),'matching_iou':.3,'inference_method':'full_frame plus actual detected person context crop; no synthetic boxes','full_frame_hood_hits_by_confidence':{str(c):sum(r['hood_target_full_frame_confidence']>=c for r in targets)for c in [.1,.25,.5]},'hood_hits_by_confidence':{str(c):sum(r['hood_target_confidence']>=c for r in targets)for c in [.1,.25,.5]},'limitation':'one reviewed track, sampled frames, not a general PPE accuracy estimate; Normal never means helmet safe'}
 if not args.skip_test_validation:
  validation=model.val(data=str(ROOT/'data/reviewed_pilot/hoodie_roboflow_v1/dataset.yaml'),split='test',device='cpu',workers=0,batch=4,plots=False,verbose=False)
  report['development_test_per_class']={validation.names[int(c)]:{'precision':float(validation.box.p[i]),'recall':float(validation.box.r[i]),'mAP50':float(validation.box.ap50[i])}for i,c in enumerate(validation.box.ap_class_index)}
 (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
