"""Re-evaluate policies over saved real model observations without inference."""
from pathlib import Path
import argparse,json,sys,hashlib
import cv2
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.ppe_events import PPEEvents
from src.ppe_unassigned_heads import UnassignedHeadEvents
from src.event_contract import export_events

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--policy',type=Path,required=True);args=p.parse_args()
 if args.output.exists():raise ValueError('Protected output')
 raw=args.run/'detections.jsonl';rows=[json.loads(v)for v in raw.read_text().splitlines()];summary=json.loads((args.run/'summary.json').read_text());policy=json.loads(args.policy.read_text());source=Path(summary['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==summary['event_context']['source_sha256'];cap=cv2.VideoCapture(str(source));shape=(int(cap.get(4)),int(cap.get(3)));cap.release();body=PPEEvents(policy);head=UnassignedHeadEvents(summary['processed_fps'],policy)if summary['unassigned_head_events']else None
 for row in rows:
  events,transitions=body.update(row['timestamp_seconds'],row['tracks'],row['missing_tracks'],row['scene_cut'])
  if head:
   extra,changes=head.update(row['timestamp_seconds'],row['head_detections']+[q for t in row['tracks'] for q in t['ppe']['head_candidates']], [t['detected_bbox_xyxy']for t in row['tracks']],shape,scene_cut=row['scene_cut'],body_events=events if policy.get('head_candidate_continuity') else None);events.extend(extra);transitions.extend(changes)
  row.update(events=events,transitions=transitions)
 context=dict(summary['event_context']);context['config_version']=hashlib.sha256(json.dumps({'parent_config_version':context['config_version'],'policy':policy,'saved_predictions_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'rule_history':'bare_evidence_v3'},sort_keys=True).encode()).hexdigest();args.output.mkdir(parents=True);(args.output/'detections.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in rows));export_events(rows,args.output/'events_v1.jsonl',feature='ppe',context=context);summary.update(events_require_rule_replay=False,policy=policy,event_context=context,rule_replay={'raw_predictions':str(raw.resolve()),'sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'new_inference':False},ppe_inference_mode='baseline_preserved_union_plus_helmet_specialist');(args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print({'frames':len(rows),'source':source.name,'replayed_real_predictions':True})
if __name__=='__main__':main()
