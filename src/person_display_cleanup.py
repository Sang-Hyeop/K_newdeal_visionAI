"""같은 사람으로 보이는 중복 박스를 정리하고 리뷰용 사람 박스를 그린다."""
import cv2
from .ppe_tiled_inference import iou

def deduplicate_people(people,prefer_source=None,minimum_coverage=.85,center_tolerance=.35,foot_tolerance=.15):
    kept=[];rejected=[]
    for d in sorted(people,key=lambda q:(q.get('model_source')!=prefer_source,-q['confidence'])):
        a=d['bbox_xyxy'];duplicate=False
        for other in kept:
            b=other['bbox_xyxy']
            if not d.get('model_source') or not other.get('model_source') or d['model_source']==other['model_source']:continue
            inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
            area=min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1]))
            maxw=max(a[2]-a[0],b[2]-b[0]);maxh=max(a[3]-a[1],b[3]-b[1])
            if inter/max(area,1)>=minimum_coverage and abs((a[0]+a[2]-b[0]-b[2])/2)<=center_tolerance*maxw and abs(a[3]-b[3])<=foot_tolerance*maxh:
                duplicate=True;break
        if duplicate:rejected.append({**d,'review_reason':'cross_model_same_person_containment_and_footpoint','duplicate_of_bbox_xyxy':other['bbox_xyxy']})
        else:kept.append(d)
    return kept,rejected

def _match(box,events):
    matches=[e for e in events if e.get('person_bbox_xyxy') and iou(box,e['person_bbox_xyxy'])>=.5]
    return max(matches,key=lambda e:iou(box,e['person_bbox_xyxy'])) if matches else None

def person_labels(d,groups):
    zone=_match(d['bbox_xyxy'],groups.get('zone_dwell',[]));ppe=_match(d['bbox_xyxy'],groups.get('ppe',[]))
    labels=[f"PERSON {d['confidence']:.2f}"];severity=None
    if zone:
        if zone.get('observation_status')=='confirmed':
            labels.append(('LANE IN' if zone.get('inside') else 'LANE OUT')+f" {zone.get('observed_dwell_seconds',0):.1f}s / {zone.get('severity') or 'CHECK'}")
            severity=zone.get('severity')
        else:labels.append('LANE: CHECK')
    else:labels.append('LANE: PENDING')
    if ppe:
        stable=ppe.get('observation_status')=='confirmed'
        status='HELMET' if stable and ppe.get('severity')=='SAFE' else 'NO HELMET DETECTED' if stable and ppe.get('severity')=='WARNING' and ppe.get('classification_status')=='observed_candidate' else 'NO HELMET? REVIEW' if ppe.get('severity')=='WARNING' else 'PENDING' if ppe.get('reason')=='pending_temporal_confirmation' else 'CHECK'
        labels.append('PPE: '+status)
        if stable and ppe.get('severity')=='WARNING' and severity!='CRITICAL':severity='WARNING'
    elif 'ppe' in groups:labels.append('PPE: PENDING')
    return labels,severity

def draw_compact_people(frame,detections,groups):
    colors={'SAFE':(0,180,0),'WARNING':(0,140,255),'CRITICAL':(0,0,255),None:(255,170,0)}
    for d in detections:
        if d['class']!='person':continue
        labels,severity=person_labels(d,groups);color=colors[severity];x,y,xx,yy=map(int,d['bbox_xyxy']);cv2.rectangle(frame,(x,y),(xx,yy),color,2)
        # A short label panel beside the body avoids drawing head/zone boxes again.
        label_x=max(0,min(x,frame.shape[1]-320));label_y=max(110,min(y,frame.shape[0]-55))
        for i,label in enumerate(labels):
            ty=label_y+15*i;cv2.putText(frame,label,(label_x+2,ty),0,.38,(0,0,0),3);cv2.putText(frame,label,(label_x+2,ty),0,.38,color,1)
    return frame
