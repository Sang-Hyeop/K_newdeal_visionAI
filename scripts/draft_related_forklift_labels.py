import os,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(R/'outputs/runtime/yolo')
import cv2,torch
from ultralytics import YOLO
torch.set_num_threads(4)
rows=json.loads((R/'data/training_review/related_forklift_v1/review_candidates.json').read_text())
rows=[x for x in rows if x['candidate_id']%3==2]
out=R/'outputs/diagnostics/related_forklift_label_drafts';out.mkdir(parents=True,exist_ok=True)
a=YOLO(str(R/'models/pilot_v15_scaled_filtered/person_forklift.pt')); b=YOLO(str(R/'models/pretrained/yolo26n.pt'))
for i,row in enumerate(rows):
 im=cv2.imread(str(R/'data/training_review/related_forklift_v1'/row['image'])); boxes=[]
 for model,persononly in [(a,False),(b,True)]:
  pred=model.predict(im,imgsz=960,conf=.15,verbose=False,device='cpu')[0]
  for q in pred.boxes:
   c=int(q.cls.item());xy=q.xyxy[0].tolist()
   if persononly and c!=0:continue
   if persononly and any(z[0]==0 and abs((z[1]+z[3])/2-(xy[0]+xy[2])/2)<35 and abs((z[2]+z[4])/2-(xy[1]+xy[3])/2)<35 for z in boxes):continue
   boxes.append([c,*xy,float(q.conf.item())])
 row['draft_boxes']=boxes
 canvas=cv2.resize(im,(960,540))
 for k,q in enumerate(boxes):
  c,x1,y1,x2,y2,score=q;color=(0,255,0) if c==0 else (0,165,255)
  cv2.rectangle(canvas,(int(x1/2),int(y1/2)),(int(x2/2),int(y2/2)),color,2);cv2.putText(canvas,f'{k}:{c} {score:.2f}',(int(x1/2),max(15,int(y1/2))),0,.45,color,1)
 cv2.putText(canvas,f'C{row["candidate_id"]} {row["video_group"]}',(10,530),0,.6,(0,255,255),2)
 cv2.imwrite(str(out/f'C{row["candidate_id"]}.jpg'),canvas)
 print(row['candidate_id'],len(boxes),flush=True)
(out/'drafts.json').write_text(json.dumps(rows,indent=2))
