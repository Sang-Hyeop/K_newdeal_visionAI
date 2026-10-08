"""Independent feature banners and faint configured ROI fills."""
import cv2,numpy as np
from src.feature_status import feature_status
COLORS={'SAFE':(0,180,0),'WARNING':(0,140,255),'CRITICAL':(0,0,255),None:(150,150,150)}
def roi_overlay(frame,polygon,safe_polygons,severity,active=True,alpha_safe=.15,alpha_alert=.2):
 mask=np.zeros(frame.shape[:2],np.uint8);cv2.fillPoly(mask,[np.asarray(polygon,np.int32)],255)
 for p in safe_polygons:cv2.fillPoly(mask,[np.asarray(p,np.int32)],0)
 if not active:severity=None
 if severity is not None:
  layer=frame.copy();layer[mask>0]=COLORS[severity];alpha=alpha_safe if severity=='SAFE'else alpha_alert;frame[:]=cv2.addWeighted(layer,alpha,frame,1-alpha,0)
 if active:
  layer=frame.copy()
  for p in safe_polygons:cv2.fillPoly(layer,[np.asarray(p,np.int32)],COLORS['SAFE'])
  frame[:]=cv2.addWeighted(layer,alpha_safe,frame,1-alpha_safe,0)
 for p in [polygon,*safe_polygons]:cv2.polylines(frame,[np.asarray(p,np.int32)],True,COLORS['SAFE'] if active and any(p is q for q in safe_polygons) else COLORS[severity],2)
 return frame

def render(frame,groups,zone=None,detections=None):
 if zone:
  pipeline,row=zone;cfg=getattr(pipeline,'config',{})
  roi_overlay(frame,pipeline.polygon,getattr(pipeline,'safe_polygons',[]),feature_status(row['events'])['severity'],row['roi_active'],cfg.get('roi_alpha_safe',.15),cfg.get('roi_alpha_alert',.2))
 if detections is not None:
  draw_review_objects(frame,detections,groups)
 for feature,events in groups.items():
  if detections is not None:continue
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
    if feature=='ppe'and e.get('vehicle_overlap_review_required')and e['severity']=='WARNING':label='PPE REVIEW: VEHICLE OVERLAP'
    if feature=='ppe'and e.get('hood_evidence'):label='PPE REVIEW: HOOD'if e['severity']=='WARNING'else'PPE UNKNOWN: HOOD'
    if 'observed_dwell_seconds'in e:label+=f" {e['observed_dwell_seconds']:.1f}s"
    cv2.putText(frame,label,(a,max(105,y-5)),0,.48,color,1)
 y=22
 for feature,events in groups.items():
  status=feature_status(events);color=COLORS[status['severity']];label=f"{feature.upper()}: {status['display_state']}  UNKNOWN={status['unknown_event_count']}"
  cv2.rectangle(frame,(5,y-17),(min(frame.shape[1]-5,660),y+5),(20,20,20),-1);cv2.putText(frame,label,(12,y),0,.55,color,2);y+=27
 return frame


def select_proximity_display_event(events):
 """Return the closest pair even when its proximity remains ambiguous.

 A confirmed SAFE relation to a distant vehicle must not hide a closer pair
 whose proximity could not be classified. Such a pair is rendered UNKNOWN.
 """
 pairs=[e for e in events if e.get('person_anchor_xy') and e.get('nearest_vehicle_point_xy') and e.get('normalized_image_gap') is not None]
 return min(pairs,key=lambda e:e['normalized_image_gap']) if pairs else None


def draw_review_objects(frame,detections,groups):
 """Draw each observed object once; unassociated head proposals stay in diagnostics."""
 for d in detections:
  if d['confidence']<.25:continue
  a,y,c,b=map(int,d['bbox_xyxy']);color=(255,170,0)if d['class']=='person'else(0,210,255)
  cv2.rectangle(frame,(a,y),(c,b),color,2)
  cv2.putText(frame,f"{d['class'].upper()} {d['confidence']:.2f}",(a,max(105,y-5)),0,.5,color,1)
 for e in groups.get('ppe',[]):
  if not e.get('person_bbox_xyxy'):continue
  expected='helmeted_head'if e.get('ppe_state')=='helmet_detected'else'no_helmet_head'if e.get('severity')=='WARNING'else None
  candidates=[h for h in e.get('head_candidates',[])if h['class']==expected]
  if not candidates:continue
  h=max(candidates,key=lambda h:h['confidence']);a,y,c,b=map(int,h['bbox_xyxy']);color=COLORS[e['severity']]
  label='HELMET'if e['severity']=='SAFE'else'NO HELMET? REVIEW'if e['severity']=='WARNING'else'HELMET? UNCONFIRMED'
  cv2.rectangle(frame,(a,y),(c,b),color,2);cv2.putText(frame,label,(a,max(120,y-5)),0,.43,color,1)
 e=select_proximity_display_event(groups.get('proximity',[]))
 if e:
  confirmed=e.get('observation_status')=='confirmed' and e.get('severity') in {'SAFE','WARNING','CRITICAL'}
  state=e['severity'] if confirmed else 'UNKNOWN / CHECK';color=COLORS[state if confirmed else 'WARNING']
  a=tuple(map(int,e['person_anchor_xy']));b=tuple(map(int,e['nearest_vehicle_point_xy']))
  cv2.line(frame,a,b,color,3);cv2.circle(frame,a,5,color,-1);cv2.circle(frame,b,5,color,-1)
  cv2.rectangle(frame,(5,73),(min(frame.shape[1]-5,770),101),(20,20,20),-1)
  cv2.putText(frame,f"GAP {e['image_gap_pixels']:.0f}px / PERSON HEIGHT = {e['normalized_image_gap']:.2f} | {state}",(12,93),0,.5,color,1)
