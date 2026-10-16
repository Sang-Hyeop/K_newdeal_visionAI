"""최종 PPE 검출기. 현재 프레임의 머리 박스만 출력하고 이벤트/ROI 규칙은 없다."""
from pathlib import Path
from ultralytics import YOLO
import importlib.util

class FinalPPEDetector:
    def __init__(self, bundle=None, weights=None):
        folder=Path(bundle) if bundle else Path(__file__).resolve().parent
        if not (folder/'ppe_helmet_v6_960.pt').exists():
            folder=Path(__file__).resolve().parents[1]/'models/ppe_final'
        spec=importlib.util.spec_from_file_location('ppe_final_duplicates',folder/'ppe_duplicate_filter.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.filter=module.clean
        self.model=YOLO(str(weights or folder/'ppe_helmet_v6_960.pt'))
        if self.model.names != {0:'helmeted_head',1:'no_helmet_head'}:
            raise ValueError('Unexpected PPE class order')
    def predict(self, frame):
        result=self.model.predict(frame,imgsz=960,conf=0.15,device='cpu',verbose=False)[0]
        heads=[{'class':int(b.cls.item()),'confidence':float(b.conf.item()),'box':b.xyxy[0].tolist()} for b in result.boxes]
        return self.filter(heads,cover=0.8,overlap=0.7)

    def predict_person_context(self,frame,boxes):
        """Current person context only; crop edges cannot fabricate observed heads."""
        h,w=frame.shape[:2];heads=[]
        for box in boxes:
            bw,bh=box[2]-box[0],box[3]-box[1]
            x0,y0=max(0,int(box[0]-.75*bw)),max(0,int(box[1]-.7*bh))
            x1,y1=min(w,int(box[2]+.75*bw)),min(h,int(box[3]+.7*bh))
            result=self.model.predict(frame[y0:y1,x0:x1],imgsz=640,conf=.15,device='cpu',verbose=False)[0]
            for b in result.boxes:
                q=b.xyxy[0].tolist()
                if (x0>0 and q[0]<=1) or (y0>0 and q[1]<=1) or (x1<w and q[2]>=x1-x0-1) or (y1<h and q[3]>=y1-y0-1):continue
                heads.append({'class':int(b.cls.item()),'confidence':float(b.conf.item()),'box':[q[0]+x0,q[1]+y0,q[2]+x0,q[3]+y0]})
        return self.filter(heads,cover=.8,overlap=.7)

    def predict_upper_body_context(self,frame,boxes):
        """Current guarded upper-body search; crop-only helmets cannot certify SAFE."""
        h,w=frame.shape[:2];heads=[]
        for box in boxes:
            bw,bh=box[2]-box[0],box[3]-box[1]
            if bw<=0 or bh<=0:raise ValueError('Positive person box required')
            x0,y0=max(0,int(box[0]-.4*bw)),max(0,int(box[1]-.15*bh))
            x1,y1=min(w,int(box[2]+.4*bw)),min(h,int(box[1]+.6*bh))
            if x1<=x0 or y1<=y0:continue
            result=self.model.predict(frame[y0:y1,x0:x1],imgsz=640,conf=.15,device='cpu',verbose=False)[0]
            for b in result.boxes:
                q=b.xyxy[0].tolist()
                if (x0>0 and q[0]<=1) or (y0>0 and q[1]<=1) or (x1<w and q[2]>=x1-x0-1) or (y1<h and q[3]>=y1-y0-1):continue
                heads.append({'class':int(b.cls.item()),'confidence':float(b.conf.item()),'box':[q[0]+x0,q[1]+y0,q[2]+x0,q[3]+y0]})
        return self.filter(heads,cover=.8,overlap=.7)

    def predict_fixed_context(self,frame,boxes,context_size=320,imgsz=640):
        """Fixed-size surrounding pixels recover small heads without changing ownership geometry."""
        h,w=frame.shape[:2];heads=[]
        if not isinstance(context_size,int) or context_size<32 or not isinstance(imgsz,int) or imgsz<32:raise ValueError('Positive supported context and inference sizes required')
        for box in boxes:
            if box[2]<=box[0] or box[3]<=box[1]:raise ValueError('Positive person box required')
            size=min(context_size,h,w)
            cx=(box[0]+box[2])/2;cy=box[1]+.1*(box[3]-box[1])
            x0=max(0,min(w-size,int(cx-size/2)));y0=max(0,min(h-size,int(cy-size/2)))
            result=self.model.predict(frame[y0:y0+size,x0:x0+size],imgsz=imgsz,conf=.15,device='cpu',verbose=False)[0]
            for b in result.boxes:
                q=b.xyxy[0].tolist()
                if min(q[:2])<=3 or max(q[2:])>=size-3:continue
                heads.append({'class':int(b.cls.item()),'confidence':float(b.conf.item()),'box':[q[0]+x0,q[1]+y0,q[2]+x0,q[3]+y0]})
        return self.filter(heads,cover=.8,overlap=.7)
