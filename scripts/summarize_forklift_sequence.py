"""Same reference and thresholds for both real inference caches; estimated continuity explicit."""
import json,argparse
from pathlib import Path
from src.ppe_tiled_inference import iou
ROOT=Path(__file__).resolve().parents[1]
def evaluate(rows,refs,w=1920,h=1080):
    anchors={r['frame_index']:[r['bbox_xyxy_400'][0]*w/400,r['bbox_xyxy_400'][1]*h/225,r['bbox_xyxy_400'][2]*w/400,r['bbox_xyxy_400'][3]*h/225]for r in refs};manual=[];diagnostic=[]
    for row in rows:
        idx=row['frame_index'];left=max((k for k in anchors if k<=idx),default=None);right=min((k for k in anchors if k>=idx),default=None)
        if left is None or right is None:continue
        f=(idx-left)/(right-left)if right!=left else 0;gt=[a+(b-a)*f for a,b in zip(anchors[left],anchors[right])];score=max([d['confidence']for d in row['detections']if iou(d['bbox_xyxy'],gt)>=.5],default=0);result={'frame_index':idx,'timestamp_seconds':row['timestamp_seconds'],'matched':score>=.25,'confidence':score};diagnostic.append(result)
        if idx in anchors:manual.append(result)
    longest=0;current=0;start=None;spans=[]
    for row in diagnostic:
        if not row['matched']:
            if current==0:start=row['frame_index']
            current+=1;longest=max(longest,current)
        elif current:spans.append({'start_frame':start,'end_frame':row['frame_index']-1,'frames':current});current=0
    if current:spans.append({'start_frame':start,'end_frame':diagnostic[-1]['frame_index'],'frames':current})
    return {'manual_anchor_count':len(manual),'manual_anchor_matches':sum(r['matched']for r in manual),'manual_anchor_misses':[r['frame_index']for r in manual if not r['matched']],'interpolated_diagnostic_frames':len(diagnostic),'interpolated_diagnostic_matches':sum(r['matched']for r in diagnostic),'interpolated_longest_unmatched_frames':longest,'interpolated_unmatched_spans':spans,'limits':'Whole-vehicle/cargo envelope match; body-only detections may fail IoU. Intermediate boxes are interpolation diagnostics, not manual ground truth.','anchors':manual}
def main():
    p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--new',type=Path);p.add_argument('--new-field',choices=['detections','fused_detections'],default='detections');p.add_argument('--output',type=Path,required=True);a=p.parse_args();refs=json.load(open(ROOT/'configs/review/reverse-main-vehicle-reference-v2.json'))['frames'];results={}
    for tag,path in [('old',a.old),('new',a.new)]:
        if path:
            rows=[json.loads(x)for x in path.read_text().splitlines()]
            if tag=='new' and a.new_field!='detections':rows=[{**row,'detections':row[a.new_field]}for row in rows]
            results[tag]=evaluate(rows,refs)
    a.output.write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({k:{f:r[f]for f in ['manual_anchor_matches','manual_anchor_count','interpolated_diagnostic_matches','interpolated_longest_unmatched_frames']}for k,r in results.items()}))
if __name__=='__main__':main()
