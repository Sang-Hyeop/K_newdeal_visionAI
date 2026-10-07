"""Saved-video person tracking and per-observation PPE; no risk decisions."""
from pathlib import Path
import argparse,json,os,sys,math,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,numpy as np,torch
from ultralytics import YOLO
from src.person_tracker import PersonTracker
from src.ppe_events import PPEEvents
from src.ppe_unassigned_heads import UnassignedHeadEvents
from src.event_contract import export_events
from src.ppe_person_crop import infer_person_ppe,head_owner
from src.ppe_tiled_inference import infer_tiled_heads
from src.ppe_head_context import refine_weak_heads
from src.ppe_recall_ensemble import PPERecallEnsemble
from src.object_recall_ensemble import ObjectRecallEnsemble


def main():
    p=argparse.ArgumentParser()
    for name in ['source','output','objects-weights','ppe-weights']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--supplement-object-weights',type=Path)
    p.add_argument('--supplement-ppe-weights',type=Path)
    p.add_argument('--ppe-preserve-union',action='store_true');p.add_argument('--helmet-specialist-weights',type=Path)
    p.add_argument('--config',type=Path,default=ROOT/'configs/ppe-event-policy.json')
    p.add_argument('--ppe-crop-height',type=float,default=.55)
    p.add_argument('--tiled-head-search',action='store_true')
    p.add_argument('--unassigned-head-events',action='store_true')
    p.add_argument('--sample-fps',type=float,default=5)
    p.add_argument('--object-imgsz',type=int,default=640)
    p.add_argument('--ppe-candidate-tracks',action='store_true');p.add_argument('--weak-head-context-recheck',action='store_true')
    p.add_argument('--scene-cut-threshold',type=float,default=.18)
    args=p.parse_args()
    if args.object_imgsz<320 or args.object_imgsz%32:raise ValueError('Object size must be a multiple of 32, at least 320')
    if args.output.exists() or not math.isfinite(args.sample_fps) or args.sample_fps<=0:
        raise ValueError('New output and finite positive FPS required')
    if not math.isfinite(args.ppe_crop_height) or not .35<=args.ppe_crop_height<=1:raise ValueError('PPE crop height must be in [.35, 1]')
    if not 0<args.scene_cut_threshold<=1:raise ValueError('Invalid scene cut threshold')
    if args.helmet_specialist_weights and not args.ppe_preserve_union:raise ValueError('Helmet specialist requires preserved PPE union')
    if args.ppe_preserve_union and not args.supplement_ppe_weights:raise ValueError('PPE union requires supplement weights')
    torch.set_num_threads(4)
    objects,ppe=YOLO(str(args.objects_weights)),YOLO(str(args.ppe_weights))
    if args.supplement_object_weights:
        objects=ObjectRecallEnsemble(objects,YOLO(str(args.supplement_object_weights)))
    if args.supplement_ppe_weights:
        ppe=PPERecallEnsemble(ppe,YOLO(str(args.supplement_ppe_weights)),preserve_union=args.ppe_preserve_union,helmet_specialist=YOLO(str(args.helmet_specialist_weights))if args.helmet_specialist_weights else None)
    if objects.names.get(0)!='person':raise ValueError('Expected person class at index 0')
    cap=cv2.VideoCapture(str(args.source));fps=cap.get(5);w,h=int(cap.get(3)),int(cap.get(4))
    if not cap.isOpened() or fps<=0:raise ValueError('Unreadable video')
    stride=max(1,round(fps/args.sample_fps));tracker=PersonTracker(fps/stride,expose_current_candidates=args.ppe_candidate_tracks)
    args.output.mkdir(parents=True)
    writer=cv2.VideoWriter(str(args.output/'tracked_ppe.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps/stride,(w,h))
    if not writer.isOpened():raise RuntimeError('Cannot open video writer')
    policy=json.loads(args.config.read_text());event_rule=PPEEvents(policy)
    head_rule=UnassignedHeadEvents(fps/stride,policy) if args.unassigned_head_events else None
    records=[];idx=0;previous=None
    try:
        while True:
            ok,frame=cap.read()
            if not ok:break
            if idx%stride==0:
                small=cv2.resize(frame,(96,54)).astype(np.float32)/255
                cut_score=0. if previous is None else float(np.mean(np.abs(small-previous)))
                cut=cut_score>args.scene_cut_threshold;previous=small
                result=objects.predict(frame,classes=[0],conf=.1,imgsz=args.object_imgsz,device='cpu',verbose=False)[0]
                detections=[{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),
                             'bbox_xyxy':b.xyxy[0].tolist(),'detection_source':getattr(b,'detection_source','single_object_model')} for b in result.boxes]
                timestamp=idx/fps;tracks,missing=tracker.update(timestamp,detections,(h,w),scene_cut=cut)
                raw=ppe.predict(frame,conf=.25,imgsz=640,device='cpu',verbose=False)[0]
                heads=[{'class':raw.names[int(b.cls.item())],'confidence':float(b.conf.item()),
                        'bbox_xyxy':b.xyxy[0].tolist(), 'model_sources':getattr(b,'model_sources',['single_ppe_model'])} for b in raw.boxes]
                tile_rejected=[]
                if args.tiled_head_search:
                    tiled,tile_rejected=infer_tiled_heads(frame,ppe)
                    heads.extend(tiled)
                observations=infer_person_ppe(frame,[t['detected_bbox_xyxy'] for t in tracks],ppe,full_frame_heads=heads,crop_height_fraction=args.ppe_crop_height)
                if args.weak_head_context_recheck:
                    proposals=heads+[q for o in observations for q in o['head_candidates']]
                    heads.extend(refine_weak_heads(frame,proposals,ppe));proposals=heads+[q for o in observations for q in o['head_candidates']]
                    people=[t['detected_bbox_xyxy'] for t in tracks]
                    for i,observation in enumerate(observations):
                        matched=[q for q in proposals if head_owner(q['bbox_xyxy'],people,h)==i];classes={q['class'] for q in matched}
                        observation.update(head_candidates=matched,state='helmet_detected' if classes=={'helmeted_head'} else 'no_helmet_candidate' if classes=={'no_helmet_head'} else 'conflicting_evidence' if len(classes)>1 else 'unknown')
                canvas=frame.copy()
                for track,observation in zip(tracks,observations):
                    observation['track_id']=track['track_id'];track['ppe']=observation
                    x1,y1,x2,y2=map(int,track['bbox_xyxy']);color=(0,180,0) if observation['state']=='helmet_detected' else (0,190,255)
                    cv2.rectangle(canvas,(x1,y1),(x2,y2),color,2)
                    cv2.putText(canvas,f"ID {track['track_id']} {observation['state']}",(x1,max(50,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1)
                    for head in observation['head_candidates']:
                        a,b,c,d=map(int,head['bbox_xyxy']);cv2.rectangle(canvas,(a,b),(c,d),(255,200,0),1)
                events,transitions=event_rule.update(timestamp,tracks,missing,scene_cut=cut)
                if head_rule:
                    head_events,head_transitions=head_rule.update(timestamp,heads+[q for t in tracks for q in t['ppe']['head_candidates']], [t['detected_bbox_xyxy'] for t in tracks],(h,w),scene_cut=cut,body_events=events if policy.get('head_candidate_continuity') else None)
                    events.extend(head_events);transitions.extend(head_transitions)
                    for event in head_events:
                        if 'head_bbox_xyxy' in event:
                            a,b,c,d=map(int,event['head_bbox_xyxy']);color=(0,190,255) if event['severity']=='WARNING' else (160,160,160)
                            cv2.rectangle(canvas,(a,b),(c,d),color,2)
                            cv2.putText(canvas,'HEAD '+(event['severity'] or 'UNKNOWN'),(a,max(65,b-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1)
                for event in events:
                    if 'person_bbox_xyxy' in event:
                        x,y,x2,y2=map(int,event['person_bbox_xyxy']);cv2.rectangle(canvas,(x,y),(x2,y2),{'SAFE':(0,180,0),'WARNING':(0,190,255),None:(160,160,160)}[event['severity']],2);cv2.putText(canvas,event['severity'] or 'UNKNOWN',(x,max(75,y+20)),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,180,0) if event['severity']=='SAFE' else (0,190,255),2)
                cv2.putText(canvas,'PPE CANDIDATES / NOT VERIFIED VIOLATIONS',(15,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,200,255),2)
                if cut:cv2.putText(canvas,'SCENE RESET',(15,50),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,80,255),2)
                writer.write(canvas)
                if len(records) in {0,25,50}:cv2.imwrite(str(args.output/f'preview_{len(records):04d}.jpg'),canvas)
                records.append({'timestamp_seconds':timestamp,'frame_index':idx,'scene_id':tracker.scene,
                                'scene_cut':cut,'scene_cut_score':cut_score,'tracks':tracks,
                                'object_detections':detections,'head_detections':heads,'unassigned_heads':[head for head in heads if head_owner(head['bbox_xyxy'],[t['detected_bbox_xyxy'] for t in tracks],h) is None],'rejected_tile_heads':tile_rejected,'missing_tracks':missing,'events':events,'transitions':transitions,'risk_status':'not_evaluated'})
            idx+=1
    finally:cap.release();writer.release()
    (args.output/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    model_hash={key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in [('objects',args.objects_weights),('ppe',args.ppe_weights)]}
    if args.supplement_object_weights:
        model_hash['objects_supplement']=hashlib.sha256(args.supplement_object_weights.read_bytes()).hexdigest()
    if args.supplement_ppe_weights:
        model_hash['ppe_supplement']=hashlib.sha256(args.supplement_ppe_weights.read_bytes()).hexdigest()
    if args.helmet_specialist_weights:model_hash['helmet_specialist']=hashlib.sha256(args.helmet_specialist_weights.read_bytes()).hexdigest()
    context={'camera_id':args.source.stem+'-ppe','video':args.source.name,'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),'model_version':hashlib.sha256(json.dumps(model_hash,sort_keys=True).encode()).hexdigest(),'config_version':hashlib.sha256(json.dumps({'policy':policy,'sample_fps':args.sample_fps,'cut_threshold':args.scene_cut_threshold,'ppe_crop_height':args.ppe_crop_height,'head_assignment_version':'clipped_body_head_v2','tiled_head_search':args.tiled_head_search,'unassigned_head_events':args.unassigned_head_events,'ppe_preserve_union':args.ppe_preserve_union,'object_imgsz':args.object_imgsz,'ppe_candidate_tracks':args.ppe_candidate_tracks,'weak_head_context_recheck':args.weak_head_context_recheck},sort_keys=True).encode()).hexdigest()}
    export_events(records,args.output/'events_v1.jsonl',feature='ppe',context=context)
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
             'supplement_object_weights':str(args.supplement_object_weights.resolve()) if args.supplement_object_weights else None,
             'supplement_ppe_weights':str(args.supplement_ppe_weights.resolve()) if args.supplement_ppe_weights else None,
             'helmet_specialist_weights':str(args.helmet_specialist_weights.resolve())if args.helmet_specialist_weights else None,
             'ppe_head_assignment_version':'clipped_body_head_v2','tiled_head_search':args.tiled_head_search,'unassigned_head_events':args.unassigned_head_events,'ppe_preserve_union':args.ppe_preserve_union,'object_imgsz':args.object_imgsz,'ppe_candidate_tracks':args.ppe_candidate_tracks,'weak_head_context_recheck':args.weak_head_context_recheck,
             'ppe_crop_height_fraction':args.ppe_crop_height,
             'ppe_inference_mode':'baseline_preserved_union_plus_helmet_specialist' if args.helmet_specialist_weights else 'baseline_preserved_union' if args.ppe_preserve_union else 'baseline_plus_bare_head_supplement' if args.supplement_ppe_weights else 'single_model',
             'model_hashes':model_hash,'policy':policy,'event_context':context,'limitations':'No ground-truth accuracy; hood ambiguity persists; no-helmet is a review candidate; missing people remain UNKNOWN'}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))


if __name__=='__main__':main()
