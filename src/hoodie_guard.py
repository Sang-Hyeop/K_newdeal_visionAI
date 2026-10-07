"""Whole-person hood evidence can veto PPE SAFE, never establish helmet/bare status."""
import math

def _iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return inter/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)

def person_context_crops(frame,person_boxes,pad_fraction=.25):
    """Full frame plus padded actual person crops; no synthetic boxes."""
    h,w=frame.shape[:2];inputs=[(frame,0,0)]
    for box in person_boxes:
        x,y,a,b=box;pad=pad_fraction*max(a-x,b-y);left=max(0,int(x-pad));top=max(0,int(y-pad));right=min(w,int(a+pad));bottom=min(h,int(b+pad))
        if right>left and bottom>top:inputs.append((frame[top:bottom,left:right],left,top))
    return inputs

def predict_hood_detections(model,frame,person_boxes,confidence=.25,imgsz=640):
    predictions=[]
    for image,left,top in person_context_crops(frame,person_boxes):
        result=model.predict(image,imgsz=imgsz,conf=confidence,verbose=False)[0]
        for box in result.boxes:
            x,y,a,b=box.xyxy[0].tolist()
            predictions.append({'class_id':int(box.cls.item()),'confidence':float(box.conf.item()),'bbox_xyxy':[x+left,y+top,a+left,b+top]})
    return predictions

def apply_hood_guard(events,detections,minimum_confidence=.5,minimum_iou=.3):
    if not all(math.isfinite(x) and 0<x<=1 for x in (minimum_confidence,minimum_iou)):
        raise ValueError('Invalid hood evidence threshold')
    result=[]
    for original in events:
        event=dict(original);box=event.get('person_bbox_xyxy')
        matches=[d for d in detections if d['class_id']==0 and d['confidence']>=minimum_confidence and box and _iou(box,d['bbox_xyxy'])>=minimum_iou]
        if matches:
            event['hood_evidence']=matches
            event['classification_status']='unconfirmed'
            event['hood_review_status']='whole_person_hood_candidate_ppe_requires_review'
            event['hood_evidence_scope']='whole_person_not_head_or_helmet'
            if event.get('severity')=='SAFE':
                event.update(severity=None,observation_status='unconfirmed',classification_status='unconfirmed',reason='hood_and_helmet_evidence_requires_review',ppe_state='unknown')
            # Keep bare-head warnings: a hood false positive must not erase observed risk.
        result.append(event)
    return result
