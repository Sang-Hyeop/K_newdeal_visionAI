"""Independent feature banners and faint configured ROI fills."""
import cv2,numpy as np
from src.feature_status import feature_status
COLORS={'SAFE':(0,180,0),'WARNING':(0,140,255),'CRITICAL':(0,0,255),None:(150,150,150)}
def roi_overlay(frame,polygon,safe_polygons,severity,active=True,alpha_safe=.15,alpha_alert=.2):
 mask=np.zeros(frame.shape[:2],np.uint8);cv2.fillPoly(mask,[np.asarray(polygon,np.int32)],255)
 for p in safe_polygons:cv2.fillPoly(mask,[np.asarray(p,np.int32)],0)
 if not active:severity=None
 layer=frame.copy();layer[mask>0]=COLORS[severity];alpha=alpha_alert if severity in {'WARNING','CRITICAL'} else alpha_safe;frame[:]=cv2.addWeighted(layer,alpha,frame,1-alpha,0)
 # Excluded storage/walking regions are not the monitored lane or a safety verdict.
 cv2.polylines(frame,[np.asarray(polygon,np.int32)],True,COLORS[severity],2)
 for p in safe_polygons:cv2.polylines(frame,[np.asarray(p,np.int32)],True,COLORS[None],1)
 return frame

def render(frame,groups,zone=None,detections=None,proximity_warning_ratio=1.6,driver_overlap_threshold=.8):
 if detections is not None and 'proximity' in groups:
  groups={**groups,'proximity':exclude_driver_overlap_pairs(groups['proximity'],driver_overlap_threshold)}
 if zone:
  pipeline,row=zone;cfg=getattr(pipeline,'config',{})
  roi_overlay(frame,pipeline.polygon,getattr(pipeline,'safe_polygons',[]),feature_status(row['events'])['severity'],row['roi_active'],cfg.get('roi_alpha_safe',.15),cfg.get('roi_alpha_alert',.2))
 if detections is not None:
  draw_review_objects(frame,detections,groups,proximity_warning_ratio,driver_overlap_threshold)
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
    if feature in {'zone_access','zone_dwell'}:label='LANE '+label
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


def select_proximity_display_events(events,warning_ratio=1.6,driver_overlap_threshold=.8):
 """Select observed pairs except people mostly inside a forklift box.

 The overlap rule is a demo-view exclusion heuristic, not proof that the person
 is the operator. Safe pairs are only a per-person fallback without alerts.
 """
 pairs=[e for e in events if e.get('person_anchor_xy') and e.get('nearest_vehicle_point_xy') and e.get('normalized_image_gap') is not None]
 pairs=[e for e in pairs if _person_vehicle_overlap(e)<driver_overlap_threshold]
 alerts=[e for e in pairs if e.get('observation_status')=='confirmed' and e.get('severity') in {'WARNING','CRITICAL'}]
 uncertain=[e for e in pairs if e.get('observation_status')!='confirmed' and e['normalized_image_gap']<=warning_ratio]
 if alerts or uncertain:
  return alerts+uncertain
 safe=[e for e in pairs if e.get('observation_status')=='confirmed' and e.get('severity')=='SAFE']
 selected=[]
 for person_id in dict.fromkeys(e.get('person_track_id') for e in safe):
  per_person=[e for e in safe if e.get('person_track_id')==person_id]
  if per_person:selected.append(min(per_person,key=lambda e:e['normalized_image_gap']))
 return selected


def _person_vehicle_overlap(event):
 person=event.get('person_bbox_xyxy');vehicle=event.get('forklift_bbox_xyxy')
 if not person or not vehicle:return 0.0
 x1=max(person[0],vehicle[0]);y1=max(person[1],vehicle[1]);x2=min(person[2],vehicle[2]);y2=min(person[3],vehicle[3])
 intersection=max(0,x2-x1)*max(0,y2-y1);area=max(1e-9,(person[2]-person[0])*(person[3]-person[1]))
 return intersection/area


def exclude_driver_overlap_pairs(events,threshold=.8):
 """Exclude person/forklift pairs likely to be the seated operator in this demo."""
 return [event for event in events if _person_vehicle_overlap(event)<threshold]


def _box_iou(a,b):
 x1=max(a[0],b[0]);y1=max(a[1],b[1]);x2=min(a[2],b[2]);y2=min(a[3],b[3])
 inter=max(0,x2-x1)*max(0,y2-y1);area_a=max(0,a[2]-a[0])*max(0,a[3]-a[1]);area_b=max(0,b[2]-b[0])*max(0,b[3]-b[1])
 return inter/max(1e-9,area_a+area_b-inter)


