"""두 시험 모델로 보관 영상 검출. 위험 판단 이전의 영상/JSONL 출력."""
from pathlib import Path
import os,json,argparse,time,math
ROOT=Path(__file__).resolve().parents[1]
for folder in ['yolo','matplotlib','cache']:(ROOT/'outputs/runtime'/folder).mkdir(parents=True,exist_ok=True)
os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'outputs/runtime/cache'))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
import cv2,torch
from ultralytics import YOLO

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'data/videos');p.add_argument('--sample-fps',type=float,default=2);p.add_argument('--conf',type=float,default=.25);p.add_argument('--output',type=Path,default=ROOT/'outputs/pilot_video_v1');p.add_argument('--objects-weights',type=Path,required=True);p.add_argument('--ppe-weights',type=Path,required=True);args=p.parse_args()
 if not 0<=args.conf<=1:raise ValueError('conf must be between 0 and 1')
 if args.sample_fps<=0:raise ValueError('sample-fps must be positive')
 if args.output.exists():raise SystemExit('Existing output protected; choose --output')
 models=[('objects',args.objects_weights),('ppe',args.ppe_weights)]
 torch.set_num_threads(4);models=[(key,YOLO(str(path))) for key,path in models]
 expected={'objects':{0:'person',1:'forklift'},'ppe':{0:'helmeted_head',1:'no_helmet_head'}}
 for key,model in models:
  if model.names!=expected[key]:raise ValueError(f'{key}: incompatible classes {model.names}')
 paths=sorted(args.source.glob('*.mp4')) if args.source.is_dir() else [args.source]
 if not paths:raise ValueError('No mp4 sources found')
 args.output.mkdir(parents=True);summary=[]
 for source in paths:
  cap=cv2.VideoCapture(str(source));fps=cap.get(cv2.CAP_PROP_FPS);w=int(cap.get(3));h=int(cap.get(4));total=int(cap.get(7))
  if not cap.isOpened() or fps<=0:raise RuntimeError(f'Cannot open {source}')
  stride=max(1,round(fps/args.sample_fps));folder=args.output/source.stem;folder.mkdir();writer=cv2.VideoWriter(str(folder/'detections.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps/stride,(w,h))
  if not writer.isOpened():raise RuntimeError('Cannot open video writer')
  start=time.monotonic();frame_idx=0;n=0;counts={}
  try:
   with (folder/'detections.jsonl').open('w') as log:
    while True:
     ok,frame=cap.read()
     if not ok:break
     if frame_idx%stride==0:
      detections=[];canvas=frame.copy()
      for key,model in models:
       result=model.predict(frame,imgsz=640,conf=args.conf,device='cpu',verbose=False)[0]
       for box in result.boxes:
        c=int(box.cls.item());name=result.names[c];xyxy=[round(v,2) for v in box.xyxy[0].tolist()];confidence=round(float(box.conf.item()),4)
        detections.append({'model':key,'class':name,'confidence':confidence,'bbox_xyxy':xyxy});counts[name]=counts.get(name,0)+1
        color=(0,190,0) if name in ['person','helmeted_head'] else (0,80,255);x1,y1,x2,y2=map(int,xyxy);cv2.rectangle(canvas,(x1,y1),(x2,y2),color,2);cv2.putText(canvas,f'{name} {confidence:.2f}',(x1,max(18,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1)
      record={'video':source.name,'frame_index':frame_idx,'timestamp_seconds':round(frame_idx/fps,4),'detections':detections,'risk_status':'not_evaluated','note':'raw detector pilot; no tracking/ROI/distance/PPE-person assignment'}
      log.write(json.dumps(record,ensure_ascii=False)+'\n');cv2.putText(canvas,'DETECTION PILOT / RISK NOT EVALUATED',(15,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,200,255),2);writer.write(canvas)
      if n in [0,5,15]:cv2.imwrite(str(folder/f'preview_{n:04}.jpg'),canvas)
      n+=1
     frame_idx+=1
  finally:cap.release();writer.release()
  item={'video':source.name,'source_frames':total,'source_fps':fps,'processed_frames':n,'sample_stride':stride,'detection_counts':counts,'elapsed_seconds':round(time.monotonic()-start,2),'accuracy':'not measured; demo ground truth absent','weights':{'objects':str(args.objects_weights.resolve()),'ppe':str(args.ppe_weights.resolve())},'confidence_threshold':args.conf};summary.append(item);print(json.dumps(item),flush=True)
 (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
