"""Interpolated bare-head review diagnostic; not exhaustive manual GT."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.ppe_tiled_inference import iou

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();refs=json.loads((ROOT/'data/training_review/ppe_remaining_v2/global_target_references_v3.json').read_text());rows=[json.loads(v)for v in (args.run/'detections.jsonl').read_text().splitlines()];summary=json.loads((args.run/'summary.json').read_text());warning_threshold=summary['policy'].get('minimum_no_helmet_candidate_confidence',.5);fps=rows[1]['frame_index']/rows[1]['timestamp_seconds']
 trajectories={name:sorted([(int(k),h['bbox_xyxy'])for k,v in refs.items()for h in v if h['class_id']==1 and h['target_index']in ids])for name,ids in {'bare_man':{0,1,2,6,8,17,24,32,38,43,56},'bare_woman':{11,16,22,30,37,44,52}}.items()};findings=[]
 for name,keys in trajectories.items():
  for row in rows:
   f=row['frame_index']
   if not keys[0][0]<=f<=keys[-1][0]:continue
   left=max((k for k in keys if k[0]<=f),key=lambda k:k[0]);right=min((k for k in keys if k[0]>=f),key=lambda k:k[0]);ratio=0 if left[0]==right[0]else(f-left[0])/(right[0]-left[0]);gt=[a+(b-a)*ratio for a,b in zip(left[1],right[1])];heads=list(row['head_detections'])
   for track in row['tracks']:heads.extend(track['ppe']['head_candidates'])
   detected=any(h['class']=='no_helmet_head' and h['confidence']>=.5 and iou(gt,h['bbox_xyxy'])>=.5 for h in heads);mature=(f-keys[0][0])/fps>=summary['policy']['minimum_confirmed_seconds'];warning=any(e['severity']=='WARNING' and any(h['class']=='no_helmet_head' and h['confidence']>=warning_threshold and iou(gt,h['bbox_xyxy'])>=.5 for h in e.get('head_candidates',[]))for e in row['events']);false_safe=any(e['severity']=='SAFE' and any(iou(gt,h['bbox_xyxy'])>=.5 for h in e.get('head_candidates',[]))for e in row['events']);findings.append({'subject':name,'frame_index':f,'bbox_xyxy':gt,'detected':detected,'mature':mature,'warning':warning,'false_safe':false_safe})
 report={'scope':'Interpolated between manually reviewed head keyframes, sampled ~4.8 FPS, adaptation diagnostic; not exhaustive manual every-frame GT','detection_confidence':.5,'review_warning_candidate_confidence':warning_threshold,'iou':.5,'observations':len(findings),'detected':sum(r['detected']for r in findings),'misses':sum(not r['detected']for r in findings),'mature_alert_observations':sum(r['mature']for r in findings),'mature_warning':sum(r['mature']and r['warning']for r in findings),'mature_alert_gaps':[r for r in findings if r['mature']and not r['warning']],'false_safe':[r for r in findings if r['false_safe']],'records':findings};args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='records'}))
if __name__=='__main__':main()
