"""Preserve established detections and supplement missing object proposals."""
import hashlib,json
from types import SimpleNamespace
import torch
from src.ppe_recall_ensemble import iou

class ObjectRecallEnsemble:
    names={0:'person',1:'forklift'}
    def __init__(self,baseline,supplement):
        if baseline.names!=self.names or supplement.names!=self.names:raise ValueError('Object class mapping mismatch')
        self.baseline,self.supplement=baseline,supplement
    def predict(self,frame,**kwargs):
        rows=[]
        for model,source in [(self.baseline,'v16_baseline'),(self.supplement,'demo_adaptation')]:
            result=model.predict(frame,**kwargs)[0]
            for box in result.boxes:
                rows.append({'cls':int(box.cls.item()),'confidence':float(box.conf.item()),'bbox':box.xyxy[0].tolist(),'source':source})
        # Every established baseline box survives unchanged. New boxes only fill
        # uncovered regions. Weak proposals cannot replace an established box.
        kept=[r for r in rows if r['source']=='v16_baseline' and r['confidence']>=.25]
        rest=[r for r in rows if not (r['source']=='v16_baseline' and r['confidence']>=.25)]
        for row in sorted(rest,key=lambda r:-r['confidence']):
            if not any(k['cls']==row['cls'] and iou(k['bbox'],row['bbox'])>=.5 for k in kept):kept.append(row)
        boxes=[SimpleNamespace(cls=torch.tensor([r['cls']]),conf=torch.tensor([r['confidence']]),xyxy=torch.tensor([r['bbox']]),detection_source=r['source']) for r in kept]
        return [SimpleNamespace(names=self.names,boxes=boxes)]

def object_bundle_version(baseline_hash,supplement_hash=None):
    if supplement_hash is None:return baseline_hash
    return hashlib.sha256(json.dumps({'baseline':baseline_hash,'supplement':supplement_hash,'routing':'preserve_baseline_high_025_supplement_iou_05_v1'},sort_keys=True).encode()).hexdigest()
