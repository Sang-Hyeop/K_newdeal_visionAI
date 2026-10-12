"""Experimental PPE multi-scale inference with person confirmation for additions.
Requires project src.ppe_person_crop on the import path and local YOLO models.
No tracking or safety-state decisions. Hood-only class policy is unchanged.
"""
from multiscale_detector import infer as multiscale_infer, iou
from src.ppe_person_crop import head_owner
def guard(f,heads,base,people,confirmation):
 h,w=f.shape[:2];kept=[];checks=[]
 for hd in heads:
  if any(iou(hd['box'],p['box'])>=.35 for p in base):kept.append(hd);continue
  owner=head_owner(hd['box'],people,h);support=0
  if owner is not None:
   a,b,c,d=people[owner];pw=c-a;ph=d-b;x=max(0,int(a-.3*pw));y=max(0,int(b-.3*ph));xx=min(w,int(c+.3*pw));yy=min(h,int(d+.3*ph));p=confirmation.predict(f[y:yy,x:xx],imgsz=640,conf=.25,classes=[0],device='cpu',verbose=False)[0]
   support=max([iou([bb[0]+x,bb[1]+y,bb[2]+x,bb[3]+y],people[owner]) for bb in p.boxes.xyxy.tolist()],default=0)
  accepted=support>=.25;checks.append(dict(head=hd,owner=owner,support_iou=support,accepted=accepted))
  if accepted:kept.append(hd)
 return kept,checks

def infer(frame,ppe_model,person_model,confirmation_model):
 p=ppe_model.predict(frame,imgsz=960,conf=.15,device='cpu',verbose=False)[0]
 baseline=[{'class':int(c),'confidence':float(s),'box':b} for c,s,b in zip(p.boxes.cls.tolist(),p.boxes.conf.tolist(),p.boxes.xyxy.tolist())]
 p=person_model.predict(frame,imgsz=960,conf=.25,classes=[0],device='cpu',verbose=False)[0]
 people=p.boxes.xyxy.tolist()
 candidate=multiscale_infer(frame,ppe_model)
 heads,checks=guard(frame,candidate,baseline,people,confirmation_model)
 return {'heads':heads,'baseline':baseline,'checks':checks,'people':people}
