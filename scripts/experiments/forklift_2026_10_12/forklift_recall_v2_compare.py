from pathlib import Path
import json,cv2,numpy as np,torch,subprocess
from ultralytics import YOLO
torch.set_num_threads(4)
w=Path('/Users/sanghyeopkim/Desktop/workspace');out=w/'outputs/diagnostics/forklift_context_video_compare_v2';out.mkdir(parents=True,exist_ok=True)
models=[YOLO(str(w/'models/experiments/forklift_cvat_combined_v1/weights/best.pt')),YOLO(str(w/'models/experiments/forklift_real_context_v2/weights/best.pt'))]
meta=json.loads((w/'configs/demo-videos.json').read_text());records=[]
for i,video in enumerate(meta[6:],7):
 cap=cv2.VideoCapture(str(w/'data/videos'/video['file']));fps=cap.get(cv2.CAP_PROP_FPS);n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));tmp=out/f'video{i}_tmp.mp4';writer=cv2.VideoWriter(str(tmp),cv2.VideoWriter_fourcc(*'mp4v'),2,(1280,360));rows=[]
 for k in range(int(n/fps*2)+1):
  idx=round(k*fps/2)
  if idx>=n:break
  cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,frame=cap.read()
  if not ok:break
  panels=[];row=dict(video=i,frame=idx,seconds=idx/fps)
  for model,name in zip(models,['previous_cvat','context_v2']):
   r=model.predict(frame,imgsz=1280,conf=.25,iou=.7,device='cpu',verbose=False)[0];d=[dict(confidence=float(b.conf.item()),box=b.xyxy[0].tolist()) for b in r.boxes];row[name]=d;p=frame.copy()
   for q in d:
    a,b,c,e=map(int,q['box']);cv2.rectangle(p,(a,b),(c,e),(0,200,255),2);cv2.putText(p,f"F {q['confidence']:.2f}",(a,max(15,b-6)),0,.5,(0,200,255),1)
   p=cv2.resize(p,(640,360));cv2.rectangle(p,(0,0),(640,28),(20,20,20),-1);cv2.putText(p,f'{name} | {idx/fps:.1f}s | 1280 conf .25',(8,20),0,.55,(255,255,255),1);panels.append(p)
  pair=np.hstack(panels);writer.write(pair);rows.append(row)
  if k in {0,4,8,12,24,40,120,240,360}:cv2.imwrite(str(out/f'video{i}_{k/2:g}s.jpg'),pair)
 writer.release();cap.release();subprocess.run(['/opt/homebrew/bin/ffmpeg','-y','-loglevel','error','-i',str(tmp),'-c:v','libx264','-pix_fmt','yuv420p','-crf','22',str(out/f'video{i}_comparison.mp4')],check=True);tmp.unlink();records.extend(rows)
 (out/'predictions.json').write_text(json.dumps(records,indent=2));(out/'status.json').write_text(json.dumps(dict(completed_videos=i,total_videos=7,stage='completed' if i==7 else 'running',sample_fps=2,imgsz=1280,conf=.25,model_applied=False)));print('completed video',i,'samples',len(rows),flush=True)
