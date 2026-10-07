"""Prepare raw failed-head crops and existing annotated source candidates for review."""
from pathlib import Path
import os,json,hashlib,random
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,numpy as np,torch
from ultralytics import YOLO

def main():
 out=ROOT/'data/training_review/ppe_remaining_v2';out.mkdir(exist_ok=True)
 model=YOLO(str(ROOT/'models/pretrained/yolo26n.pt'));torch.set_num_threads(4)
 candidates=[]
 for frame_index in [144,156,168,180,192,204,216,228,240,252,264,276]:
  frame=cv2.imread(str(out/f'frame_{frame_index}.jpg'));h,w=frame.shape[:2]
  pred=model.predict(frame,classes=[0],conf=.25,imgsz=1280,device='cpu',verbose=False)[0]
  for box in pred.boxes:
   x,y,x2,y2=map(float,box.xyxy[0].tolist());pw,ph=x2-x,y2-y
   if pw<25 or ph<80:continue
   l=max(0,int(x-.15*pw));t=max(0,int(y-.1*ph));r=min(w,int(x2+.15*pw));b=min(h,int(y2))
   index=len(candidates);crop=frame[t:b,l:r];name=f'target_{index:03d}.jpg';cv2.imwrite(str(out/name),crop)
   candidates.append({'index':index,'frame_index':frame_index,'source':'5_PPE_Helmet.mp4','person_bbox_xyxy':[x,y,x2,y2],'person_confidence':float(box.conf.item()),'review_crop_xyxy':[l,t,r,b],'image':name,'native_crop_resolution':[r-l,b-t],'status':'unreviewed','not_training_labels':True})
 (out/'target_candidates.json').write_text(json.dumps(candidates,indent=2)+'\n')
 def sheet(rows,prefix,size=16):
  for batch in range(0,len(rows),size):
   tiles=[]
   for row in rows[batch:batch+size]:
    im=cv2.imread(str(out/row['image']));tile=cv2.resize(im,(320,300));cv2.putText(tile,f"{row['index']} f{row.get('frame_index','')} {row.get('class_folder','')}",(8,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2)
    for c,x,y,x2,y2 in row.get('crop_boxes_xyxy',[]):
     ih,iw=im.shape[:2];cv2.rectangle(tile,(round(x/iw*320),round(y/ih*300)),(round(x2/iw*320),round(y2/ih*300)),(0,255,0) if c==0 else (0,190,255),2)
    tiles.append(tile)
   tiles.extend([np.zeros((300,320,3),np.uint8)]*(size-len(tiles)))
   cv2.imwrite(str(out/f'{prefix}_{batch//size:02d}.jpg'),np.vstack([np.hstack(tiles[i:i+4]) for i in range(0,size,4)]))
 sheet(candidates,'target_review')
 original=json.loads((ROOT/'configs/review/demo-ppe-smartyard-v1.json').read_text());dataset=Path(original[0]['source']).parents[3]
 support=[];rng=random.Random(20261007);used={r['source_image_sha256'] for r in original}
 for folder,cls in [('helmet_worn',0),('helmet_missing',1)]:
  paths=sorted((dataset/'training/labels'/folder).glob('*.json'));rng.shuffle(paths);groups={};accepted=0
  for label in paths:
   data=json.loads(label.read_text());image=dataset/'training/source'/folder/(label.stem+'.jpg');group=label.stem.rsplit('_',1)[0]
   if groups.get(group,0)>=3 or not image.is_file():continue
   anns=[a for a in data['annotations'] if a['object_class']==0];boxes=[a['bbox'] for a in anns if isinstance(a.get('bbox'),list) and len(a['bbox'])==4];w,h=data['images']['width'],data['images']['height']
   choices=[b for b in boxes if 32<=b[2]-b[0]<=300 and 32<=b[3]-b[1]<=300 and b[0]>20 and b[1]>20 and b[2]<w-20 and b[3]<h-20]
   if not choices:continue
   digest=hashlib.sha256(image.read_bytes()).hexdigest()
   if digest in used:continue
   im=cv2.imread(str(image));x,y,x2,y2=max(choices,key=lambda b:(b[2]-b[0])*(b[3]-b[1]));pw,ph=x2-x,y2-y;l=max(0,int(x-pw));t=max(0,int(y-ph));r=min(w,int(x2+pw));b=min(h,int(y2+ph))
   crop_boxes=[[cls,max(a,l)-l,max(bb,t)-t,min(c,r)-l,min(d,b)-t] for a,bb,c,d in boxes if a<r and c>l and bb<b and d>t]
   index=len(support);name=f'support_{index:03d}.jpg';cv2.imwrite(str(out/name),im[t:b,l:r])
   support.append({'index':index,'source':str(image),'label_source':str(label),'source_sha256':digest,'class_folder':folder,'group':group,'crop_xyxy':[l,t,r,b],'crop_boxes_xyxy':crop_boxes,'image':name,'status':'unreviewed','not_training_labels':True})
   groups[group]=groups.get(group,0)+1;accepted+=1
   if accepted>=32:break
 (out/'support_candidates.json').write_text(json.dumps(support,ensure_ascii=False,indent=2)+'\n');sheet(support,'support_review');print({'target_candidates':len(candidates),'support_candidates':len(support),'source_root':str(dataset)})
if __name__=='__main__':main()