def select_ppe_review_candidates(events,iou_threshold=.5):
 """Deduplicate repeated model/tile proposals while preserving class conflicts."""
 selected=[]
 for event in events:
  candidates=sorted(event.get('head_candidates',[]),key=lambda h:h.get('confidence',0),reverse=True)
  kept=[]
  for candidate in candidates:
   if candidate.get('class') not in {'helmeted_head','no_helmet_head'}:continue
   if any(candidate['class']==prior['class'] and _box_iou(candidate['bbox_xyxy'],prior['bbox_xyxy'])>=iou_threshold for prior in kept):continue
   kept.append(candidate)
  selected.extend((event,candidate) for candidate in kept)
 return selected


def draw_review_objects(frame,detections,groups,warning_ratio=1.6,driver_overlap_threshold=.8):
 """Draw each observed object once; unassociated head proposals stay in diagnostics."""
 for d in detections:
  if d['confidence']<.1:continue
  a,y,c,b=map(int,d['bbox_xyxy']);low_person=d['class']=='person'and d['confidence']<.25;color=(0,165,255)if low_person else(255,170,0)if d['class']=='person'else(0,210,255)
  cv2.rectangle(frame,(a,y),(c,b),color,2)
  label=f"LOW PERSON {d['confidence']:.2f}"if low_person else f"{d['class'].upper()} {d['confidence']:.2f}"
  cv2.putText(frame,label,(a,max(105,y-5)),0,.45,color,1)
 for e in groups.get('ppe',[]):
  candidates=e.get('head_candidates',[])
  if not e.get('person_bbox_xyxy'):continue
  x,y,_,_=map(int,e['person_bbox_xyxy']);status=None
  if e.get('severity')=='SAFE' and e.get('observation_status')=='confirmed':status='PPE OK';status_color=COLORS['SAFE']
  elif e.get('severity')=='WARNING' and not candidates:status='PPE REVIEW';status_color=COLORS['WARNING']
  elif e.get('ppe_state')=='conflicting_evidence' and not candidates:status='PPE CONFLICT';status_color=COLORS['WARNING']
  elif not candidates:status='PPE UNKNOWN';status_color=COLORS[None]
  if status:cv2.putText(frame,status,(x+2,min(frame.shape[0]-8,y+18)),0,.38,status_color,1)
 for e,h in select_ppe_review_candidates(groups.get('ppe',[])):
  a,y,c,b=map(int,h['bbox_xyxy']);helmet=h['class']=='helmeted_head';confirmed=e.get('observation_status')=='confirmed' and e.get('severity')=='SAFE' and helmet
  color=COLORS['SAFE']if confirmed else(255,180,0)if helmet else(0,165,255)
  label=('H'if confirmed else'H?'if helmet else'NH?')+f" {h['confidence']:.2f}"
  cv2.rectangle(frame,(a,y),(c,b),color,2);cv2.putText(frame,label,(a,max(120,y-5)),0,.4,color,1)
 display_events=select_proximity_display_events(groups.get('proximity',[]),warning_ratio,driver_overlap_threshold)
 legend_y=frame.shape[0]-100
 for e in display_events:
  confirmed=e.get('observation_status')=='confirmed' and e.get('severity') in {'SAFE','WARNING','CRITICAL'}
  state=e['severity'] if confirmed else 'UNKNOWN / CHECK';color=COLORS[state if confirmed else 'WARNING']
  a=tuple(map(int,e['person_anchor_xy']));b=tuple(map(int,e['nearest_vehicle_point_xy']))
  cv2.line(frame,a,b,color,3);cv2.circle(frame,a,5,color,-1);cv2.circle(frame,b,5,color,-1)
  if len(display_events)<=3:
   mark=('CRIT'if e['severity']=='CRITICAL'else'WARN'if e['severity']=='WARNING'else'SAFE')if confirmed else'CHECK'
   person=e.get('person_track_id','?');vehicle=e.get('forklift_track_id','?')
   label=f"P{person} -> F{vehicle}  {mark}  gap {e['normalized_image_gap']:.2f}"
   y=legend_y+22*display_events.index(e)
   cv2.rectangle(frame,(7,y-15),(min(frame.shape[1]-7,410),y+5),(20,20,20),-1)
   cv2.putText(frame,label,(12,y),0,.45,color,1)
 if len(display_events)>3:
  cv2.rectangle(frame,(7,legend_y-15),(min(frame.shape[1]-7,410),legend_y+5),(20,20,20),-1)
  cv2.putText(frame,f"{len(display_events)} person-forklift pairs shown; details in event log",(12,legend_y),0,.43,(0,165,255),1)
