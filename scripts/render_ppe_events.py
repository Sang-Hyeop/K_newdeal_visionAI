"""Render saved real PPE observations without repeating inference or decisions."""
from pathlib import Path
import argparse,json,hashlib
import cv2

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--demo-adapted',action='store_true');p.add_argument('--warning-head-boxes',action='store_true');p.add_argument('--preview-indices',type=int,nargs='+',default=[25,50]);args=p.parse_args()
 if args.output.exists():raise ValueError('New rendering output required')
 summary=json.loads((args.run/'summary.json').read_text());source=Path(summary['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==summary['event_context']['source_sha256']
 rows=list(map(json.loads,(args.run/'detections.jsonl').read_text().splitlines()));cap=cv2.VideoCapture(str(source));w,h=int(cap.get(3)),int(cap.get(4));args.output.mkdir(parents=True)
 writer=cv2.VideoWriter(str(args.output/'ppe_events.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),summary['processed_fps'],(w,h))
 if not writer.isOpened():raise ValueError('Video writer failed')
 colors={'SAFE':(0,180,0),'WARNING':(0,190,255),None:(160,160,160)}
 try:
  for i,row in enumerate(rows):
   cap.set(1,row['frame_index']);ok,frame=cap.read();assert ok
   for e in row['events']:
    key='person_bbox_xyxy' if 'person_bbox_xyxy' in e else 'head_bbox_xyxy' if 'head_bbox_xyxy' in e else None
    if key is None:continue
    box=e[key]
    if args.warning_head_boxes and e['severity']=='WARNING':
     bare=[q for q in e.get('head_candidates',[]) if q['class']=='no_helmet_head']
     if bare:box=max(bare,key=lambda q:q['confidence'])['bbox_xyxy'];key='head_bbox_xyxy'
    a,b,c,d=map(int,box);color=colors[e['severity']];cv2.rectangle(frame,(a,b),(c,d),color,2)
    cv2.putText(frame,f"{'HEAD' if key=='head_bbox_xyxy' else 'ID'} {e['track_id']} {e['severity'] or 'UNKNOWN'}",(a,max(70,b-5)),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2)
   cv2.putText(frame,'DEMO-ADAPTED PPE / NO-HELMET CANDIDATES REQUIRE REVIEW' if args.demo_adapted else 'PPE OBSERVATIONS / NO-HELMET CANDIDATES REQUIRE REVIEW',(15,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,190,255),2)
   cv2.putText(frame,f"t={row['timestamp_seconds']:.2f}s",(15,50),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,190,255),2)
   writer.write(frame)
   if i in args.preview_indices:cv2.imwrite(str(args.output/f'preview_{i}.jpg'),frame)
 finally:cap.release();writer.release()
if __name__=='__main__':main()
