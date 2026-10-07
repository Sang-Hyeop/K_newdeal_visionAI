"""Render stored lane observations without changing detections or decisions."""
from pathlib import Path
import argparse,json,hashlib
import cv2,numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 if args.output.exists():raise ValueError('New output required')
 s=json.loads((args.run/'summary.json').read_text());source=Path(s['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==s['source_sha256']
 rows=list(map(json.loads,(args.run/'observations.jsonl').read_text().splitlines()));cap=cv2.VideoCapture(str(source));w,h=int(cap.get(3)),int(cap.get(4));polygon=np.array([[x*w,y*h] for x,y in s['config']['polygon_normalized']],np.int32)
 args.output.mkdir(parents=True);writer=cv2.VideoWriter(str(args.output/'vehicle_lane.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),s['processed_fps'],(w,h))
 if not writer.isOpened():raise ValueError('Video writer failed')
 colors={'SAFE':(0,180,0),'WARNING':(0,190,255),'CRITICAL':(0,0,255),None:(160,160,160)}
 try:
  for i,r in enumerate(rows):
   cap.set(1,r['frame_index']);ok,frame=cap.read();assert ok
   cv2.polylines(frame,[polygon],True,(255,190,0),3)
   states={e['track_id']:e for e in r['events'] if e['event_type']=='zone_dwell'}
   for track in r['tracks']:
    e=states.get(track['track_id']);box=track['detected_bbox_xyxy'];a,b,c,d=map(int,box)
    inside=e and e['inside'];color=colors[e['severity']] if inside else (150,150,150)
    cv2.rectangle(frame,(a,b),(c,d),color,2)
    text=f"{track['track_id']} OUTSIDE LANE" if e and e['inside'] is False else f"{track['track_id']} {e['severity'] or 'UNKNOWN'} {e['observed_dwell_seconds']:.1f}s" if e else f"{track['track_id']} UNKNOWN"
    cv2.putText(frame,text,(a,max(150,b-8)),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2)
   for vehicle in r.get('forklifts',[]):
    a,b,c,d=map(int,vehicle['detected_bbox_xyxy']);cv2.rectangle(frame,(a,b),(c,d),(255,180,0),2)
   cv2.rectangle(frame,(0,0),(920,115),(30,30,30),-1)
   cv2.putText(frame,'VEHICLE LANE: PEDESTRIAN WARNING / VEHICLE PRESENT CRITICAL',(15,25),cv2.FONT_HERSHEY_SIMPLEX,.58,(0,190,255),2)
   state=r['vehicle_lane_state']['state'] if r.get('vehicle_lane_state') else 'ROI INACTIVE'
   cv2.putText(frame,f"t={r['timestamp_seconds']:.2f}s {state}",(15,55),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,190,255),2)
   cv2.putText(frame,'NO DETECTION IS NOT PROOF OF ABSENCE / IMAGE ANCHORS',(15,88),cv2.FONT_HERSHEY_SIMPLEX,.55,(180,180,180),2)
   writer.write(frame)
   if i in [25,50,75]:cv2.imwrite(str(args.output/f'preview_{i}.jpg'),frame)
 finally:cap.release();writer.release()
if __name__=='__main__':main()
