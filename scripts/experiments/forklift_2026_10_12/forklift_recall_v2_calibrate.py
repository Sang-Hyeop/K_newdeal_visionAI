from pathlib import Path
import json,cv2,torch,numpy as np
from ultralytics import YOLO
from torchvision.ops import nms,box_iou
torch.set_num_threads(4);w=Path('/Users/sanghyeopkim/Desktop/workspace');o=w/'outputs/diagnostics/forklift_recall_v2';m=YOLO(str(w/'models/experiments/forklift_cvat_combined_v1/weights/best.pt'));rows=[]
paths=(w/'data/reviewed_pilot/forklift_cvat_combined_v1/val.txt').read_text().splitlines()
for k,path in enumerate(paths):
 f=cv2.imread(path);h,ww=f.shape[:2];ds={}
 for name,rects in [('full',[(0,0,ww,h)]),('tiles',[(x,y,min(ww,x+round(ww*.65)),min(h,y+round(h*.65))) for y in [0,round(h*.35)] for x in [0,round(ww*.35)]])]:
  boxes=[]
  for x,y,z,t in rects:
   r=m.predict(f[y:t,x:z],imgsz=960,conf=.05,device='cpu',verbose=False)[0]
   for b in r.boxes:
    a,c,d,e=b.xyxy[0].tolist();boxes.append([a+x,c+y,d+x,e+y,float(b.conf.item())])
  ds[name]=boxes
 label=Path(path.replace('/images/','/labels/')).with_suffix('.txt');gt=[]
 for line in label.read_text().splitlines():
  cl,x,y,bw,bh=map(float,line.split());gt.append([(x-bw/2)*ww,(y-bh/2)*h,(x+bw/2)*ww,(y+bh/2)*h])
 rows.append(dict(path=path,gt=gt,**ds))
 if k%20==0:print(k,len(paths),flush=True)
(o/'validation_predictions.json').write_text(json.dumps(rows))
def score(fullconf,tileconf=None):
 tp=fp=fn=0
 for r in rows:
  b=[a for a in r['full'] if a[4]>=fullconf]+([] if tileconf is None else [a for a in r['tiles'] if a[4]>=tileconf]);pred=torch.tensor(b,dtype=torch.float32).reshape(-1,5)
  if len(pred):pred=pred[nms(pred[:,:4],pred[:,4],.5)]
  gt=torch.tensor(r['gt'],dtype=torch.float32).reshape(-1,4);matched=set()
  for a in pred:
   if not len(gt):fp+=1;continue
   vals=box_iou(a[:4].reshape(1,4),gt)[0];choices=sorted(range(len(gt)),key=lambda j:float(vals[j]),reverse=True);hit=next((j for j in choices if j not in matched and vals[j]>=.5),None)
   if hit is None:fp+=1
   else:matched.add(hit);tp+=1
  fn+=len(gt)-len(matched)
 return dict(tp=tp,fp=fp,fn=fn,precision=tp/max(1,tp+fp),recall=tp/max(1,tp+fn),f1=2*tp/max(1,2*tp+fp+fn))
configs=[dict(full_conf=c,tile_conf=t,**score(c,t)) for c in [.15,.25,.35] for t in [None,.25,.35,.5,.65]];baseline=score(.25);safe=[r for r in configs if r['fp']<=baseline['fp'] and r['tp']>=baseline['tp']];best=max(safe,key=lambda a:(a['tp'],-a['fp'])) if safe else None
(o/'calibration.json').write_text(json.dumps(dict(baseline=baseline,configs=configs,selected=best,scope='99 validation images; fixed IoU .5, confidence chosen on validation only'),indent=2));print('baseline',baseline,'selected',best,flush=True)
