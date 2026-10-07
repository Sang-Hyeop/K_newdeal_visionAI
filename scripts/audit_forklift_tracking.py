"""Compare association settings using identical saved real detection evidence."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.person_tracker import PersonTracker
from src.ppe_tiled_inference import iou

def main():
 refs={r['frame_index']:[v*4.8 for v in r['bbox_xyxy_400']]for r in json.load(open(ROOT/'configs/review/reverse-main-vehicle-reference-v2.json'))['frames']};report={}
 for run in ['safe_carrying_envelope_v2_integrated','forklift_multiscale_review_v3']:
  report[run]={}
  for n in [2,3]:
   path=ROOT/f'outputs/diagnostics/{run}/video{n}';meta=json.load(open(path/'summary.json'));rows=list(map(json.loads,(path/'detections.jsonl').read_text().splitlines()));results={}
   for fuse in [True,False]:
    tracker=PersonTracker(meta['processed_fps'],target_class='forklift',namespace='F',fuse_score=fuse);ids=set();samples=0;anchors=[]
    for r in rows:
     tracks,missing=tracker.update(r['timestamp_seconds'],r['object_detections'],(1080,1920),r['scene_cut']);ids.update(t['track_id']for t in tracks);samples+=bool(tracks)
     if n==2 and r['frame_index']in refs:
      gt=refs[r['frame_index']];valid=[t for t in tracks if iou(t['detected_bbox_xyxy'],gt)>=.5];match=max(valid,key=lambda t:iou(t['detected_bbox_xyxy'],gt),default=None);anchors.append({'frame':r['frame_index'],'track_id':match['track_id']if match else None})
    matched=[x for x in anchors if x['track_id']];results[str(fuse)]={'observed_track_samples':samples,'all_scene_track_ids':len(ids),'manual_envelope_anchor_matches':len(matched),'matched_anchor_track_ids':len({x['track_id']for x in matched}),'anchors':anchors}
   report[run][str(n)]=results
 out=ROOT/'outputs/diagnostics/forklift_failure_audit_v1/tracking.json';out.write_text(json.dumps({'comparisons':report,'limits':['Track count includes false positives; fewer IDs alone does not prove better tracking','Coarse envelope references only, no manually labelled identity ground truth','No interpolated boxes are emitted for lost detections']},indent=2));print(json.dumps(report))
if __name__=='__main__':main()
