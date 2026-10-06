"""Saved-video person tracking and per-observation PPE; no risk decisions."""
from pathlib import Path
import argparse,json,os,sys,math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,numpy as np,torch
from ultralytics import YOLO
from src.person_tracker import PersonTracker
from src.ppe_person_crop import infer_person_ppe


def main():
    p=argparse.ArgumentParser()
    for name in ['source','output','objects-weights','ppe-weights']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sample-fps',type=float,default=5)
    p.add_argument('--scene-cut-threshold',type=float,default=.18)
    args=p.parse_args()
    if args.output.exists() or not math.isfinite(args.sample_fps) or args.sample_fps<=0:
        raise ValueError('New output and finite positive FPS required')
    if not 0<args.scene_cut_threshold<=1:raise ValueError('Invalid scene cut threshold')
    torch.set_num_threads(4)
    objects,ppe=YOLO(str(args.objects_weights)),YOLO(str(args.ppe_weights))
    if objects.names.get(0)!='person':raise ValueError('Expected person class at index 0')
    cap=cv2.VideoCapture(str(args.source));fps=cap.get(5);w,h=int(cap.get(3)),int(cap.get(4))
    if not cap.isOpened() or fps<=0:raise ValueError('Unreadable video')
    stride=max(1,round(fps/args.sample_fps));tracker=PersonTracker(fps/stride)
    args.output.mkdir(parents=True)
    writer=cv2.VideoWriter(str(args.output/'tracked_ppe.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps/stride,(w,h))
    if not writer.isOpened():raise RuntimeError('Cannot open video writer')
    records=[];idx=0;previous=None
    try:
        while True:
            ok,frame=cap.read()
            if not ok:break
            if idx%stride==0:
                small=cv2.resize(frame,(96,54)).astype(np.float32)/255
                cut_score=0. if previous is None else float(np.mean(np.abs(small-previous)))
                cut=cut_score>args.scene_cut_threshold;previous=small
                result=objects.predict(frame,classes=[0],conf=.1,imgsz=640,device='cpu',verbose=False)[0]
                detections=[{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),
                             'bbox_xyxy':b.xyxy[0].tolist()} for b in result.boxes]
                timestamp=idx/fps;tracks,missing=tracker.update(timestamp,detections,(h,w),scene_cut=cut)
                raw=ppe.predict(frame,conf=.25,imgsz=640,device='cpu',verbose=False)[0]
                heads=[{'class':raw.names[int(b.cls.item())],'confidence':float(b.conf.item()),
                        'bbox_xyxy':b.xyxy[0].tolist()} for b in raw.boxes]
                observations=infer_person_ppe(frame,[t['bbox_xyxy'] for t in tracks],ppe,full_frame_heads=heads)
                canvas=frame.copy()
                for track,observation in zip(tracks,observations):
                    observation['track_id']=track['track_id'];track['ppe']=observation
                    x1,y1,x2,y2=map(int,track['bbox_xyxy']);color=(0,180,0) if observation['state']=='helmet_detected' else (0,190,255)
                    cv2.rectangle(canvas,(x1,y1),(x2,y2),color,2)
                    cv2.putText(canvas,f"ID {track['track_id']} {observation['state']}",(x1,max(50,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1)
                    for head in observation['head_candidates']:
                        a,b,c,d=map(int,head['bbox_xyxy']);cv2.rectangle(canvas,(a,b),(c,d),(255,200,0),1)
                cv2.putText(canvas,'TRACKING PILOT / RISK NOT EVALUATED',(15,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,200,255),2)
                if cut:cv2.putText(canvas,'SCENE RESET',(15,50),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,80,255),2)
                writer.write(canvas)
                if len(records) in {0,25,50}:cv2.imwrite(str(args.output/f'preview_{len(records):04d}.jpg'),canvas)
                records.append({'timestamp_seconds':timestamp,'frame_index':idx,'scene_id':tracker.scene,
                                'scene_cut':cut,'scene_cut_score':cut_score,'tracks':tracks,
                                'missing_tracks':missing,'risk_status':'not_evaluated'})
            idx+=1
    finally:cap.release();writer.release()
    (args.output/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    counts={};spans={}
    for record in records:
        for track in record['tracks']:
            identity=track['track_id'];span=spans.setdefault(identity,{'first':record['timestamp_seconds'],'last':0,'observations':0})
            span['last']=record['timestamp_seconds'];span['observations']+=1
            state=track['ppe']['state'];counts[state]=counts.get(state,0)+1
    summary={'source':str(args.source.resolve()),'sampled_frames':len(records),'processed_fps':fps/stride,
             'person_state_counts':counts,'track_spans':spans,
             'scene_resets_seconds':[r['timestamp_seconds'] for r in records if r['scene_cut']],
             'scene_cut_threshold':args.scene_cut_threshold,'tracker':'ByteTrack; high .25 / low .1 / gap 1 second',
             'weights':{'objects':str(args.objects_weights.resolve()),'ppe':str(args.ppe_weights.resolve())},
             'accuracy':'Not measured; ID ground truth absent; track count is not headcount',
             'limitations':'Automatic scene-cut heuristic can miss cuts; no temporal PPE confirmation, ROI or alerts'}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))


if __name__=='__main__':main()
