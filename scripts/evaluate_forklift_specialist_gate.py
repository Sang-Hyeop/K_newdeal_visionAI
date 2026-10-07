"""Compare exact reviewed reverse-forklift references with unchanged IoU thresholds."""
from pathlib import Path
import argparse,json,os,hashlib,cv2,torch
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
from ultralytics import YOLO
from src.ppe_tiled_inference import iou

def main():
 p=argparse.ArgumentParser();p.add_argument('--tiles',action='store_true');p.add_argument('--weights',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
 protocol=json.loads((ROOT/'configs/review/related-forklift-v17-protocol.json').read_text());source=ROOT/protocol['target_source'];assert hashlib.sha256(source.read_bytes()).hexdigest()==protocol['target_source_sha256'];cap=cv2.VideoCapture(str(source));report={'tiled_inference_all_compared_models':a.tiles,'reference':'eight existing manually reviewed full-vehicle boxes; unchanged IoU0.5','models':{},'limits':['Demo scene already training-exposed by prior adaptation','A body-only specialist box can be real while failing full-vehicle IoU; report both overlap and full IoU, do not count partial matches as full detections']}
 for tag,path in [('general_v16',ROOT/'models/pilot_v16_related/person_forklift.pt'),('previous_demo',ROOT/'models/demo_object_adaptation_v1/best.pt'),('specialist',a.weights)]:
  model=YOLO(str(path));frames=[]
  for ref in protocol['target_frames']:
   cap.set(1,ref['frame_index']);ok,im=cap.read();assert ok;pred=[]
   for size in [640,1280]:
    r=model.predict(im,imgsz=size,conf=.01,verbose=False,device='cpu')[0]
    pred.extend({'class':r.names[int(b.cls[0])],'confidence':float(b.conf[0]),'bbox_xyxy':b.xyxy[0].tolist(),'imgsz':size}for b in r.boxes if r.names[int(b.cls[0])]=='forklift')
   if a.tiles:
    from src.forklift_tiled_inference import infer_tiled_forklifts
    tiled,rejected=infer_tiled_forklifts(im,model,conf=.01);pred.extend(tiled)
   hits=[d for d in pred if iou(d['bbox_xyxy'],ref['forklift_xyxy'])>=.5];score=max([d['confidence']for d in hits],default=0);frames.append({**ref,'best_matching_confidence':score,'detected_01':score>=.1,'detected_025':score>=.25,'predictions':pred})
  report['models'][tag]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'detected_01':sum(f['detected_01']for f in frames),'detected_025':sum(f['detected_025']for f in frames),'frames':frames};print(tag,report['models'][tag]['detected_01'],report['models'][tag]['detected_025'],flush=True)
  (a.output/'gate.json').write_text(json.dumps(report,indent=2))
 cap.release()
if __name__=='__main__':main()
