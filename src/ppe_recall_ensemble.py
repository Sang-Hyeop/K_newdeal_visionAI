"""Retain baseline PPE evidence and add adaptation bare-head candidates."""
from types import SimpleNamespace
import torch


def iou(a,b):
    x=max(0,min(a[2],b[2])-max(a[0],b[0]))
    y=max(0,min(a[3],b[3])-max(a[1],b[1]))
    intersection=x*y
    return intersection/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)


class PPERecallEnsemble:
    """Both baseline classes plus supplemental no-helmet evidence; no veto."""
    names={0:'helmeted_head',1:'no_helmet_head'}
    def __init__(self,baseline,supplement,preserve_union=False,helmet_specialist=None):
        if baseline.names!=self.names or supplement.names!=self.names:
            raise ValueError('PPE class mapping mismatch')
        self.baseline,self.supplement=baseline,supplement
        self.preserve_union=preserve_union
        self.helmet_specialist=helmet_specialist
        if helmet_specialist is not None and (helmet_specialist.names!=self.names or not preserve_union):raise ValueError('Helmet specialist requires same classes and preserved union')

    def predict(self,frame,**kwargs):
        candidates=[]
        sources=[(self.baseline,'baseline',{0,1}),(self.supplement,'demo_supplement',{0,1} if self.preserve_union else {1})]
        if self.helmet_specialist is not None:sources.append((self.helmet_specialist,'helmet_specialist',{0}))
        for model,source,classes in sources:
            result=model.predict(frame,**kwargs)[0]
            for box in result.boxes:
                cls=int(box.cls.item())
                if cls in classes:
                    candidates.append({'cls':cls,'confidence':float(box.conf.item()),'bbox':box.xyxy[0].tolist(),'sources':[source]})
        if self.preserve_union:
            boxes=[SimpleNamespace(cls=torch.tensor([r['cls']]),conf=torch.tensor([r['confidence']]),xyxy=torch.tensor([r['bbox']]),model_sources=r['sources'])for r in candidates]
            return [SimpleNamespace(names=self.names,boxes=boxes)]
        kept=[]
        for candidate in sorted(candidates,key=lambda r:r['confidence'],reverse=True):
            duplicate=next((r for r in kept if r['cls']==candidate['cls'] and iou(r['bbox'],candidate['bbox'])>=.5),None)
            if duplicate is None:kept.append(candidate)
            else:duplicate['sources']=sorted(set(duplicate['sources']+candidate['sources']))
        boxes=[SimpleNamespace(cls=torch.tensor([r['cls']]),conf=torch.tensor([r['confidence']]),xyxy=torch.tensor([r['bbox']]),model_sources=r['sources']) for r in kept]
        return [SimpleNamespace(names=self.names,boxes=boxes)]
