"""Selected PPE detector. Outputs current observed head boxes; no event/ROI rules."""
from pathlib import Path
from ultralytics import YOLO
import importlib.util

class FinalPPEDetector:
    def __init__(self, bundle=None):
        folder=Path(bundle) if bundle else Path(__file__).resolve().parent
        if not (folder/'ppe_helmet_v6_960.pt').exists():
            folder=Path(__file__).resolve().parents[1]/'models/ppe_final'
        spec=importlib.util.spec_from_file_location('ppe_final_duplicates',folder/'ppe_duplicate_filter.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.filter=module.clean
        self.model=YOLO(str(folder/'ppe_helmet_v6_960.pt'))
        if self.model.names != {0:'helmeted_head',1:'no_helmet_head'}:
            raise ValueError('Unexpected PPE class order')
    def predict(self, frame):
        result=self.model.predict(frame,imgsz=960,conf=0.15,device='cpu',verbose=False)[0]
        heads=[{'class':int(b.cls.item()),'confidence':float(b.conf.item()),'box':b.xyxy[0].tolist()} for b in result.boxes]
        return self.filter(heads,cover=0.8,overlap=0.7)
