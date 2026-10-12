"""Experimental additive PPE inference; preserves full-frame observations.
Requires the project's src.ppe_person_crop module on Python's import path.
No training, tracking, ROI severity, or automatic safety decision is performed.
"""
from src.ppe_person_crop import infer_person_ppe

def iou(a,b):
    v=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return v/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-v)

def infer(frame,ppe,person_detector,person_confirmation,full_conf=.15,crop_conf=.5):
    raw=ppe.predict(frame,imgsz=960,conf=full_conf,device='cpu',verbose=False)[0]
    full=[{'class':int(c),'confidence':float(s),'box':b,'source':'full'} for c,s,b in zip(raw.boxes.cls.cpu().tolist(),raw.boxes.conf.cpu().tolist(),raw.boxes.xyxy.cpu().tolist())]
    persons=person_detector.predict(frame,imgsz=960,conf=.25,classes=[0],device='cpu',verbose=False)[0].boxes.xyxy.cpu().tolist()
    observations=infer_person_ppe(frame,persons,ppe,conf=.10,imgsz=640,full_frame_heads=[])
    heads=list(full);rejected=[];h,w=frame.shape[:2]
    proposals=[{'class':0 if q['class']=='helmeted_head' else 1,'confidence':q['confidence'],'box':q['bbox_xyxy'],'source':'crop','person_index':r['person_index']} for r in observations for q in r['head_candidates'] if q['confidence']>=crop_conf]
    for q in sorted(proposals,key=lambda x:-x['confidence']):
        overlap=[x for x in heads if iou(x['box'],q['box'])>=.35]
        if overlap:
            rejected.append({**q,'reason':'conflicting_class' if any(x['class']!=q['class'] for x in overlap) else 'duplicate'});continue
        a,b,c,d=persons[q['person_index']];pw=c-a;ph=d-b;x=max(0,int(a-.3*pw));y=max(0,int(b-.3*ph));xx=min(w,int(c+.3*pw));yy=min(h,int(d+.3*ph))
        pred=person_confirmation.predict(frame[y:yy,x:xx],imgsz=640,conf=.25,classes=[0],device='cpu',verbose=False)[0]
        support=max([iou([v[0]+x,v[1]+y,v[2]+x,v[3]+y],[a,b,c,d]) for v in pred.boxes.xyxy.cpu().tolist()],default=0)
        if support>=.25:heads.append({**q,'person_support_iou':support})
        else:rejected.append({**q,'reason':'unconfirmed_person','person_support_iou':support})
    return {'full_frame_heads':full,'heads':heads,'people':persons,'rejected':rejected,'scope':'frame-local detections; no accuracy guarantee or safety state'}
