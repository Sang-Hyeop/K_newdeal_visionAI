"""Fixed representative-frame diagnostic; no ground-truth accuracy claim."""
from pathlib import Path
import os,json,cv2,torch
r=Path(__file__).resolve().parents[1];os.environ['YOLO_CONFIG_DIR']=str(r/'outputs/runtime/yolo');os.environ['MPLCONFIGDIR']=str(r/'outputs/runtime/matplotlib')
from ultralytics import YOLO
torch.set_num_threads(4)
out=r/'outputs/video_validation/v9_frame_probe';out.mkdir(parents=True,exist_ok=True)
report=[]
for version,weight in [('v6',r/'models/pilot_v6_corrected_forklift/person_forklift.pt'),('v9',r/'outputs/training/logistics_pilot_v9_hard_examples/weights/best.pt')]:
 model=YOLO(str(weight))
 for name,times in [('1_forklift_forward.mp4',[0,5,10,15,20]),('2_forklift_back.mp4',[0,5,10,15,20])]:
  c=cv2.VideoCapture(str(r/'data/videos'/name))
  for t in times:
   c.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,im=c.read()
   if not ok:continue
   pred=model.predict(im,imgsz=640,conf=.25,device='cpu',verbose=False)[0]
   rows=[{'class':pred.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox':b.xyxy[0].tolist()} for b in pred.boxes]
   report.append({'version':version,'video':name,'time':t,'detections':rows})
   cv2.imwrite(str(out/f'{version}_{name[:-4]}_{t}.jpg'),pred.plot())
  c.release()
(out/'predictions.json').write_text(json.dumps(report,indent=2));print('20 frame/model samples saved, no accuracy ground truth')
