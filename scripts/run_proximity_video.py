"""Two-class tracking and camera-configured image-plane proximity candidates."""
from pathlib import Path
import argparse,hashlib,json,math,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,numpy as np,torch
from ultralytics import YOLO
from src.tracked_proximity import TrackedProximity
from src.event_contract import export_events


def main():
    p=argparse.ArgumentParser()
    for name in ['source','output','weights','config']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--demo-adapted',action='store_true',help='Label training-exposed demo adaptation honestly')
    p.add_argument('--sample-fps',type=float,default=5)
    args=p.parse_args()
    if args.output.exists() or not math.isfinite(args.sample_fps) or args.sample_fps<=0:raise ValueError('New output and positive FPS required')
    cfg=json.loads(args.config.read_text());sha=hashlib.sha256(args.source.read_bytes()).hexdigest()
    if cfg['source_name']!=args.source.name or cfg['source_sha256']!=sha:raise ValueError('Camera source changed; review configuration')
    cap=cv2.VideoCapture(str(args.source));fps=cap.get(5);w,h=int(cap.get(3)),int(cap.get(4))
    if not cap.isOpened() or fps<=0:raise ValueError('Unreadable source')
    torch.set_num_threads(4);model=YOLO(str(args.weights))
    if model.names!={0:'person',1:'forklift'}:raise ValueError('Requires own two-class detector; truck is not forklift')
    stride=max(1,round(fps/args.sample_fps));processed_fps=fps/stride
    pipeline=TrackedProximity(cfg,processed_fps)
    args.output.mkdir(parents=True)
    writer=cv2.VideoWriter(str(args.output/'proximity.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),processed_fps,(w,h))
    if not writer.isOpened():raise RuntimeError('Cannot write video')
    records=[];previous_image=None;idx=0
    colors={'SAFE':(0,180,0),'WARNING':(0,190,255),'CRITICAL':(0,0,255),None:(170,170,170)}
    try:
        while True:
            ok,frame=cap.read()
            if not ok:break
            if idx%stride==0:
                thumbnail=cv2.resize(frame,(96,54)).astype(np.float32)/255
                cut=previous_image is not None and float(np.abs(thumbnail-previous_image).mean())>.18
                previous_image=thumbnail
                prediction=model.predict(frame,conf=.1,imgsz=640,device='cpu',verbose=False)[0]
                detections=[{'class':prediction.names[int(box.cls.item())],'bbox_xyxy':box.xyxy[0].tolist(),'confidence':float(box.conf.item())} for box in prediction.boxes]
                timestamp=idx/fps
                record=pipeline.update(timestamp,detections,(h,w),cut);record['frame_index']=idx;record['detections']=detections
                pt=record['people'];ft=record['forklifts'];events=record['events']
                records.append(record);canvas=frame.copy()
                cv2.putText(canvas,'DEMO-ADAPTED MODEL / IMAGE PROXIMITY / NOT METERS' if args.demo_adapted else 'IMAGE PROXIMITY CANDIDATES / NOT METERS OR COLLISION PROOF',(15,25),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,190,255),2)
                cv2.putText(canvas,f't={timestamp:.2f}s {record["pair_observation_status"]}',(15,50),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,190,255),2)
                for track in pt+ft:
                    a,b,c,d=map(int,track['bbox_xyxy']);cv2.rectangle(canvas,(a,b),(c,d),(255,180,0),2)
                    cv2.putText(canvas,track['track_id'],(a,max(75,b-5)),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,180,0),2)
                for event in events:
                    if 'person_anchor_xy' not in event:continue
                    a,b=map(round,event['person_anchor_xy']);c,d=map(round,event['nearest_vehicle_point_xy']);color=colors[event['severity']]
                    cv2.line(canvas,(a,b),(c,d),color,3)
                    text=f"{event['person_track_id']}/{event['forklift_track_id']} {event['severity'] or 'UNKNOWN'} gap={event['normalized_image_gap']:.2f}"
                    cv2.putText(canvas,text,(max(0,a-150),max(100,b-10)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,2)
                writer.write(canvas)
                if len(records)-1 in {0,25,50,75,100}:cv2.imwrite(str(args.output/f'preview_{len(records)-1:04d}.jpg'),canvas)
            idx+=1
    finally:cap.release();writer.release()
    (args.output/'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    transitions=[e for r in records for e in r['transitions']]
    (args.output/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in transitions))
    counts={}
    for record in records:
        for event in record['events']:
            state=event['severity'] or 'UNKNOWN';counts[state]=counts.get(state,0)+1
    common=export_events(records,args.output/'events_v1.jsonl',feature='proximity',context={'camera_id':cfg['camera_id'],'video':args.source.name,'source_sha256':sha,'model_version':hashlib.sha256(args.weights.read_bytes()).hexdigest(),'config_version':hashlib.sha256(args.config.read_bytes()).hexdigest()})
    summary={'source':str(args.source.resolve()),'source_sha256':sha,'weights':str(args.weights.resolve()),
        'weights_sha256':hashlib.sha256(args.weights.read_bytes()).hexdigest(),'config':cfg,'imgsz':640,
        'frames_sampled':len(records),'processed_fps':processed_fps,'pair_state_observation_counts':counts,
        'frames_without_confirmed_pair':sum(r['pair_observation_status']=='unconfirmed' for r in records),
        'zone_roi_used':False,'detection_scope':'full_frame','common_events':len(common),
        'transition_events':len(transitions),'scene_cuts_seconds':[r['timestamp_seconds'] for r in records if r['scene_cut']],
        'model_scope':'demo_adapted' if args.demo_adapted else 'development','limitations':'No 3D calibration/front-rear orientation; detector errors remain; full-frame false positives require review; no ground truth accuracy'}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))


if __name__=='__main__':main()
