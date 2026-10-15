"""카메라별 검수 프로필로 객체 후보를 고르고, 설비 오탐 등은 거절 목록으로 남긴다."""
from .ppe_tiled_inference import iou
from types import SimpleNamespace


def exclude_confirmed_equipment(proposals,shape,profile,frame=None):
    """Exclude only user-confirmed fixed-camera equipment; never infer a general role."""
    h,w=shape;kept=[];rejected=[]
    for d in proposals:
        a=d['bbox_xyxy'];area=max(1,(a[2]-a[0])*(a[3]-a[1]));blocked=False
        for region in profile.get('confirmed_equipment_regions',[]):
            if d['class'] not in region.get('excluded_classes',[]):continue
            if region.get('empty_reference'):
                from .equipment_reference import matches_empty_equipment
                if not matches_empty_equipment(frame,region):continue
            b=region['bbox_normalized'];b=[b[0]*w,b[1]*h,b[2]*w,b[3]*h]
            inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
            if inter/area>=region.get('minimum_coverage',.8) and (not region.get('require_center_inside') or b[0]<=(a[0]+a[2])/2<=b[2] and b[1]<=(a[1]+a[3])/2<=b[3]):blocked=True;break
        if blocked:rejected.append({**d,'review_reason':region.get('review_reason','user_confirmed_equipment_not_person_or_head'),'equipment_region_id':region.get('region_id')})
        else:kept.append(d)
    return kept,rejected

def select_review_objects(predictions, shape, profile, frame=None):
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
    people_kept=[]
    for d in kept:
        if d['class']!='person':continue
        box=d['bbox_xyxy'];area=max(1,(box[2]-box[0])*(box[3]-box[1]))
        supported=any(max(0,min(box[2],v['bbox_xyxy'][2])-max(box[0],v['bbox_xyxy'][0]))*max(0,min(box[3],v['bbox_xyxy'][3])-max(box[1],v['bbox_xyxy'][1]))/area>=.5 for v in deduplicated)
        corroborated=any(q['confidence']>=.15 and iou(box,q['bbox_xyxy'])>=.3 for q in predictions.get('person_coco',[]))
        if profile.get('weak_person_requires_context') and d.get('model_source')!='person_coco' and d['confidence']<.5 and not supported and not corroborated:
            rejected.append({**d,'review_reason':'weak_person_without_vehicle_or_coco_support'})
        else:people_kept.append(d)
    if profile.get('deduplicate_cabin_people'):
        unique=[]
        def coverage(a,b):
            inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
            return inter/max(1,(a[2]-a[0])*(a[3]-a[1]))
        for d in people_kept:
            a=d['bbox_xyxy'];duplicate=False
            for other in unique:
                b=other['bbox_xyxy']
                if d.get('model_source')==other.get('model_source'):continue
                overlapping=iou(a,b)>=.3 or max(coverage(a,b),coverage(b,a))>=.85
                same_cabin=any(coverage(a,v['bbox_xyxy'])>=.9 and coverage(b,v['bbox_xyxy'])>=.9 and max(a[3],b[3])<=v['bbox_xyxy'][1]+.85*(v['bbox_xyxy'][3]-v['bbox_xyxy'][1]) for v in deduplicated)
                if overlapping and same_cabin:duplicate=True;break
            if duplicate:rejected.append({**d,'review_reason':'duplicate_person_cross_model_same_cabin'})
            else:unique.append(d)
        people_kept=unique
    if profile.get('deduplicate_person_containment'):
        from .person_display_cleanup import deduplicate_people
        people_kept,duplicates=deduplicate_people(people_kept,**profile.get('person_deduplication_options',{}));rejected+=duplicates
    kept=people_kept+deduplicated
    kept,equipment_rejected=exclude_confirmed_equipment(kept,shape,profile,frame)
    return kept,rejected+equipment_rejected

