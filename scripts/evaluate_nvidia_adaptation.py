import os,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(R/'outputs/runtime/yolo')
import torch
from ultralytics import YOLO
torch.set_num_threads(4)
boxes=[[319,10,363,107],[318,19,361,122],[306,44,358,162],[291,42,410,184],[314,30,426,189],[391,111,425,188],[327,7,362,105],[322,31,362,127],[308,44,354,164],[298,56,355,181],[260,64,358,281],[274,70,376,275],[333,8,361,70],[324,15,359,97],[298,54,355,190],[180,85,370,270],[328,0,367,88],[231,27,337,183],[223,30,329,197],[198,63,311,183],None,None]
refs=json.loads((R/'data/training_review/nvidia52_v1/demo1_reference_candidates.json').read_text())
for row,b in zip(refs,boxes):row['main_vehicle_bbox']=None if b is None else [v*2 for v in b]
out=R/'outputs/diagnostics/nvidia_adaptation_comparison';out.mkdir(parents=True,exist_ok=True)
(out/'reference.json').write_text(json.dumps({'scope':'manually reviewed main forklift only; background vehicles are not labelled; same camera adaptation, not independent generalization','frames':refs},indent=2))
def iou(a,b):
 inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter+1e-9)
results={}
for tag,path in [('previous',R/'models/demo_object_adaptation_v1/best.pt'),('candidate',R/'models/nvidia_object_adaptation_v1/best.pt')]:
 model=YOLO(str(path));rows=[]
 for ref in refs:
  predictions=[]
  for size in [640,1280]:
   result=model.predict(str(R/'data/training_review/nvidia52_v1/frames'/ref['image']),imgsz=size,conf=.1,verbose=False,device='cpu')[0]
   for b in result.boxes:
    if result.names[int(b.cls[0])]=='forklift':predictions.append({'bbox':b.xyxy[0].tolist(),'confidence':float(b.conf[0]),'imgsz':size})
  gt=ref['main_vehicle_bbox'];matched=[p for p in predictions if gt and iou(p['bbox'],gt)>=.5]
  score=max([p['confidence'] for p in matched],default=0)
  rows.append({**ref,'matched_confidence':score,'detected_at_025':score>=.25,'predictions':predictions})
 positive=[r for r in rows if r['main_vehicle_bbox']]
 results[tag]={'reference_positive_frames':len(positive),'matched_at_025':sum(r['detected_at_025'] for r in positive),'missed_frame_indices':[r['frame_index'] for r in positive if not r['detected_at_025']],'frames':rows}
 (out/'comparison.json').write_text(json.dumps(results,indent=2));print(tag,results[tag]['matched_at_025'],len(positive),results[tag]['missed_frame_indices'],flush=True)
