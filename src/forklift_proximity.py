"""Symmetric observed forklift footprint distance; uncalibrated, no orientation claim."""
import math,itertools

def _area(box):return max(0,box[2]-box[0])*max(0,box[3]-box[1])
def _intersection(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
def unreliable_vehicle_pair(p,q,iou_threshold=.5,containment_threshold=.8):
 """Merged/duplicate boxes make image-plane gaps untrustworthy."""
 inter=_intersection(p,q);union=_area(p)+_area(q)-inter
 if union<=0:return True
 if inter/union>=iou_threshold:return True
 smaller=min(_area(p),_area(q))
 return smaller>0 and inter/smaller>=containment_threshold

class ForkliftProximity:
 def __init__(self,warning=1,critical=.15,hysteresis=.1,gap=1):
  if not all(math.isfinite(x)for x in[warning,critical,hysteresis,gap])or not 0<=critical<warning or hysteresis<0 or gap<=0:raise ValueError('Invalid pair thresholds')
  self.warning=warning;self.critical=critical;self.hysteresis=hysteresis;self.gap=gap;self.previous={};self.last=None
 def reset(self):self.previous.clear();self.last=None
 def update(self,timestamp,vehicles,shape):
  if not math.isfinite(timestamp)or timestamp<0 or self.last is not None and timestamp<=self.last:raise ValueError('Increasing source time required')
  self.last=timestamp;events=[];seen=set();h,w=shape
  if len({v['track_id']for v in vehicles})!=len(vehicles):raise ValueError('Duplicate vehicle IDs')
  for a,b in itertools.combinations(sorted(vehicles,key=lambda v:v['track_id']),2):
   key=(a['track_id'],b['track_id']);seen.add(key);p=a.get('detected_bbox_xyxy',a['bbox_xyxy']);q=b.get('detected_bbox_xyxy',b['bbox_xyxy'])
   if any(len(v)!=4 or not all(math.isfinite(x)for x in v)or v[2]<=v[0]or v[3]<=v[1]for v in[p,q]):raise ValueError('Invalid vehicle bbox')
   foot=lambda v:[v[0],v[3]-.15*(v[3]-v[1]),v[2],v[3]]
   x,y=foot(p),foot(q);distance=math.hypot(max(0,x[0]-y[2],y[0]-x[2]),max(0,x[1]-y[3],y[1]-x[3]));ratio=distance/min(p[3]-p[1],q[3]-q[1]);old=self.previous.get(key);continuous=old and old['severity']and timestamp-old['time']<=self.gap;clipped=any(v[0]<=0 or v[2]>=w-1 or v[3]>=h-1 for v in[p,q]);merged=unreliable_vehicle_pair(p,q)
   if clipped or merged:severity=None;reason='forklift_extent_clipped'if clipped else'merged_or_duplicate_vehicle_boxes'
   else:
    severity='CRITICAL'if ratio<=self.critical+(self.hysteresis if continuous and old['severity']=='CRITICAL'else 0)else'WARNING'if ratio<=self.warning+(self.hysteresis if continuous and old['severity']in['WARNING','CRITICAL']else 0)else'SAFE';reason='image_plane_vehicle_pair_rule'
   self.previous[key]={'time':timestamp,'severity':severity}
   events.append({'event_type':'forklift_forklift_proximity','timestamp_seconds':timestamp,'forklift_track_ids':list(key),'severity':severity,'observation_status':'unconfirmed'if clipped or merged else'confirmed','reason':reason,'forklift_bboxes_xyxy':[p,q],'image_gap_pixels':distance,'normalized_image_gap':ratio,'distance_meters':None,'orientation_status':'unknown','zone_roi_used':False,'scope':'observed_vehicle_pair_image_distance_only'})
  for key,v in list(self.previous.items()):
   if key in seen:continue
   events.append({'event_type':'forklift_forklift_proximity','timestamp_seconds':timestamp,'forklift_track_ids':list(key),'severity':None,'observation_status':'unconfirmed','reason':'pair_not_observed','distance_meters':None})
   if timestamp-v['time']>self.gap:del self.previous[key]
   else:v['severity']=None
  return events