def predict_review_objects(models,person_model,frame,profile):
    predictions={}
    for key,model,imgsz,kwargs in [('baseline',models.baseline,640,{}),('supplement',models.supplement,640,{}),('supplement_highres',models.supplement,1280,{}),('person_coco',person_model,1280,{'classes':[0]})]:
        result=model.predict(frame,conf=.1,imgsz=imgsz,device='cpu',verbose=False,**kwargs)[0]
        predictions[key]=[{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'model_source':key}for b in result.boxes]
    if 'baseline_highres' in profile.get('person_prediction_keys',()) or 'baseline_highres' in profile.get('vehicle_prediction_keys',()):
        result=models.baseline.predict(frame,conf=.1,imgsz=1280,device='cpu',verbose=False)[0]
        predictions['baseline_highres']=[{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'model_source':'baseline_highres'}for b in result.boxes]
    if 'person_adaptation' in profile.get('person_prediction_keys',()):
        result=models.person_adaptation.predict(frame,conf=.1,imgsz=640,device='cpu',verbose=False)[0]
        predictions['person_adaptation']=[{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'model_source':'person_adaptation'}for b in result.boxes]
    if profile.get('vehicle_support_required'):
        result=models.review_support.predict(frame,conf=profile.get('vehicle_support_minimum_confidence',.1),imgsz=1280,device='cpu',verbose=False)[0]
        predictions['vehicle_support']=[{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'model_source':'vehicle_support'}for b in result.boxes]
        if profile.get('vehicle_support_context'):
            h,w=frame.shape[:2]
            for d in predictions['supplement_highres']:
                if d['class']!='forklift' or d['confidence']<profile.get('vehicle_support_context_minimum_candidate_confidence',.5):continue
                box=d['bbox_xyxy']
                if any(q['class']=='forklift' and iou(box,q['bbox_xyxy'])>=profile.get('vehicle_support_minimum_iou',.3) for q in predictions['vehicle_support']):continue
                bw,bh=box[2]-box[0],box[3]-box[1]
                x0,y0=max(0,int(box[0]-.25*bw)),max(0,int(box[1]-.25*bh));x1,y1=min(w,int(box[2]+.25*bw)),min(h,int(box[3]+.25*bh))
                result=models.review_support.predict(frame[y0:y1,x0:x1],conf=profile.get('vehicle_support_context_minimum_confidence',.3),imgsz=960,device='cpu',verbose=False)[0]
                for b in result.boxes:
                    if result.names[int(b.cls.item())]!='forklift':continue
                    q=b.xyxy[0].tolist()
                    if q[0]<=1 or q[1]<=1 or q[2]>=x1-x0-1 or q[3]>=y1-y0-1:continue
                    predictions['vehicle_support'].append({'class':'forklift','confidence':float(b.conf.item()),'bbox_xyxy':[q[0]+x0,q[1]+y0,q[2]+x0,q[3]+y0],'model_source':'vehicle_support_context'})
                if not any(q['class']=='forklift' and iou(box,q['bbox_xyxy'])>=profile.get('vehicle_support_minimum_iou',.3) for q in predictions['vehicle_support']):
                    candidates=[q for key in profile.get('person_prediction_keys',()) for q in predictions[key] if q['class']=='person' and q['confidence']>=.25]
                    for person in candidates:
                        p=person['bbox_xyxy'];pa=max(1,(p[2]-p[0])*(p[3]-p[1]));inter=max(0,min(p[2],box[2])-max(p[0],box[0]))*max(0,min(p[3],box[3])-max(p[1],box[1]))
                        if inter/pa<.8:continue
                        bw,bh=p[2]-p[0],p[3]-p[1];scale=profile.get('vehicle_support_person_context_scale',1);x0,y0=max(0,int(p[0]-scale*bw)),max(0,int(p[1]-.7*bh));x1,y1=min(w,int(p[2]+scale*bw)),min(h,int(p[3]+.7*bh))
                        result=models.review_support.predict(frame[y0:y1,x0:x1],conf=profile.get('vehicle_support_context_minimum_confidence',.3),imgsz=960,device='cpu',verbose=False)[0]
                        for b in result.boxes:
                            if result.names[int(b.cls.item())]!='forklift':continue
                            q=b.xyxy[0].tolist()
                            if q[0]<=1 or q[1]<=1 or q[2]>=x1-x0-1 or q[3]>=y1-y0-1:continue
                            predictions['vehicle_support'].append({'class':'forklift','confidence':float(b.conf.item()),'bbox_xyxy':[q[0]+x0,q[1]+y0,q[2]+x0,q[3]+y0],'model_source':'vehicle_support_person_context'})
    if profile.get('vehicle_context_refinement'):
        predictions['vehicle_context']=[]
        h,w=frame.shape[:2]
        for d in predictions['supplement_highres']:
            b=d['bbox_xyxy'];bw,bh=b[2]-b[0],b[3]-b[1]
            if d['class']!='forklift' or d['confidence']<.25 or bw/bh<1.5:continue
            x0,y0=max(0,int(b[0]-.15*bw)),max(0,int(b[1]-.25*bh));x1,y1=min(w,int(b[2]+.15*bw)),min(h,int(b[3]+.25*bh))
            result=models.supplement.predict(frame[y0:y1,x0:x1],conf=.4,imgsz=1280,device='cpu',verbose=False)[0]
            for item in result.boxes:
                q=item.xyxy[0].tolist()
                if q[0]<=1 or q[1]<=1 or q[2]>=x1-x0-1 or q[3]>=y1-y0-1:continue
                q=[q[0]+x0,q[1]+y0,q[2]+x0,q[3]+y0]
                predictions['vehicle_context'].append({'class':result.names[int(item.cls.item())],'confidence':float(item.conf.item()),'bbox_xyxy':q,'model_source':'vehicle_context'})
    return select_review_objects(predictions,frame.shape[:2],profile,frame)


