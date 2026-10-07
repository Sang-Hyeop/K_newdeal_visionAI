"""Full-frame overlapping forklift search with real pixel coordinates and edge checks."""
from .ppe_tiled_inference import tile_starts,iou

def infer_tiled_forklifts(frame,model,conf=.1,size=640,stride=480):
    if size<=0 or stride<=0 or stride>size:raise ValueError('Require0 < stride <= size')
    h,w=frame.shape[:2];accepted=[];rejected=[]
    for y in tile_starts(h,size,stride):
        for x in tile_starts(w,size,stride):
            right,bottom=min(w,x+size),min(h,y+size)
            result=model.predict(frame[y:bottom,x:right],imgsz=size,conf=conf,device='cpu',verbose=False)[0]
            for b in result.boxes:
                label=model.names[int(b.cls.item())]
                if label!='forklift':continue
                l,t,r,z=b.xyxy[0].tolist();item={'class':'forklift','confidence':float(b.conf.item()),'bbox_xyxy':[l+x,t+y,r+x,z+y],'model_source':'forklift_native_scale_tile','tile_bbox_xyxy':[x,y,right,bottom]}
                cut=(x>0 and l<=3)or(y>0 and t<=3)or(right<w and r>=right-x-3)or(bottom<h and z>=bottom-y-3)
                if cut:rejected.append({**item,'reason':'internal_tile_boundary'})
                else:accepted.append(item)
    kept=[]
    for d in sorted(accepted,key=lambda q:-q['confidence']):
        if not any(iou(d['bbox_xyxy'],k['bbox_xyxy'])>=.5 for k in kept):kept.append(d)
    return kept,rejected
