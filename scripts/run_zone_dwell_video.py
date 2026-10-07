"""Detector -> tracker -> configured ROI dwell -> events and annotated video."""
from pathlib import Path
import argparse,hashlib,json,math,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,numpy as np,torch
from ultralytics import YOLO
from src.tracked_zone import TrackedZone
from src.event_contract import export_events
from src.detection_sources import route_detections, model_version


def main():
    p=argparse.ArgumentParser()
    for name in ['source','output','weights','config']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--demo-adapted',action='store_true',help='Label training-exposed demo diagnostics')
    p.add_argument('--person-weights',type=Path,help='Experimental separate person source; default unchanged')
    p.add_argument('--sample-fps',type=float,default=5)
    p.add_argument('--imgsz',type=int,default=1280)
    args=p.parse_args()
    if args.output.exists() or not math.isfinite(args.sample_fps) or args.sample_fps<=0:raise ValueError('New output and positive FPS required')
    if args.imgsz<32 or args.imgsz%32:raise ValueError('imgsz must be a positive multiple of 32')
    config=json.loads(args.config.read_text())
    if config['source_name']!=args.source.name:raise ValueError('ROI configuration belongs to another source')
    source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest()
    if config.get('source_sha256',source_sha256)!=source_sha256:raise ValueError('Source changed; review ROI before reuse')
    torch.set_num_threads(4);model=YOLO(str(args.weights))
    if model.names.get(0)!='person':raise ValueError('Expected person class 0')
    if config.get('vehicle_conditioned') and model.names!={0:'person',1:'forklift'}:raise ValueError('Conditional lane requires person/forklift model')
    person_model=YOLO(str(args.person_weights)) if args.person_weights else None
    if person_model and person_model.names.get(0)!='person':raise ValueError('Separate source requires person class 0')
    object_hash=hashlib.sha256(args.weights.read_bytes()).hexdigest()
    person_hash=hashlib.sha256(args.person_weights.read_bytes()).hexdigest() if args.person_weights else None
    effective_version=model_version(object_hash,person_hash)
    cap=cv2.VideoCapture(str(args.source));fps=cap.get(5);w,h=int(cap.get(3)),int(cap.get(4))
    if not cap.isOpened() or fps<=0:raise ValueError('Unreadable source')
    stride=max(1,round(fps/args.sample_fps));pipeline=TrackedZone(config,(h,w),fps/stride)
    approach_contours=[]
    if pipeline.access:
        mask=np.zeros((h,w),np.uint8);cv2.fillPoly(mask,[np.array(pipeline.polygon,np.int32)],255)
        radius=math.ceil(pipeline.access.margin)
        kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1))
        outer=cv2.dilate(mask,kernel)
        approach_contours=cv2.findContours(outer,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]
    args.output.mkdir(parents=True)
    writer=cv2.VideoWriter(str(args.output/'zone_dwell.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps/stride,(w,h))
    if not writer.isOpened():raise RuntimeError('Cannot open video writer')
    idx=0;records=[];previous=None
    colors={'SAFE':(0,180,0),'WARNING':(0,190,255),'CRITICAL':(0,0,255),None:(160,160,160)}
    try:
        while True:
            ok,frame=cap.read()
            if not ok:break
            if idx%stride==0:
                small=cv2.resize(frame,(96,54)).astype(np.float32)/255
                cut=previous is not None and float(np.abs(small-previous).mean())>.18;previous=small
                prediction=model.predict(frame,classes=None if pipeline.forklift_tracker else [0],conf=.1,imgsz=args.imgsz,device='cpu',verbose=False)[0]
                detections=[{'class':prediction.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()} for b in prediction.boxes]
                if person_model:
                    pp=person_model.predict(frame,classes=[0],conf=.1,imgsz=args.imgsz,device='cpu',verbose=False)[0]
                    people=[{'class':pp.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()} for b in pp.boxes]
                    detections=route_detections(detections,people)
                r=pipeline.update(idx/fps,detections,(h,w),cut);r['frame_index']=idx;r['scene_cut']=cut;r['detections']=detections
                records.append(r);canvas=frame.copy();polygon=np.array(pipeline.polygon,dtype=np.int32)
                cv2.polylines(canvas,[polygon],True,(255,190,0) if r['roi_active'] else (120,120,120),3)
                if approach_contours and r['roi_active']:cv2.drawContours(canvas,approach_contours,-1,(0,190,255),2)
                cv2.putText(canvas,('DEMO-ADAPTED / VEHICLE LANE / CONDITIONAL WARNING' if args.demo_adapted else 'VEHICLE LANE / CONDITIONAL PEDESTRIAN WARNING') if pipeline.lane else 'DEMO ROI / ACCESS + DWELL / NOT SITE VIOLATION',(15,30),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,190,255),2)
                cv2.putText(canvas,f"t={idx/fps:.2f}s  {'ROI ACTIVE' if r['roi_active'] else 'ROI RECONFIGURATION REQUIRED'}",(15,60),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,190,255),2)
                events={e['track_id']:e for e in r['events'] if e['event_type']=='zone_dwell'}
                access={e['track_id']:e for e in r['events'] if e['event_type']=='zone_access'}
                for track in r['tracks']:
                    event=events.get(track['track_id']);severity=event['severity'] if event else None
                    x1,y1,x2,y2=map(int,track['bbox_xyxy']);color=colors[severity]
                    access_event=access.get(track['track_id'])
                    box_severity=severity
                    if access_event:
                        rank={None:-1,'SAFE':0,'WARNING':1,'CRITICAL':2}
                        if rank[access_event['severity']]>rank[severity]:box_severity=access_event['severity']
                    cv2.rectangle(canvas,(x1,y1),(x2,y2),colors[box_severity],2)
                    if track['anchor_status']=='bbox_bottom_center_proxy':
                        a,b,c,d=track['detected_bbox_xyxy'];cv2.circle(canvas,(round((a+c)/2),round(d)),5,color,-1)
                    text=f"ID {track['track_id']} DWELL {severity or 'UNKNOWN'}"
                    if event:text+=f" {event['observed_dwell_seconds']:.1f}s"
                    cv2.putText(canvas,text,(x1,max(90,y1-7)),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
                    if access_event:
                        access_severity=access_event['severity']
                        cv2.putText(canvas,f"ACCESS {access_severity or 'UNKNOWN'}",(x1,max(115,y1+18)),cv2.FONT_HERSHEY_SIMPLEX,.6,colors[access_severity],2)
                if r.get('vehicle_lane_state'):cv2.putText(canvas,r['vehicle_lane_state']['state'],(15,90),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,190,255),2)
                for vehicle in r.get('forklifts',[]):
                    a,b,c,d=map(int,vehicle['detected_bbox_xyxy']);cv2.rectangle(canvas,(a,b),(c,d),(255,180,0),2)
                unknown=sum(e['severity'] is None for e in r['events'])
                if not r['tracks'] or unknown:
                    cv2.putText(canvas,f'UNCONFIRMED OBSERVATIONS: {unknown}',(15,90),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,190,255),2)
                writer.write(canvas)
                if len(records)-1 in {0,25,50,75}:cv2.imwrite(str(args.output/f'preview_{len(records)-1:04d}.jpg'),canvas)
            idx+=1
    finally:cap.release();writer.release()
    (args.output/'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    transitions=[e for r in records for e in r['transitions']]
    (args.output/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in transitions))
    export_events(records,args.output/'events_v1.jsonl',feature='zone',context={'camera_id':config['camera_id'],'video':args.source.name,'source_sha256':source_sha256,'model_version':effective_version,'config_version':hashlib.sha256(args.config.read_bytes()).hexdigest()})
    maxima={};critical=set();states={};access_states={};entries=[];exits=[]
    for r in records:
        for event in r['events']:
            if event['event_type']=='zone_access':
                state=event['severity'] or 'UNKNOWN';access_states[state]=access_states.get(state,0)+1
                if event['entry_observed']:entries.append({'track_id':event['track_id'],'timestamp_seconds':event['timestamp_seconds']})
                if event['exit_observed']:exits.append({'track_id':event['track_id'],'timestamp_seconds':event['timestamp_seconds']})
                continue
            key=event['track_id'];maxima[key]=max(maxima.get(key,0),event['observed_dwell_seconds'])
            state=event['severity'] or 'UNKNOWN';states[state]=states.get(state,0)+1
            if state=='CRITICAL':critical.add(key)
    summary={'source':str(args.source.resolve()),'source_sha256':source_sha256,
             'weights':str(args.weights.resolve()),'weights_sha256':hashlib.sha256(args.weights.read_bytes()).hexdigest(),
             'person_weights':str(args.person_weights.resolve()) if args.person_weights else None,'person_weights_sha256':person_hash,'model_version':effective_version,
             'demo_training_exposed':args.demo_adapted,'person_source_status':'experimental_not_promoted' if person_model else 'demo_adapted_candidate' if args.demo_adapted else 'configured_object_model','config':config,'frames_sampled':len(records),'processed_fps':fps/stride,'imgsz':args.imgsz,
             'transition_events':len(transitions),'state_observation_counts':states,
             'max_observed_dwell_by_track':maxima,'critical_track_ids':sorted(critical),
             'access_state_observation_counts':access_states,'observed_entries':entries,'observed_exits':exits,
             'limitation':'demo ROI, bbox footpoint proxy; missed people/ID switches possible; no independent ground truth'}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))


if __name__=='__main__':main()
