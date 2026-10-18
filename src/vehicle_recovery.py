"""현재 프레임 다중 스케일로 놓친 지게차를 다시 찾는다. 과거 궤적으로 박스를 만들지 않는다."""
from .ppe_tiled_inference import iou
from .detection_review_profile import exclude_confirmed_equipment

def body_ambiguous_recovery(detection, people):
    """Both current vehicle models must resemble the same person's full body."""
    if detection.get('model_source') != 'vehicle_recovery_current_image':
        return False
    boxes = [detection.get('primary_bbox_xyxy', detection['bbox_xyxy']),
             detection['recovery_support']['bbox_xyxy']]
    for person in people:
        if person['class'] != 'person' or person.get('confidence', 0) < .25:
            continue
        pb = person['bbox_xyxy']
        if all(iou(b, pb) >= .65 and pb[3] >= b[3] - .1 * (b[3] - b[1])
               and pb[2] - pb[0] >= .75 * (b[2] - b[0]) for b in boxes):
            return True
    return False

class VehicleRecovery:
    def __init__(self, primary, support, profile, max_gap=1.):
        self.primary=primary;self.support=support;self.profile=profile;self.gap=max_gap;self.history=[]

    @staticmethod
    def predict(model,image,offset=(0,0),size=960):
        result=model.predict(image,conf=.12,imgsz=size,device='cpu',verbose=False)[0]
        return [{'class':'forklift','confidence':float(b.conf.item()),'bbox_xyxy':[float(v)+offset[i%2] for i,v in enumerate(b.xyxy[0].tolist())]} for b in result.boxes if result.names[int(b.cls.item())]=='forklift']

    def verify_body_context(self, frame, detections):
        """A veto only: larger current-image context cannot create a vehicle.

        Keep existing dual-model acceptance thresholds. Either model's .12
        proposal in the wider view prevents this veto, to protect occluded riders.
        Absence here means insufficient evidence, never proof of safety.
        """
        h, w = frame.shape[:2]
        result = []
        for detection in detections:
            if not body_ambiguous_recovery(detection, detections):
                result.append(detection)
                continue
            b = detection['bbox_xyxy']
            # Use the same geometry selected by the subsequent consensus review.
            evidence = detection['recovery_support']
            if evidence['confidence'] > detection['confidence']:
                b = evidence['bbox_xyxy']
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            side = max(400, (b[2] - b[0]) * 4, (b[3] - b[1]) * 3)
            x, y = max(0, int(cx - side / 2)), max(0, int(cy - side / 2))
            a, z = min(w, int(cx + side / 2)), min(h, int(cy + side / 2))
            predictions = [self.predict(model, frame[y:z, x:a], (x, y))
                           for model in (self.primary, self.support)]
            observed = any(iou(p['bbox_xyxy'], b) >= .35
                           for group in predictions for p in group)
            result.append({**detection, 'recovery_context_verification': {
                'version': 'body-context-v1', 'crop_xyxy': [x, y, a, z],
                'predictions': predictions, 'observed': observed,
                'proposal_minimum_confidence': .12, 'minimum_iou': .35}})
        return result

    def update(self,frame,detections,timestamp,scene_cut=False,full_scan=True):
        if scene_cut:self.history=[]
        h,w=frame.shape[:2];vehicles=[d for d in detections if d['class']=='forklift']
        support=self.predict(self.support,frame) if full_scan else [];proposals=self.predict(self.primary,frame) if full_scan else []
        crops=[]
        # All current people can seed a search. A person never becomes a vehicle without detection evidence.
        seeds=[d['bbox_xyxy'] for d in detections if d['class']=='person' and d['confidence']>=.25]
        seeds += [b for t,b in self.history if timestamp-t<=self.gap]
        for b in seeds:
            bw,bh=b[2]-b[0],b[3]-b[1]
            if bh<25:continue
            side=max(bw*3,bh*1.6);cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
            crop=[max(0,int(cx-side/2)),max(0,int(cy-side/2)),min(w,int(cx+side/2)),min(h,int(cy+side/2))]
            if any(iou(crop,c)>=.65 for c in crops):continue
            # Skip a person already within a currently observed vehicle; no need to re-detect it.
            if any(iou(b,v['bbox_xyxy'])>.55 for v in vehicles):continue
            crops.append(crop)
        crop_calls=0
        for x,y,a,z in crops:
            if a-x<24 or z-y<24:continue
            current=self.predict(self.primary,frame[y:z,x:a],(x,y));crop_calls+=1
            current=[q for q in current if q['confidence']>=.2 and q['bbox_xyxy'][0]>x+2 and q['bbox_xyxy'][1]>y+2 and q['bbox_xyxy'][2]<a-2 and q['bbox_xyxy'][3]<z-2]
            if not current:continue
            extra=self.predict(self.support,frame[y:z,x:a],(x,y));crop_calls+=1
            support+=extra
            for q in current:q['recovery_crop_xyxy']=[x,y,a,z]
            proposals+=current
        accepted=[]
        for q in sorted(proposals,key=lambda q:-q['confidence']):
            if q['confidence']<.2:continue
            evidence=[s for s in support if s['confidence']>=.25 and iou(q['bbox_xyxy'],s['bbox_xyxy'])>=.35]
            if not evidence:continue
            if any(iou(q['bbox_xyxy'],v['bbox_xyxy'])>=.35 for v in vehicles+accepted):continue
            b=q['bbox_xyxy']
            if (b[2]-b[0])*(b[3]-b[1])>w*h*self.profile.get('maximum_vehicle_frame_area',.35):continue
            accepted.append({**q,'model_source':'vehicle_recovery_current_image','recovery_support':max(evidence,key=lambda s:s['confidence']),'observation_status':'confirmed'})
        accepted,rejected=exclude_confirmed_equipment(accepted,(h,w),self.profile,frame)
        verified = self.verify_body_context(frame, detections + accepted)
        accepted = verified[len(detections):]
        # Short history only seeds future image searches; it is never rendered or used for distance.
        self.history=[(t,b)for t,b in self.history if timestamp-t<=self.gap]
        self.history += [(timestamp,v['bbox_xyxy'])for v in vehicles+accepted]
        return detections+accepted,{'accepted':accepted,'rejected':rejected,'crop_inference_calls':crop_calls,'history_used_for_search_only':True}