def build_review_models(models,profile,model_loader):
    """Keep each camera route isolated from the production object bundle."""
    route=SimpleNamespace(baseline=models.baseline,person_adaptation=models.supplement,supplement=model_loader(profile['vehicle_weights']) if profile.get('vehicle_weights') else models.supplement)
    if profile.get('vehicle_support_required'):
        route.review_support=model_loader(profile['vehicle_support_weights'])
    return route


def refine_reused_vehicle_support(frame,detections,rejected,profile,model):
    """Recheck all unsupported current proposals; no source-time or fixed-region rules."""
    h,w=frame.shape[:2];rescued=[];remaining=[]
    people=[p for p in detections if p['class']=='person' and p['confidence']>=.25]
    for d in rejected:
        if d.get('review_reason')!='vehicle_not_supported_by_review_model' or d['confidence']<profile.get('vehicle_support_context_minimum_candidate_confidence',.5):
            remaining.append(d);continue
        box=d['bbox_xyxy'];evidence=[]
        for person in people:
            p=person['bbox_xyxy'];area=max(1,(p[2]-p[0])*(p[3]-p[1]))
            intersection=max(0,min(p[2],box[2])-max(p[0],box[0]))*max(0,min(p[3],box[3])-max(p[1],box[1]))
            if intersection/area<.8:continue
            bw,bh=p[2]-p[0],p[3]-p[1];scale=profile.get('vehicle_support_person_context_scale',1)
            x0,y0=max(0,int(p[0]-scale*bw)),max(0,int(p[1]-.7*bh));x1,y1=min(w,int(p[2]+scale*bw)),min(h,int(p[3]+.7*bh))
            result=model.predict(frame[y0:y1,x0:x1],conf=profile.get('vehicle_support_context_minimum_confidence',.3),imgsz=960,device='cpu',verbose=False)[0]
            for b in result.boxes:
                if result.names[int(b.cls.item())]!='forklift':continue
                q=b.xyxy[0].tolist()
                if q[0]<=1 or q[1]<=1 or q[2]>=x1-x0-1 or q[3]>=y1-y0-1:continue
                absolute=[q[0]+x0,q[1]+y0,q[2]+x0,q[3]+y0]
                if iou(box,absolute)>=profile.get('vehicle_support_minimum_iou',.3):
                    evidence.append({'confidence':float(b.conf.item()),'bbox_xyxy':absolute,'crop_xyxy':[x0,y0,x1,y1],'model_source':'vehicle_support_person_context'})
        if evidence and not any(v['class']=='forklift' and iou(box,v['bbox_xyxy'])>=.5 for v in detections+rescued):
            rescued.append({k:v for k,v in d.items() if k!='review_reason'}|{'review_support_evidence':evidence})
        else:remaining.append(d)
    return detections+rescued,remaining
