from pathlib import Path
import cv2,torch,json,numpy as np
from ultralytics import YOLO
torch.set_num_threads(4);w=Path('/Users/sanghyeopkim/Desktop/workspace');out=w/'outputs/diagnostics/forklift_recall_v2';out.mkdir(parents=True,exist_ok=True);m=YOLO(str(w/'models/experiments/forklift_cvat_combined_v1/weights/best.pt'));cap=cv2.VideoCapture(str(w/'data/videos/7_Logistics Warehouse.mp4'));rows=[]
for sec in [12,60]:
 cap.set(0 if False else cv2.CAP_PROP_POS_MSEC,sec*1000);ok,f=cap.read();assert ok;h,ww=f.shape[:2];panels=[]
 for name,img,x,y,size in [('full960',f,0,0,960),('full1280',f,0,0,1280),('top_left',f[:500,:800],0,0,960),('top_right',f[:500,480:],480,0,960)]:
  r=m.predict(img,imgsz=size,conf=.01,device='cpu',verbose=False)[0];p=f.copy();ds=[]
  for b in r.boxes:
   a,c,d,e=b.xyxy[0].tolist();a+=x;d+=x;c+=y;e+=y;conf=float(b.conf.item());ds.append(dict(box=[a,c,d,e],confidence=conf))
   if conf<.05:continue
   cv2.rectangle(p,(int(a),int(c)),(int(d),int(e)),(0,200,255),2);cv2.putText(p,f'{conf:.2f}',(int(a),max(18,int(c)-4)),0,.5,(0,200,255),1)
  p=cv2.resize(p,(640,360));cv2.putText(p,name,(5,22),0,.65,(255,255,255),2);panels.append(p);rows.append(dict(sec=sec,name=name,detections=ds))
 cv2.imwrite(str(out/f'probe_{sec}.jpg'),np.vstack([np.hstack(panels[:2]),np.hstack(panels[2:])]))
(out/'probe.json').write_text(json.dumps(rows,indent=2))
