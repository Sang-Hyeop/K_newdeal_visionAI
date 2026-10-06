"""Two-class tracking and camera-configured image-plane proximity candidates."""
from pathlib import Path
import argparse,hashlib,json,math,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,numpy as np,torch
from ultralytics import YOLO
from src.person_tracker import PersonTracker
from src.proximity import Proximity


def main():
    p=argparse.ArgumentParser()
    for name in ['source','output','weights','config']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sample-fps',type=float,default=5)
    args=p.parse_args()
    if args.output.exists() or not math.isfinite(args.sample_fps) or args.sample_fps<=0:raise ValueError('New output and positive FPS required')
    cfg=json.loads(args.config.read_text());sha=hashlib.sha256(args.source.read_bytes()).hexdigest()
    if cfg['source_name']!=args.source.name or cfg['source_sha256']!=sha:raise ValueError('Camera source changed; review configuration')
    cap=cv2.VideoCapture(str(args.source));fps=cap.get(5);w,h=int(cap.get(3)),int(cap.get(4))
    if not cap.isOpened() or fps<=0:raise ValueError('Unreadable source')
    torch.set_num_threads(4);model=YOLO(str(args.weights))
    if model.names!={0:'person',1:'forklift'}:raise ValueError('Requires own two-class detector; truck is not forklift')
    points=cfg['forklift_ground_roi_normalized']
    if len(points)<3 or any(len(p)!=2 or not all(0<=v<=1 for v in p) for p in points):raise ValueError('Invalid floor ROI')
    polygon=np.array([[x*w,y*h] for x,y in points],np.float32)
    if abs(cv2.contourArea(polygon))<=0:raise ValueError('Empty floor ROI')
    stride=max(1,round(fps/args.sample_fps));processed_fps=fps/stride
    people=PersonTracker(processed_fps,cfg['max_gap_seconds'],namespace='P')
    forklifts=PersonTracker(processed_fps,cfg['max_gap_seconds'],target_class='forklift',namespace='F')
    proximity=Proximity(cfg['warning_ratio'],cfg['critical_ratio'],cfg['hysteresis_ratio'],cfg['max_gap_seconds'])
    args.output.mkdir(parents=True)
    writer=cv2.VideoWriter(str(args.output/'proximity.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),processed_fps,(w,h))
    if not writer.isOpened():raise RuntimeError('Cannot write video')
    records=[];previous_image=None;previous_events={};roi_active=True;idx=0
    colors={'SAFE':(0,180,0),'WARNING':(0,190,255),'CRITICAL':(0,0,255),None:(170,170,170)}
    try:
        while True:
            ok,frame=cap.read()
            if not ok:break
            if idx%stride==0:
                thumbnail=cv2.resize(frame,(96,54)).astype(np.float32)/255
                cut=previous_image is not None and float(np.abs(thumbnail-previous_image).mean())>.18
                previous_image=thumbnail
                if cut:roi_active=False;proximity.reset();previous_events.clear()
                prediction=model.predict(frame,conf=.1,imgsz=640,device='cpu',verbose=False)[0]
                accepted=[];rejected=[]
                for box in prediction.boxes:
                    name=prediction.names[int(box.cls.item())];bbox=box.xyxy[0].tolist()
                    detection={'class':name,'bbox_xyxy':bbox,'confidence':float(box.conf.item())}
                    if name=='forklift' and (not roi_active or cv2.pointPolygonTest(polygon,((bbox[0]+bbox[2])/2,bbox[3]),False)<0):
                        rejected.append({**detection,'reason':'ground_anchor_outside_configured_floor_or_roi_inactive'})
                    else:accepted.append(detection)
                timestamp=idx/fps
                pt,pm=people.update(timestamp,accepted,(h,w),cut);ft,fm=forklifts.update(timestamp,accepted,(h,w),cut)
                events=proximity.update(timestamp,pt,ft,(h,w)) if roi_active else []
                transitions=[]
                for event in events:
                    event['camera_id']=cfg['camera_id']
                    key=(event['person_track_id'],event['forklift_track_id']);state=(event['severity'],event['reason'])
                    if previous_events.get(key)!=state:transitions.append(event.copy())
                    previous_events[key]=state
                record={'frame_index':idx,'timestamp_seconds':timestamp,'people':pt,'forklifts':ft,
                    'missing_people':pm,'missing_forklifts':fm,'rejected_detections':rejected,'events':events,
                    'transitions':transitions,'roi_active':roi_active,'scene_cut':cut,
                    'global_safety_status':'not_evaluated',
                    'pair_observation_status':'some_pairs_observed' if any(e['severity'] is not None for e in events) else 'unconfirmed'}
                records.append(record);canvas=frame.copy()
                cv2.polylines(canvas,[polygon.astype(np.int32)],True,(255,190,0),2)
                cv2.putText(canvas,'IMAGE PROXIMITY CANDIDATES / NOT METERS OR COLLISION PROOF',(15,25),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,190,255),2)
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
                if not roi_active:cv2.putText(canvas,'NEW VIEW: ROI RECONFIGURATION REQUIRED',(15,80),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,0,255),2)
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
    summary={'source':str(args.source.resolve()),'source_sha256':sha,'weights':str(args.weights.resolve()),
        'weights_sha256':hashlib.sha256(args.weights.read_bytes()).hexdigest(),'config':cfg,'imgsz':640,
        'frames_sampled':len(records),'processed_fps':processed_fps,'pair_state_observation_counts':counts,
        'frames_without_confirmed_pair':sum(r['pair_observation_status']=='unconfirmed' for r in records),
        'rejected_forklift_boxes':sum(len(r['rejected_detections']) for r in records),
        'transition_events':len(transitions),'scene_cuts_seconds':[r['timestamp_seconds'] for r in records if r['scene_cut']],
        'limitations':'No 3D calibration/front-rear orientation; detector errors remain; floor ROI limits coverage; no ground truth accuracy'}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))


if __name__=='__main__':main()