def review_recovered_vehicles(detections,shape):
    """Conservative consensus and common box geometry for the supplementary route only."""
    from math import sqrt
    original=[d for d in detections if d.get('model_source')!='vehicle_recovery_current_image'];recovered=[];rejected=[]
    for d in sorted((d for d in detections if d.get('model_source')=='vehicle_recovery_current_image'),key=lambda d:-d['confidence']):
        verification = d.get('recovery_context_verification')
        if verification and verification['version'] == 'body-context-v1' and not verification['observed']:
            rejected.append({**d, 'review_reason': 'recovery_body_without_wider_context'});continue
        evidence=d['recovery_support'];b=d.get('primary_bbox_xyxy',d['bbox_xyxy'])
        if sqrt(d['confidence']*evidence['confidence'])<.3 or b[3]-b[1]<shape[0]*.08:
            rejected.append({**d,'review_reason':'recovery_weak_consensus_or_too_small'});continue
        # Both boxes are current model observations; prefer the stronger model's geometry.
        q={**d,'primary_bbox_xyxy':d.get('primary_bbox_xyxy',b),'bbox_xyxy':evidence['bbox_xyxy'] if evidence['confidence']>d['confidence'] else b}
        vb=q['bbox_xyxy'];vw=vb[2]-vb[0];vh=vb[3]-vb[1]
        def person_context(person):
            if person['class']!='person' or person.get('confidence',0)<.25:return False
            pb=person['bbox_xyxy'];pa=max(1,(pb[2]-pb[0])*(pb[3]-pb[1]));inter=max(0,min(pb[2],vb[2])-max(pb[0],vb[0]))*max(0,min(pb[3],vb[3])-max(pb[1],vb[1]));cx=(pb[0]+pb[2])/2
            return inter/pa>=.45 and vb[0]-.15*vw<=cx<=vb[2]+.15*vw and pb[1]<vb[1]+.6*vh
        if not any(person_context(person) for person in original):
            rejected.append({**d,'review_reason':'recovery_without_current_person_context'});continue
        if any(v['class']=='forklift' and iou(q['bbox_xyxy'],v['bbox_xyxy'])>=.35 for v in original+recovered):continue
        recovered.append(q)
    return original+recovered,rejected
