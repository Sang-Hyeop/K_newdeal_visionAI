"""Development-only candidate screening against unchanged failure references."""
from pathlib import Path
import sys,os,json,hashlib,cv2,torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
from ultralytics import YOLO
from src.ppe_tiled_inference import iou

def main():
 torch.set_num_threads(2);audit=json.load(open(ROOT/'outputs/diagnostics/forklift_failure_audit_v1/audit.json'));report={'status':'development_candidate_selection_not_independent_test','fixed_iou':.5,'fixed_confidence':.25,'models':{}};names=['pilot_v9_hard_examples/person_forklift.pt','pilot_v11_multisite/person_forklift.pt','pilot_v14_error_focus/person_forklift.pt','pilot_v15_scaled_filtered/person_forklift.pt','nvidia_object_adaptation_v1/best.pt'];dataset=ROOT/'data/reviewed_pilot/safe_carrying_envelope_v2/test/images';source=json.load(open(ROOT/'outputs/diagnostics/safe_carrying_envelope_v2_native2/video2-metadata.json'))['source'];cap=cv2.VideoCapture(source);images=[]
 for case in audit['rows']:
  if case['image'].startswith('reverse_'):
   cap.set(1,case['provenance']['frame_index']);ok,im=cap.read();assert ok
  else:im=cv2.imread(str(dataset/case['image']))
  images.append(im)
 cap.release();out=ROOT/'outputs/diagnostics/forklift_failure_screen_v4';out.mkdir(parents=True,exist_ok=True)
 for name in names:
  path=ROOT/'models'/name;model=YOLO(str(path));rows=[]
  for case,im in zip(audit['rows'],images):
   ds=[]
   for size in [640,1280]:
    result=model.predict(im,imgsz=size,conf=.1,device='cpu',verbose=False)[0];ds.extend({'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'imgsz':size}for b in result.boxes if result.names[int(b.cls.item())]=='forklift')
   rows.append({'image':case['image'],'matches':[max([d['confidence']for d in ds if iou(d['bbox_xyxy'],g)>=.5],default=0)for g in case['references']],'predictions':ds})
  report['models'][name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'matched_025':sum(c>=.25 for r in rows for c in r['matches']),'total_references':sum(len(r['matches'])for r in rows),'rows':rows};(out/'screen.json').write_text(json.dumps(report,indent=2));print(name,report['models'][name]['matched_025'],flush=True)
if __name__=='__main__':main()
