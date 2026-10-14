"""Side-by-side geometry experiment. Dashed lines are diagnostics, not risk events."""
from pathlib import Path
import argparse,json,cv2,numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 left=list(map(json.loads,(a.before/'detections.jsonl').read_text().splitlines()));right=list(map(json.loads,(a.after/'detections.jsonl').read_text().splitlines()));assert len(left)==len(right)
 ca,cb=cv2.VideoCapture(str(a.before/'demo.mp4')),cv2.VideoCapture(str(a.after/'demo.mp4'));rate=ca.get(5);assert abs(rate-cb.get(5))<1e-6
 writer=cv2.VideoWriter(str(a.output/'comparison_raw.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),rate,(1920,700));focus=cv2.VideoWriter(str(a.output/'focus_raw.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),rate,(1920,700));assert writer.isOpened()and focus.isOpened();changed=[];focus_count=0;key_details=[]
 for old,new in zip(left,right):
  assert old['frame_index']==new['frame_index'] and old['object_detections']==new['object_detections']
  assert old['feature_events']['ppe']==new['feature_events']['ppe'];assert old['feature_events']['zone_dwell']==new['feature_events']['zone_dwell']
  oka,fa=ca.read();okb,fb=cb.read();assert oka and okb
  canvas=np.zeros((700,1920,3),np.uint8);canvas[50:590,:960]=cv2.resize(fa,(960,540));canvas[50:590,960:]=cv2.resize(fb,(960,540));cv2.putText(canvas,'A: NEAREST BOX EDGE - EXISTING',(12,30),0,.65,(255,255,255),2);cv2.putText(canvas,'B: BOTTOM CENTRE - EXPERIMENT',(972,30),0,.65,(255,255,255),2)
  t=old['timestamp_seconds'];cv2.putText(canvas,f't={t:.2f}s / SAME DETECTIONS, THRESHOLDS AND RIDER-ROI RULES / NOT METRES',(12,612),0,.5,(220,220,220),1)
  pool=new['feature_events']['proximity']+new['proximity_tracking'].get('suppressed_proximity_events',[]);lookup={(e.get('person_track_id'),e.get('forklift_track_id')):e for e in pool}
  for i,e in enumerate([e for e in old['feature_events']['proximity']if e.get('distance_display_enabled')][:4]):
   key=(e['person_track_id'],e['forklift_track_id']);q=lookup.get(key)
   if not q or q.get('normalized_image_gap')is None:continue
   state=q.get('severity')or'CHECK';line=f"{key[0]} -> {key[1]}: {e.get('severity')} {e['normalized_image_gap']:.2f}  ->  {state} {q['normalized_image_gap']:.2f}"
   cv2.putText(canvas,line,(12,633+i*16),0,.43,(220,220,220),1)
   if e.get('severity')!=q.get('severity'):changed.append({'t':t,'person':key[0],'vehicle':key[1],'before':e.get('severity'),'after':q.get('severity')})
   if not q.get('distance_display_enabled') and q.get('nearest_vehicle_point_xy'):
    start=np.asarray(q['person_anchor_xy'])*.75+np.array([960,50]);end=np.asarray(q['nearest_vehicle_point_xy'])*.75+np.array([960,50])
    for s in np.arange(0,1,.12):
     aa=start+(end-start)*s;bb=start+(end-start)*min(1,s+.06);cv2.line(canvas,tuple(aa.astype(int)),tuple(bb.astype(int)),(170,170,170),2)
   if abs(t-18.541666666666668)<.01:key_details.append({'person':key[0],'before':e.get('severity'),'before_ratio':e['normalized_image_gap'],'after':q.get('severity'),'after_ratio':q['normalized_image_gap'],'right_panel_alarm':q.get('notification_enabled',False)})
  cv2.putText(canvas,'DASHED LINES: diagnostic distance for pairs hidden by ROI policy; NOT an alarm',(1000,684),0,.38,(200,200,200),1);writer.write(canvas)
  if 14<=t<=23:focus.write(canvas);focus_count+=1
  if abs(t-18.541666666666668)<.01:cv2.imwrite(str(a.output/'comparison_18_54.jpg'),canvas)
 writer.release();focus.release();ca.release();cb.release();(a.output/'comparison_summary.json').write_text(json.dumps({'frames':len(left),'fps':rate,'focus_frames':focus_count,'changed_pair_observations':len(changed),'key_18_54':key_details,'changes':changed,'status':'experimental_not_promoted','unchanged':'detections, PPE, zone dwell, rider/ROI gates, threshold values; baseline files and config unchanged'},indent=2)+'\n');print('frames',len(left),'changed pair observations',len(changed),'key',key_details)
if __name__=='__main__':main()
