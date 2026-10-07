"""Optional overlapping head search; predictions only, never safety decisions."""
from src.ppe_person_crop import head_owner


def tile_starts(length, size=320, stride=240):
    if length <= size:
        return [0]
    starts=list(range(0,length-size+1,stride))
    if starts[-1] != length-size: starts.append(length-size)
    return starts


def iou(a,b):
    x=max(0,min(a[2],b[2])-max(a[0],b[0]));y=max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-x*y
    return x*y/union if union>0 else 0


def infer_tiled_heads(frame,model,conf=.25,imgsz=640):
    """Keep opposite-class evidence; reject heads cut by internal tile edges."""
    h,w=frame.shape[:2];accepted=[];rejected=[]
    for y in tile_starts(h):
        for x in tile_starts(w):
            right,bottom=min(w,x+320),min(h,y+320)
            prediction=model.predict(frame[y:bottom,x:right],conf=conf,imgsz=imgsz,device='cpu',verbose=False)[0]
            for box in prediction.boxes:
                a,b,c,d=box.xyxy[0].tolist()
                item={'class':model.names[int(box.cls.item())],'confidence':float(box.conf.item()),'bbox_xyxy':[a+x,b+y,c+x,d+y],'source':'overlapping_head_tile','tile_bbox_xyxy':[x,y,right,bottom]}
                cut=(x>0 and a<=3) or (y>0 and b<=3) or (right<w and c>=right-x-3) or (bottom<h and d>=bottom-y-3)
                if cut:
                    rejected.append({**item,'reason':'internal_tile_boundary'})
                else:accepted.append(item)
    kept=[]
    for item in sorted(accepted,key=lambda r:r['confidence'],reverse=True):
        if not any(item['class']==other['class'] and iou(item['bbox_xyxy'],other['bbox_xyxy'])>=.5 for other in kept):kept.append(item)
    return kept,rejected
