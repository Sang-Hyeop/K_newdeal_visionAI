from pathlib import Path
import os,json
os.environ['YOLO_CONFIG_DIR']='/private/tmp/cvat_yolo_config'
import torch
from ultralytics import YOLO
from PIL import Image
r=Path('/Users/sanghyeopkim/Desktop/workspace');run=r/'outputs/training/cvat_helmet_manual_v2';torch.set_num_threads(4)
def iou(a,b):
 x=max(0,min(a[2],b[2])-max(a[0],b[0]));y=max(0,min(a[3],b[3])-max(a[1],b[1]));v=x*y;return v/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-v)
report={'confidence':.25,'iou':.5,'imgsz':640,'scope':'single PPE network comparison; does not evaluate deployed ensemble or full videos','models':{}}
for name,weight in [('baseline',r/'models/demo_ppe_failure_context_v3/best.pt'),('first_trial',r/'outputs/training/cvat_helmet_manual_v1/fit/weights/best.pt'),('candidate',run/'fit/weights/best.pt')]:
 m=YOLO(str(weight));report['models'][name]={}
 for ds,root in [('manual',r/'data/reviewed_pilot/cvat_helmet_training_v1/test'),('legacy',r/'data/reviewed_pilot/ppe_color_expansion_v3/test')]:
  stats={c:{'TP':0,'FP':0,'FN':0} for c in [0,1]}
  for p in sorted((root/'images').glob('*')):
   if not p.is_file():continue
   w,h=Image.open(p).size;gt=[]
   for row in (root/'labels'/(p.stem+'.txt')).read_text().splitlines():
    c,x,y,bw,bh=map(float,row.split());gt.append((int(c),[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]))
   res=m.predict(str(p),imgsz=640,conf=.25,device='cpu',verbose=False)[0];pred=[(int(c),box.tolist(),float(conf)) for c,box,conf in zip(res.boxes.cls.cpu(),res.boxes.xyxy.cpu(),res.boxes.conf.cpu())];used=set()
   for c,box,score in sorted(pred,key=lambda v:-v[2]):
    options=[(iou(box,g),j) for j,(gc,g) in enumerate(gt) if gc==c and j not in used];best=max(options,default=(0,-1))
    if best[0]>=.5:stats[c]['TP']+=1;used.add(best[1])
    else:stats[c]['FP']+=1
   for j,(c,g) in enumerate(gt):
    if j not in used:stats[c]['FN']+=1
  report['models'][name][ds]=stats
(run/'fixed_comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
