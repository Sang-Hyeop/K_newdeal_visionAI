"""Audit raw v15 predictions against saved ROI/tracker observations; no training."""
from pathlib import Path
import os,json,hashlib,argparse
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,numpy as np,torch
from ultralytics import YOLO

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 if args.output.exists():raise ValueError('Existing output protected')
 args.output.mkdir(parents=True);weights=ROOT/'models/pilot_v15_scaled_filtered/person_forklift.pt';torch.set_num_threads(4);model=YOLO(str(weights));rows=[]
 for name,times,video,camera in [('forward',[9.38,10.01,10.43,11.05],'1_forklift_forward.mp4','forward-proximity.json'),('reverse',[12.4,12.8,13.2,13.8],'2_forklift_back.mp4','reverse-proximity.json')]:
  source=ROOT/'data/videos'/video;old=ROOT/'outputs/diagnostics/v15_final_validation'/name
  saved=[json.loads(s) for s in (old/'observations.jsonl').read_text().splitlines()];cfg=json.loads((ROOT/'configs/cameras'/camera).read_text());cap=cv2.VideoCapture(str(source));w,h=int(cap.get(3)),int(cap.get(4));polygon=np.array([[x*w,y*h] for x,y in cfg['forklift_ground_roi_normalized']],np.float32)
  assert hashlib.sha256(source.read_bytes()).hexdigest()==cfg['source_sha256']
  for target in times:
   record=min(saved,key=lambda s:abs(s['timestamp_seconds']-target));cap.set(cv2.CAP_PROP_POS_FRAMES,record['frame_index']);ok,frame=cap.read();assert ok
   prediction=model.predict(frame,conf=.01,imgsz=640,device='cpu',verbose=False)[0];raw=[];canvas=frame.copy()
   for b in prediction.boxes:
    cls=prediction.names[int(b.cls.item())];box=b.xyxy[0].tolist();score=float(b.conf.item());anchor=((box[0]+box[2])/2,box[3]);inside=cv2.pointPolygonTest(polygon,anchor,False)>=0
    raw.append({'class':cls,'bbox_xyxy':box,'confidence':score,'passes_detector_0_1':score>=.1,'passes_new_track_0_25':score>=.25,'ground_anchor_in_roi':inside,'passes_roi':cls!='forklift' or (inside and record['roi_active'])})
    if score>=.05:
     a,c,d,e=map(round,box);cv2.rectangle(canvas,(a,c),(d,e),(0,220,255) if cls=='forklift' else (0,255,0),2);cv2.putText(canvas,f'{cls} {score:.3f}',(a,max(c,24)),0,.6,(0,220,255),2)
   cv2.putText(canvas,f'{name} t={record["timestamp_seconds"]:.3f} raw diagnostic conf=.01',(10,25),0,.65,(0,220,255),2);cv2.imwrite(str(args.output/f'{name}_{record["frame_index"]}.jpg'),canvas)
   rows.append({'source':video,'source_sha256':cfg['source_sha256'],'frame_index':record['frame_index'],'timestamp_seconds':record['timestamp_seconds'],'raw_predictions':raw,'saved_roi_rejections':record['rejected_detections'],'saved_people':record['people'],'saved_forklifts':record['forklifts'],'roi_active':record['roi_active'],'scene_cut':record['scene_cut']})
  cap.release()
 report={'weights_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),'imgsz':640,'diagnostic_confidence':.01,'operating_threshold_changed':False,'training_started':False,'rows':rows,'limitations':'Selected failed demo frames; low confidence proposals include false positives; not accuracy benchmark'}
 (args.output/'report.json').write_text(json.dumps(report,indent=2))
 for row in rows:print(row['source'],round(row['timestamp_seconds'],3),'fork_raw',[(round(b['confidence'],3),[round(v) for v in b['bbox_xyxy']],b['passes_roi']) for b in row['raw_predictions'] if b['class']=='forklift'],'tracked',len(row['saved_forklifts']))
if __name__=='__main__':main()
