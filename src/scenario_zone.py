"""Camera 7: monitored floor minus reviewed safe polygons, with timed lane policy."""
import cv2,numpy as np
from src.person_tracker import PersonTracker
from src.zone_dwell import ZoneDwell
from src.lane_hazard import LaneHazard
def mark_uncertain_lane_events(events):
 for e in events:
  if e.get('inside') is True and e.get('vehicle_observation_status')=='unconfirmed' and e.get('severity') is not None:
   e.update(last_risk_severity=e['severity'],severity=None,observation_status='unconfirmed')
 return events
class ScenarioZone:
 def __init__(self,config,shape,fps):
  self.config=config;h,w=shape
  def polygon(points):
   if len(points)<3 or any(len(p)!=2 or not all(0<=v<=1 for v in p)for p in points):raise ValueError('Invalid normalized ROI')
   result=np.array([[x*w,y*h]for x,y in points],np.float32)
   if abs(cv2.contourArea(result))<=0:raise ValueError('Empty ROI')
   return result
  self.polygon=polygon(config['monitor_floor_normalized']);self.safe_polygons=[polygon(p)for p in config['safe_polygons_normalized']]
  self.contains=lambda point:cv2.pointPolygonTest(self.polygon,point,False)>=0 and not any(cv2.pointPolygonTest(p,point,False)>=0 for p in self.safe_polygons)
  self.people=PersonTracker(fps,config['max_gap_seconds'],namespace='ZP');self.vehicles=PersonTracker(fps,config['max_gap_seconds'],target_class='forklift',namespace='ZF');self.dwell=ZoneDwell(self.polygon,config['safe_seconds'],config['critical_seconds'],config['max_gap_seconds'],contains=self.contains);self.lane=LaneHazard(self.polygon,config['vehicle_missing_hold_seconds'],contains=self.contains,policy='timed',safe_seconds=config['safe_seconds'],critical_seconds=config['critical_seconds']);self.previous={};self.roi_active=True
 def update(self,timestamp,detections,shape,scene_cut=False):
  scene=self.people.scene;people,missing=self.people.update(timestamp,detections,shape,scene_cut);vehicles,vm=self.vehicles.update(timestamp,detections,shape,scene_cut)
  if self.people.scene!=scene:self.dwell.reset();self.previous.clear()
  if scene_cut:self.roi_active=False;self.lane.reset()
  boxes={t['track_id']:t['detected_bbox_xyxy']for t in people};valid=[{**t,'bbox_xyxy':t['detected_bbox_xyxy']}for t in people if t['detected_bbox_xyxy'][3]<shape[0]-1];events=self.dwell.update(timestamp,valid)if self.roi_active else[]
  for e in events:
   if e['track_id']in boxes and e['observation_status']=='confirmed':
    e['person_bbox_xyxy']=boxes[e['track_id']];b=boxes[e['track_id']];point=((b[0]+b[2])/2,b[3])
    if cv2.pointPolygonTest(self.polygon,point,False)<0:e.update(inside=None,severity=None,observation_status='unconfirmed',risk_reason='outside_monitored_floor')
  state=self.lane.update(timestamp,events,vehicles,shape)if self.roi_active else None;access=[];transitions=[]
  for e in mark_uncertain_lane_events(events):
   old=self.previous.get(e['track_id']);inside=e['inside'];entry=bool(old and old['inside']is False and inside is True);exit=bool(old and old['inside']is True and inside is False)
   e.update(camera_id=self.config['camera_id'],roi_id=self.config['roi_id'],roi_purpose='floor_minus_safe_storage_zones',distance_meters=None,
            roi_polygon_normalized=self.config.get('monitor_floor_normalized'),safe_polygons_normalized=self.config.get('safe_polygons_normalized'),
            roi_alpha_safe=self.config.get('roi_alpha_safe',.15),roi_alpha_alert=self.config.get('roi_alpha_alert',.2))
   a={**e,'event_type':'zone_access','entry_observed':entry,'exit_observed':exit,'authorization_status':'not_assessed'};access.append(a)
   key=(e['severity'],e['observation_status'],inside,e.get('vehicle_lane_state'))
   if old is None or old['key']!=key:transitions.extend([e.copy(),a.copy()])
   self.previous[e['track_id']]={'key':key,'inside':inside}
  self.previous={k:v for k,v in self.previous.items()if k in {e['track_id']for e in events}}
  return {'timestamp_seconds':timestamp,'scene_id':self.people.scene,'tracks':people,'missing_tracks':missing,'forklifts':vehicles,'missing_forklifts':vm,'events':events+access,'transitions':transitions,'roi_active':self.roi_active,'vehicle_lane_state':state,'global_safety_status':'not_evaluated'}
