"""Name-based single-class adapter; keeps existing person/PPE object taxonomy."""
from types import SimpleNamespace
import torch
from .ppe_tiled_inference import iou

class ForkliftSpecialistEnsemble:
    names={0:'person',1:'forklift'}
    def __init__(self,base,specialist):
        if base.names!=self.names:raise ValueError('Base must use canonical person/forklift classes')
        if specialist.names!={0:'forklift'}:raise ValueError('Specialist must be a single forklift class; refusing implicit index routing')
        self.base,self.specialist=base,specialist
    def predict(self,frame,**kwargs):
        prior=self.base.predict(frame,**kwargs)[0];boxes=list(prior.boxes)
        for b in self.specialist.predict(frame,**kwargs)[0].boxes:
            if int(b.cls.item())!=0:raise ValueError('Unexpected specialist class')
            score=float(b.conf.item());rect=b.xyxy[0].tolist()
            # Replace an overlapping weak proposal only with actual current-frame
            # stronger specialist inference, never with a synthetic held box.
            overlaps=[old for old in boxes if int(old.cls.item())==1 and iou(rect,old.xyxy[0].tolist())>=.5]
            if any((float(old.conf.item())>=.25 and iou(rect,old.xyxy[0].tolist())>=.85) or (float(old.conf.item())<.25 and float(old.conf.item())>=score) for old in overlaps):continue
            drop_ids={id(old)for old in overlaps if float(old.conf.item())<.25}
            boxes=[old for old in boxes if id(old)not in drop_ids]
            boxes.append(SimpleNamespace(cls=torch.tensor([1]),conf=torch.tensor([score]),xyxy=torch.tensor([rect]),detection_source='factory_forklift_specialist'))
        return [SimpleNamespace(names=self.names,boxes=boxes)]


def supplement_forklift_records(prior,observed):
    """String taxonomy for cached inference; no index guessing and no held boxes."""
    result=[dict(d)for d in prior]
    for d in observed:
        if d['class']!='forklift':raise ValueError('Specialist proposal must explicitly name forklift')
        overlaps=[k for k in result if k['class']=='forklift'and iou(k['bbox_xyxy'],d['bbox_xyxy'])>=.5]
        if any((k['confidence']>=.25 and iou(k['bbox_xyxy'],d['bbox_xyxy'])>=.85) or (k['confidence']<.25 and k['confidence']>=d['confidence'])for k in overlaps):continue
        identities={id(k)for k in overlaps if k['confidence']<.25};result=[k for k in result if id(k)not in identities];result.append({**d,'model_source':d.get('model_source','factory_forklift_specialist')})
    return result
