"""Independent feature banners and faint configured ROI fills."""
import cv2,numpy as np
from src.feature_status import feature_status
COLORS={'SAFE':(0,180,0),'WARNING':(0,140,255),'CRITICAL':(0,0,255),None:(150,150,150)}
def roi_overlay(frame,polygon,safe_polygons,severity,active=True):
 mask=np.zeros(frame.shape[:2],np.uint8);cv2.fillPoly(mask,[np.asarray(polygon,np.int32)],255)
 for p in safe_polygons:cv2.fillPoly(mask,[np.asarray(p,np.int32)],0)
 if not active:severity=None
 if severity is not None:
  layer=frame.copy();layer[mask>0]=COLORS[severity];alpha=.15 if severity=='SAFE'else .2;frame[:]=cv2.addWeighted(layer,alpha,frame,1-alpha,0)
 if active:
  layer=frame.copy()
  for p in safe_polygons:cv2.fillPoly(layer,[np.asarray(p,np.int32)],COLORS['SAFE'])
  frame[:]=cv2.addWeighted(layer,.15,frame,.85,0)
 for p in [polygon,*safe_polygons]:cv2.polylines(frame,[np.asarray(p,np.int32)],True,COLORS['SAFE'] if active and any(p is q for q in safe_polygons) else COLORS[severity],2)
 return frame

def render(frame,groups,zone=None):
 if zone:
  pipeline,row=zone;roi_overlay(frame,pipeline.polygon,getattr(pipeline,'safe_polygons',[]),feature_status(row['events'])['severity'],row['roi_active'])
 for feature,events in groups.items():
  for e in events:
   color=COLORS[e['severity'] if e.get('observation_status')=='confirmed'else None];box=e.get('person_bbox_xyxy',e.get('head_bbox_xyxy'))
   if feature=='ppe'and e['severity']=='WARNING':
    bare=[h for h in e.get('head_candidates',[])if h['class']=='no_helmet_head']
    if bare:box=max(bare,key=lambda h:h['confidence'])['bbox_xyxy']
   boxes=[box]if box else e.get('forklift_bboxes_xyxy',[])
   if e.get('forklift_bbox_xyxy'):boxes+=[e['forklift_bbox_xyxy']]
   for b in boxes:
    a,y,c,d=map(int,b);cv2.rectangle(frame,(a,y),(c,d),color,2)
    label=e['severity']or'UNKNOWN'
    if feature=='ppe':label='HELMET'if e['ppe_state']=='helmet_detected'and e['severity']=='SAFE'else'NO HELMET? REVIEW'if e['severity']=='WARNING'else'PPE UNKNOWN'
    if feature=='ppe'and e.get('hood_evidence'):label='PPE REVIEW: HOOD'if e['severity']=='WARNING'else'PPE UNKNOWN: HOOD'
    if 'observed_dwell_seconds'in e:label+=f" {e['observed_dwell_seconds']:.1f}s"
    cv2.putText(frame,label,(a,max(105,y-5)),0,.48,color,1)
 y=22
 for feature,events in groups.items():
  status=feature_status(events);color=COLORS[status['severity']];label=f"{feature.upper()}: {status['display_state']}  UNKNOWN={status['unknown_event_count']}"
  cv2.rectangle(frame,(5,y-17),(min(frame.shape[1]-5,660),y+5),(20,20,20),-1);cv2.putText(frame,label,(12,y),0,.55,color,2);y+=27
 return frame
