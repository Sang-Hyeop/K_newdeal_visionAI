"""Mine 40 unused train-group candidates; predictions do not approve labels."""
from pathlib import Path
import json,zipfile,os
import cv2,numpy as np,torch
from ultralytics import YOLO
r=Path(__file__).resolve().parents[1];os.environ['YOLO_CONFIG_DIR']=str(r/'outputs/runtime/yolo');torch.set_num_threads(4)
out=r/'data/training_review/error_focus_v1';out.mkdir(parents=True,exist_ok=False)
pool=json.load(open(r/'data/training_review/train_archives_v1/candidates.json'));manifest=json.load(open(r/'data/reviewed_pilot/logistics_multisite_v1/manifest.json'));used={x.get('group') for x in manifest};held=[x for x in manifest if x['split']!='train'];ids=[1,3,4,6,7,11,14,19,31,33,34,43,48,52,60,61,73,77,78,100,125,127,132,135,137,138,139,142,143,147,150,151,152,153,155,156,157,159,162,164]
model=YOLO(str(r/'models/pilot_v13_preserved_low_bias/person_forklift.pt'));rows=[]
for source in pool:
 if source['review_id'] not in ids:continue
 assert source['group'] not in used and all(source['site']!=x.get('site') for x in held)
 with zipfile.ZipFile(source['source_zip']) as z:raw=z.read(source['image_member'])
 im=cv2.imdecode(np.frombuffer(raw,np.uint8),1);h,w=im.shape[:2];assert [w,h]==source['resolution']
 pred=model.predict(im,imgsz=640,conf=.25,device='cpu',verbose=False)[0];detections=[{'class':pred.names[int(b.cls)],'confidence':float(b.conf),'xyxy':b.xyxy[0].tolist()} for b in pred.boxes]
 canvas=cv2.resize(im,(960,540))
 for c,x,y,bw,bh in source['boxes']:
  a,b,e,f=round(x*960/w),round(y*540/h),round((x+bw)*960/w),round((y+bh)*540/h);cv2.rectangle(canvas,(a,b),(e,f),(0,255,0) if c==0 else (0,0,255),2);cv2.putText(canvas,'GT person' if c==0 else 'GT forklift',(a,max(20,b-5)),0,.45,(0,255,0) if c==0 else (0,0,255),1)
 cv2.putText(canvas,f"ID {source['review_id']} {source['site']} / SOURCE LABELS / pending review",(10,25),0,.65,(255,255,255),2)
 cv2.imwrite(str(out/f"{source['review_id']:03}_labels.jpg"),canvas);cv2.imwrite(str(out/f"{source['review_id']:03}_predictions.jpg"),cv2.resize(pred.plot(),(960,540)))
 rows.append({**source,'mining_detections':detections,'training_eligible':False,'qa_status':'pending_visual_review','selection_reason':'unused train group; equipment context or source small person box'})
(out/'candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print('Candidate frames:',len(rows))
