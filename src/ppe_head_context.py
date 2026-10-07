"""Recheck weak real bare-head candidates at two contextual crop scales."""
from src.ppe_tiled_inference import iou

def refine_weak_heads(frame,heads,model):
    h,w=frame.shape[:2];candidates=[];result=[]
    for head in sorted(heads,key=lambda a:a['confidence'],reverse=True):
        if head['class']!='no_helmet_head' or not .25<=head['confidence']<.5:continue
        if any(iou(head['bbox_xyxy'],old['bbox_xyxy'])>=.35 for old in candidates):continue
        candidates.append(head)
    for head in candidates[:10]:
        a,b,c,d=head['bbox_xyxy'];size=max(c-a,d-b)
        for scale in (2.5,4):
            x=max(0,int((a+c)/2-size*scale/2));y=max(0,int((b+d)/2-size*scale/2));right=min(w,int((a+c)/2+size*scale/2));bottom=min(h,int((b+d)/2+size*scale/2))
            if right<=x or bottom<=y:continue
            prediction=model.predict(frame[y:bottom,x:right],conf=.25,imgsz=640,device='cpu',verbose=False)[0]
            for box in prediction.boxes:
                coords=[float(v)+offset for v,offset in zip(box.xyxy[0].tolist(),[x,y,x,y])]
                # Recheck the observed candidate, not unrelated neighboring objects.
                if iou(coords,head['bbox_xyxy'])<.35:continue
                result.append({'class':model.names[int(box.cls.item())],'confidence':float(box.conf.item()),'bbox_xyxy':coords,'source':'weak_head_context_recheck','context_scale':scale,'candidate_bbox_xyxy':head['bbox_xyxy'],'model_sources':getattr(box,'model_sources',['single_ppe_model'])})
    return result
