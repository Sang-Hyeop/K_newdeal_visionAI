"""Evaluate reviewed visible heads against real predictions, not state counts."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.ppe_tiled_inference import iou

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--references',type=Path,default=ROOT/'data/training_review/ppe_remaining_v2/global_target_references.json');p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 refs=json.loads(args.references.read_text());rows=[json.loads(s)for s in (args.input/'detections.jsonl').read_text().splitlines()];details=[];totals={str(c):{'visible_heads':0,'detected_heads':0,'misses':0}for c in [0,1]}
 for frame_index,objects in refs.items():
  if not objects:continue
  # Source-time sampling can be at most two frames away at 5 Hz.
  row=min(rows,key=lambda r:abs(r['frame_index']-int(frame_index)))
  if abs(row['frame_index']-int(frame_index))>2:continue
  truth=[]
  for obj in objects:
   if not any(obj['class_id']==t['class_id'] and iou(obj['bbox_xyxy'],t['bbox_xyxy'])>=.65 for t in truth):truth.append(obj)
  proposals=list(row.get('head_detections',[]))
  for t in row['tracks']:proposals.extend(t['ppe']['head_candidates'])
  matches=[]
  for obj in truth:
   label='helmeted_head' if obj['class_id']==0 else 'no_helmet_head'
   eligible=[h for h in proposals if h['class']==label and h['confidence']>=.5]
   overlap=max((iou(obj['bbox_xyxy'],h['bbox_xyxy'])for h in eligible),default=0);found=overlap>=.5
   totals[str(obj['class_id'])]['visible_heads']+=1;totals[str(obj['class_id'])]['detected_heads']+=int(found);totals[str(obj['class_id'])]['misses']+=int(not found)
   matches.append({**obj,'detected':found,'best_iou':overlap})
  details.append({'reference_frame':int(frame_index),'evaluated_frame':row['frame_index'],'heads':matches})
 report={'input':str(args.input),'confidence':.5,'iou':.5,'training_exposed':True,'annotation_scope':'primary visible heads in manually reviewed crops; not exhaustive every-frame ground truth','frame_tolerance':2,'metrics':totals,'records':details};args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(totals))
if __name__=='__main__':main()
