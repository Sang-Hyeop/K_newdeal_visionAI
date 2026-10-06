"""val에서만 클래스별 신뢰도를 진단. 작은 표본이므로 운영 임계값으로 승인하지 않는다."""
from pathlib import Path
from collections import Counter,defaultdict
import json,os
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
import cv2,torch
from ultralytics import YOLO
from audit_pilot_predictions import iou

def main():
 torch.set_num_threads(4);report={'status':'val-only threshold diagnostic; not deployment approved','models':{}}
 for key,task,ds in [('objects','logistics','logistics_v2'),('ppe','ppe','ppe')]:
  root=ROOT/'data/reviewed_pilot'/ds;model=YOLO(str(ROOT/'outputs/training'/f'{task}_pilot_v2/weights/best.pt'));total=Counter();observations=defaultdict(list)
  for image in sorted((root/'val/images').glob('*.jpg')):
   im=cv2.imread(str(image));h,w=im.shape[:2];gt=[]
   for line in (root/'val/labels'/(image.stem+'.txt')).read_text().splitlines():
    c,x,y,bw,bh=map(float,line.split());c=int(c);total[c]+=1;gt.append((c,[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]))
   result=model.predict(im,conf=.001,imgsz=640,device='cpu',verbose=False)[0];pred=sorted([(int(b.cls.item()),float(b.conf.item()),b.xyxy[0].tolist()) for b in result.boxes],key=lambda p:-p[1]);matched=set()
   for c,score,box in pred:
    options=[(iou(box,gbox),j) for j,(gc,gbox) in enumerate(gt) if gc==c and j not in matched];best=max(options,default=(0,-1));tp=best[0]>=.5
    if tp:matched.add(best[1])
    observations[c].append((score,tp))
  classes={}
  for c,name in model.names.items():
   grid=[]
   for threshold in [.01,.02,.03,.05,.075,.1,.15,.2,.25,.3,.4,.5,.6,.7,.8]:
    chosen=[tp for score,tp in observations[c] if score>=threshold];tp=sum(chosen);fp=len(chosen)-tp;fn=total[c]-tp;p=tp/(tp+fp) if tp+fp else 0;r=tp/total[c] if total[c] else 0;f1=2*p*r/(p+r) if p+r else 0;grid.append({'threshold':threshold,'TP':tp,'FP':fp,'FN':fn,'precision':p,'recall':r,'f1':f1})
   eligible=[g for g in grid if g['precision']>=.5 and g['TP']>0];best=max(eligible,key=lambda g:(g['f1'],g['threshold'])) if eligible else None
   classes[name]={'val_instances':total[c],'candidate':best,'grid':grid,'status':'small-sample diagnostic only' if best else 'no useful threshold found'}
  report['models'][key]=classes
 out=ROOT/'outputs/training/threshold_diagnostic.json';out.write_text(json.dumps(report,indent=2));print(json.dumps({k:{n:x['candidate'] for n,x in v.items()} for k,v in report['models'].items()}))
if __name__=='__main__':main()
