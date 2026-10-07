"""Add real contextual head inferences to saved observations; no GT-dependent crops."""
import argparse,json,sys,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,torch
from ultralytics import YOLO
from src.ppe_recall_ensemble import PPERecallEnsemble
from src.ppe_head_context import refine_weak_heads
from src.ppe_person_crop import head_owner

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Protected output')
 torch.set_num_threads(4);s=json.loads((a.run/'summary.json').read_text());rows=list(map(json.loads,(a.run/'detections.jsonl').read_text().splitlines()));source=Path(s['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==s['event_context']['source_sha256'];
 for key,path in [('ppe',s['weights']['ppe']),('ppe_supplement',s['supplement_ppe_weights']),('helmet_specialist',s['helmet_specialist_weights'])]:assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==s['model_hashes'][key]
 m=PPERecallEnsemble(YOLO(s['weights']['ppe']),YOLO(s['supplement_ppe_weights']),preserve_union=True,helmet_specialist=YOLO(s['helmet_specialist_weights']));cap=cv2.VideoCapture(str(source));count=0
 try:
  for r in rows:
   cap.set(1,r['frame_index']);ok,frame=cap.read();assert ok
   proposals=list(r['head_detections'])+[h for t in r['tracks'] for h in t['ppe']['head_candidates']];extra=refine_weak_heads(frame,proposals,m);count+=len(extra);proposals+=extra;r['head_detections']+=extra;people=[t['detected_bbox_xyxy']for t in r['tracks']]
   for i,t in enumerate(r['tracks']):
    heads=[h for h in proposals if head_owner(h['bbox_xyxy'],people,frame.shape[0])==i];classes={h['class']for h in heads};t['ppe'].update(head_candidates=heads,state='helmet_detected'if classes=={'helmeted_head'}else'no_helmet_candidate'if classes=={'no_helmet_head'}else'conflicting_evidence'if len(classes)>1 else'unknown')
 finally:cap.release()
 a.output.mkdir(parents=True);(a.output/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in rows));s.update(weak_head_context_recheck=True,context_recheck_predictions=count,events_require_rule_replay=True);s['event_context']['config_version']=hashlib.sha256(json.dumps({'parent':s['event_context']['config_version'],'context_scales':[2.5,4],'weak_threshold':[.25,.5],'maximum_candidates':10},sort_keys=True).encode()).hexdigest();(a.output/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print({'real_context_predictions':count,'frames':len(rows)})
if __name__=='__main__':main()
