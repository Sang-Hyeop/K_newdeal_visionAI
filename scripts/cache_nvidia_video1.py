import os,json,hashlib,cv2,torch
from pathlib import Path
R=Path(__file__).resolve().parents[1];os.environ['YOLO_CONFIG_DIR']=str(R/'outputs/runtime/yolo')
from ultralytics import YOLO
torch.set_num_threads(4)
weight=R/'models/nvidia_object_adaptation_v1/best.pt';model=YOLO(str(weight))
src=R/'outputs/diagnostics/video1_model_audit';out=R/'outputs/diagnostics/video1_nvidia_object_cache';out.mkdir(exist_ok=False)
meta=json.loads((src/'metadata.json').read_text());meta['model_hashes']['models/nvidia_object_adaptation_v1/best.pt']=hashlib.sha256(weight.read_bytes()).hexdigest();meta['inference_settings']['baseline']='disabled; shelf false positives';(out/'metadata.json').write_text(json.dumps(meta,indent=2))
cap=cv2.VideoCapture(str(R/'data/videos/1_forklift_forward.mp4'))
with (out/'highres.jsonl').open('w') as fh:
 for row in map(json.loads,(src/'highres.jsonl').read_text().splitlines()):
  cap.set(1,row['frame_index']);ok,frame=cap.read();assert ok
  row['baseline']=[]
  for key,size in [('supplement',640),('supplement_highres',1280)]:
   pred=model.predict(frame,imgsz=size,conf=.1,device='cpu',verbose=False)[0]
   row[key]=[{'class':pred.names[int(b.cls[0])],'confidence':float(b.conf[0]),'bbox_xyxy':b.xyxy[0].tolist(),'model_source':'nvidia_adaptation_'+str(size)} for b in pred.boxes]
  fh.write(json.dumps(row)+'\n')
cap.release();print(out)
