"""Opt-in hood inference on cached real detections; preserve risk warnings and veto SAFE."""
from pathlib import Path
import os,sys,json,argparse,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'outputs/runtime/cache'))
import torch,cv2
from ultralytics import YOLO
from src.hoodie_guard import apply_hood_guard,predict_hood_detections
from src.scenario_render import render
from src.feature_status import feature_status
from src.event_contract import export_events

def main():
 p=argparse.ArgumentParser();p.add_argument('--video',type=int,choices=[5,6],required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reuse-run',type=Path);args=p.parse_args()
 if args.output.exists():raise ValueError('Preserve existing outputs')
 cache=ROOT/f'outputs/diagnostics/scenario_plan_v2_conservative_ppe/video{args.video}';summary=json.loads((cache/'summary.json').read_text());weights=ROOT/'models/hoodie_auxiliary_v1/hoodie.pt';model=None if args.reuse_run else YOLO(str(weights));torch.set_num_threads(2);saved={}
 if args.reuse_run:
  prior=json.loads((args.reuse_run/'summary.json').read_text());assert prior['source_sha256']==summary['source_sha256'] and prior['hood_weights_sha256']==hashlib.sha256(weights.read_bytes()).hexdigest();saved={r['frame_index']:r['hood_detections']for r in map(json.loads,(args.reuse_run/'detections.jsonl').read_text().splitlines())}
 source=Path(summary['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==summary['source_sha256'];cap=cv2.VideoCapture(str(source));h,w=int(cap.get(4)),int(cap.get(3));args.output.mkdir(parents=True);writer=cv2.VideoWriter(str(args.output/'demo.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),summary['processed_fps'],(w,h));records=[];observations=[];previous={}
 for row in map(json.loads,(cache/'detections.jsonl').read_text().splitlines()):
  cap.set(1,row['frame_index']);ok,frame=cap.read()
  if not ok:raise RuntimeError('Frame read failed')
  if saved:predictions=saved[row['frame_index']]
  else:
   person_boxes=[tr.get('detected_bbox_xyxy')or tr.get('bbox_xyxy')for tr in row['ppe_tracks']]
   predictions=predict_hood_detections(model,frame,person_boxes,confidence=.25)
  events=apply_hood_guard(row['feature_events']['ppe'],predictions,minimum_confidence=.25);groups={**row['feature_events'],'ppe':events};row.update(feature_events=groups,features={k:feature_status(v)for k,v in groups.items()},hood_detections=predictions,hood_auxiliary_status='experimental');records.append(row);transitions=[]
  for event in events:
   key=event.get('track_id');state=(event.get('severity'),event.get('observation_status'),event.get('reason'),bool(event.get('hood_evidence')))
   if previous.get(key)!=state:transitions.append(event)
   previous[key]=state
  observations.append({'frame_index':row['frame_index'],'timestamp_seconds':row['timestamp_seconds'],'events':events,'transitions':transitions})
  canvas=render(frame.copy(),groups)
  for event in events:
   if event.get('hood_evidence'):
    d=max(event['hood_evidence'],key=lambda q:q['confidence'])
    x,y,a,b=map(int,d['bbox_xyxy']);cv2.rectangle(canvas,(x,y),(a,b),(255,180,0),2);cv2.putText(canvas,f"HOOD? REVIEW {d['confidence']:.2f}",(x,max(110,y-15)),0,.48,(255,180,0),1)
  writer.write(canvas)
 cap.release();writer.release();(args.output/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in records));context=dict(summary['context']);context['model_version']=hashlib.sha256((context['model_version']+hashlib.sha256(weights.read_bytes()).hexdigest()).encode()).hexdigest();context['config_version']='experimental_hood_safe_veto_v1';export_events(observations,args.output/'events_v1.jsonl',feature='ppe',context=context);summary['features']={k:{state:sum(feature_status(r['feature_events'][k])['display_state']==state for r in records)for state in ['SAFE','WARNING','CRITICAL','UNKNOWN']}for k in records[0]['feature_events']}
 summary.update(status='experimental_not_promoted',hood_weights_sha256=hashlib.sha256(weights.read_bytes()).hexdigest(),context=context,hood_samples=sum(bool(e.get('hood_evidence'))for r in records for e in r['feature_events']['ppe']),hood_safe_vetoes=sum(e.get('reason')=='hood_and_helmet_evidence_requires_review'for r in records for e in r['feature_events']['ppe']));(args.output/'summary.json').write_text(json.dumps(summary,indent=2));print('hood replay complete',args.video,flush=True)
if __name__=='__main__':main()
