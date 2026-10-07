"""Camera-reviewed object routing; rejected proposals remain available for diagnostics."""
from .ppe_tiled_inference import iou

def select_review_objects(predictions, shape, profile):
    height,width=shape;kept=[];rejected=[]
    people=predictions['person_coco']
    vehicles=[d for key in profile.get('vehicle_prediction_keys',('baseline','supplement','supplement_highres')) for d in predictions[key] if d['class']=='forklift']
    for d in sorted(people+vehicles,key=lambda d:-d['confidence']):
        box=d['bbox_xyxy'];area=(box[2]-box[0])*(box[3]-box[1])/(width*height)
        reason=None
        if d['class']=='forklift'and area>profile['maximum_vehicle_frame_area']:reason='oversized_vehicle_requires_review'
        if reason:rejected.append({**d,'review_reason':reason});continue
        if any(d['class']==k['class']and iou(box,k['bbox_xyxy'])>=.5 for k in kept):continue
        kept.append(dict(d))
    # A mast-only box inside the same vehicle is not a second forklift.
    vehicles=[d for d in kept if d['class']=='forklift'];deduplicated=[]
    for d in vehicles:
        a=d['bbox_xyxy'];area=(a[2]-a[0])*(a[3]-a[1])
        contained=False
        for other in vehicles:
            b=other['bbox_xyxy'];other_area=(b[2]-b[0])*(b[3]-b[1])
            inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
            if other_area>area and inter/area>=profile.get('vehicle_part_containment_threshold',.85):contained=True;break
        if contained:rejected.append({**d,'review_reason':'contained_vehicle_part_duplicate'})
        else:deduplicated.append(d)
    kept=[d for d in kept if d['class']=='person']+deduplicated
    return kept,rejected

def predict_review_objects(models,person_model,frame,profile):
    predictions={}
    for key,model,imgsz,kwargs in [('baseline',models.baseline,640,{}),('supplement',models.supplement,640,{}),('supplement_highres',models.supplement,1280,{}),('person_coco',person_model,1280,{'classes':[0]})]:
        result=model.predict(frame,conf=.1,imgsz=imgsz,device='cpu',verbose=False,**kwargs)[0]
        predictions[key]=[{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'model_source':key}for b in result.boxes]
    return select_review_objects(predictions,frame.shape[:2],profile)
