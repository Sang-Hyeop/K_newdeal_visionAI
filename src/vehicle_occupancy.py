"""관측된 탑승자 게이트와 차로 인식에 맞는 근접 표시를 제어한다."""
import cv2
import numpy as np

class VehicleOccupancy:
    def __init__(self, minimum_observations=3, max_gap=1.0):
        if minimum_observations < 1 or max_gap <= 0:
            raise ValueError('Positive occupancy confirmation requirements expected')
        self.minimum=minimum_observations;self.gap=max_gap;self.previous={}

    def reset(self):self.previous.clear()

    def update(self,timestamp,people,vehicles,associations):
        people_by_id={p['track_id']:p for p in people};result={};current={v['track_id'] for v in vehicles}
        for vehicle in vehicles:
            vid=vehicle['track_id']
            riders=sorted(pid for pid,owner in associations.items() if owner==vid and pid in people_by_id and people_by_id[pid].get('observation_status','confirmed')=='confirmed')
            old=self.previous.get(vid);same=old is not None and timestamp-old['timestamp']<=self.gap and bool(set(riders)&set(old['riders']))
            count=old['count']+1 if riders and same else 1 if riders else 0
            confirmed=count>=self.minimum
            self.previous[vid]={'timestamp':timestamp,'riders':riders,'count':count}
            result[vid]={'forklift_track_id':vid,'status':'occupied_observed' if confirmed else 'unconfirmed','rider_track_ids':riders,'consecutive_observations':count,'bbox_xyxy':vehicle.get('detected_bbox_xyxy',vehicle['bbox_xyxy']),'reason':'repeated_probable_rider_geometry' if confirmed else 'rider_confirmation_pending' if riders else 'no_current_rider_observation','absence_confirmed':False,'scope':'camera_local_visual_estimate_not_authorized_operator_identity'}
        self.previous={k:v for k,v in self.previous.items() if k in current}
        return result


def lane_membership(point,shape,config,roi_active=True):
    if not roi_active or point is None or point[1]>=shape[0]-1:return None
    h,w=shape
    def polygon(points):return np.asarray([[x*w,y*h]for x,y in points],np.float32)
    outer=config.get('monitor_floor_normalized')
    if not outer:return None
    return bool(cv2.pointPolygonTest(polygon(outer),tuple(point),False)>=0 and not any(cv2.pointPolygonTest(polygon(p),tuple(point),False)>=0 for p in config.get('safe_polygons_normalized',[])))


def gate_proximity(events,occupancy,shape,config,roi_active=True):
    """Retain uncertainty evidence; only occupied-camera pairs can produce distance alerts."""
    visible=[];suppressed=[]
    for original in events:
        e=dict(original);state=occupancy.get(e.get('forklift_track_id'),{'status':'unconfirmed','reason':'vehicle_not_currently_observed','rider_track_ids':[]})
        inside=lane_membership(e.get('person_anchor_xy'),shape,config,roi_active)
        e.update(vehicle_occupancy_status=state['status'],rider_track_ids=state['rider_track_ids'],person_in_monitored_lane=inside,zone_roi_used=True,distance_display_enabled=False,notification_enabled=False)
        if e.get('person_track_id')in state['rider_track_ids']:
            e['suppression_reason']='self_vehicle_rider';suppressed.append(e);continue
        if state['status']!='occupied_observed':
            e.update(severity=None,observation_status='unconfirmed',reason='vehicle_occupancy_unconfirmed',suppression_reason='requires_current_observed_rider')
            visible.append(e);continue
        confirmed=e.get('observation_status')=='confirmed'
        eligible=inside is True or (inside is False and confirmed and e.get('severity')=='CRITICAL')
        if not eligible:
            e['suppression_reason']='outside_lane_noncritical' if inside is False else 'lane_membership_unconfirmed'
            suppressed.append(e);continue
        e['distance_display_enabled']=confirmed;e['notification_enabled']=confirmed and e.get('severity')in {'WARNING','CRITICAL'}
        visible.append(e)
    return visible,suppressed
