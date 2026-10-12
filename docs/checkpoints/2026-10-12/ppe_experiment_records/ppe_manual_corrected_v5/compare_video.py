from pathlib import Path
import os,json,subprocess
os.environ['YOLO_CONFIG_DIR']='/private/tmp/cvat_ppe_v5_config'
import cv2,torch
from ultralytics import YOLO
root=Path('/Users/sanghyeopkim/Documents/Codex/2026-10-08/new-chat-3');out=root/'outputs/ppe_manual_corrected_v5';torch.set_num_threads(4)
models=[YOLO(str(root/'outputs/ppe_manual_full_v4/fit/weights/best.pt')),YOLO(str(out/'fit/weights/best.pt'))]
source=Path('/Users/sanghyeopkim/Desktop/workspace/data/videos/7_Logistics Warehouse.mp4'); cap=cv2.VideoCapture(str(source));fps=cap.get(cv2.CAP_PROP_FPS);total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));temp=root/'work/ppe_training_corrected_v5/video7_tmp.mp4';writer=cv2.VideoWriter(str(temp),cv2.VideoWriter_fourcc(*'mp4v'),1,(1600,500));records=[]
for idx in range(0,total,round(fps)):
 cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,frame=cap.read()
 if not ok:break
 panels=[];record={'seconds':idx/fps,'models':[]}
 for mi,model in enumerate(models):
  result=model.predict(frame,imgsz=640,conf=.25,device='cpu',verbose=False)[0];panel=cv2.resize(frame,(800,450));h,w=frame.shape[:2];detections=[]
  for box,cls,conf in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.cls.cpu().tolist(),result.boxes.conf.cpu().tolist()):
   c=int(cls);x1,y1,x2,y2=box;pt1=(round(x1*800/w),round(y1*450/h));pt2=(round(x2*800/w),round(y2*450/h));color=(40,210,60) if c==0 else (30,50,240);cv2.rectangle(panel,pt1,pt2,color,2);cv2.putText(panel,('H' if c==0 else 'NO')+f' {conf:.2f}',(pt1[0],max(12,pt1[1]-4)),cv2.FONT_HERSHEY_SIMPLEX,.38,color,1,cv2.LINE_AA);detections.append({'class':c,'confidence':conf,'box':box})
  canvas=cv2.copyMakeBorder(panel,50,0,0,0,cv2.BORDER_CONSTANT,value=(25,25,25));title='Previous: 490 training entries' if mi==0 else 'Updated: 510 training entries';cv2.putText(canvas,title,(15,21),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),1,cv2.LINE_AA);cv2.putText(canvas,f'{idx/fps:.1f}s | sampled 1 fps | conf 0.25 | H=helmet / NO=no helmet',(15,42),cv2.FONT_HERSHEY_SIMPLEX,.43,(220,220,220),1,cv2.LINE_AA);panels.append(canvas);record['models'].append(detections)
 writer.write(cv2.hconcat(panels));records.append(record)
cap.release();writer.release();dest=out/'video7_490_vs_510.mp4';subprocess.run(['/opt/homebrew/bin/ffmpeg','-y','-loglevel','error','-i',str(temp),'-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True);temp.unlink()
(out/'video7_predictions.json').write_text(json.dumps({'source':str(source),'scope':'Qualitative single PPE network comparison at 1 fps; no ground truth, no FN/FP labels; video previously used for demo adaptation. Not independent generalization.','frames':records},indent=2));print('VIDEO_DONE',len(records),dest,flush=True)
