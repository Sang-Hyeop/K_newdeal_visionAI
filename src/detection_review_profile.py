"""Camera-reviewed object routing; rejected proposals remain available for diagnostics."""
from .ppe_tiled_inference import iou
from types import SimpleNamespace

def select_review_objects(predictions, shape, profile):
    height,width=shape;kept=[];rejected=[]
    people=[d for key in profile.get('person_prediction_keys',('person_coco',)) for d in predictions[key] if d['class']=='person']
    vehicles=[d for key in profile.get('vehicle_prediction_keys',('baseline','supplement','supplement_highres')) for d in predictions[key] if d['class']=='forklift']
    for d in sorted(people+vehicles,key=lambda d:-d['confidence']):
        box=d['bbox_xyxy'];area=(box[2]-box[0])*(box[3]-box[1])/(width*height)
        reason=None
        if d['confidence'] < profile.get('minimum_confidence_by_class',{}).get(d['class'],0):reason='low_confidence_requires_review'
        elif d['class']=='forklift'and area>profile['maximum_vehicle_frame_area']:reason='oversized_vehicle_requires_review'
        if reason is None and d['class']=='forklift' and profile.get('review_multi_vehicle_envelopes'):
            area_px=(box[2]-box[0])*(box[3]-box[1]);children=[]
            for q in vehicles:
                b=q['bbox_xyxy'];a=(b[2]-b[0])*(b[3]-b[1]);inter=max(0,min(box[2],b[2])-max(box[0],b[0]))*max(0,min(box[3],b[3])-max(box[1],b[1]))
                if q is not d and q['confidence']>=.25 and .25*area_px<a<.85*area_px and inter/max(a,1e-9)>=.9:children.append(q)
            for i,left in enumerate(children):
                for right in children[i+1:]:
                    a,b=left['bbox_xyxy'],right['bbox_xyxy'];inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
                    if iou(a,b)<.35 and union/area_px>=.7:reason='multi_vehicle_envelope_requires_review'
        if reason is None and d['class']=='forklift' and profile.get('vehicle_support_required'):
            support=predictions.get('vehicle_support',[])
            if not any(q['class']=='forklift' and q['confidence']>=profile.get('vehicle_support_minimum_confidence',.1) and iou(box,q['bbox_xyxy'])>=profile.get('vehicle_support_minimum_iou',.3) for q in support):reason='vehicle_not_supported_by_review_model'
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
    if 'person_adaptation' in profile.get('person_prediction_keys',()):
        result=models.person_adaptation.predict(frame,conf=.1,imgsz=640,device='cpu',verbose=False)[0]
        predictions['person_adaptation']=[{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'model_source':'person_adaptation'}for b in result.boxes]
    if profile.get('vehicle_support_required'):
        result=models.review_support.predict(frame,conf=profile.get('vehicle_support_minimum_confidence',.1),imgsz=1280,device='cpu',verbose=False)[0]
        predictions['vehicle_support']=[{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'model_source':'vehicle_support'}for b in result.boxes]
    return select_review_objects(predictions,frame.shape[:2],profile)


def build_review_models(models,profile,model_loader):
    """Keep each camera route isolated from the production object bundle."""
    route=SimpleNamespace(baseline=models.baseline,person_adaptation=models.supplement,supplement=model_loader(profile['vehicle_weights']) if profile.get('vehicle_weights') else models.supplement)
    if profile.get('vehicle_support_required'):
        route.review_support=model_loader(profile['vehicle_support_weights'])
    return route
