"""Conditional pedestrian-lane severity using observed vehicle entry/exit evidence."""
import math
import cv2
import numpy as np

class LaneHazard:
    def __init__(self,polygon,hold_seconds=1.0, contains=None, policy="immediate", safe_seconds=3, critical_seconds=5):
        self.polygon=np.asarray(polygon,dtype=np.float32)
        if not math.isfinite(hold_seconds) or hold_seconds<=0:raise ValueError('Positive hold required')
        self.hold=hold_seconds;self.vehicles={};self.last=None;self.contains=contains;self.policy=policy;self.safe=safe_seconds;self.critical=critical_seconds
        if policy not in {"immediate","timed"} or not 0<=safe_seconds<critical_seconds:raise ValueError("Invalid lane policy")
    def reset(self):self.vehicles.clear();self.last=None
    def update(self,timestamp,events,forklifts,shape):
        if not math.isfinite(timestamp) or timestamp<0 or self.last is not None and timestamp<=self.last:raise ValueError('Increasing timestamps required')
        self.last=timestamp;h,w=shape;seen=set();ambiguous=[];present=[]
        for vehicle in forklifts:
            key=vehicle['track_id'];box=vehicle.get('detected_bbox_xyxy',vehicle['bbox_xyxy'])
            if key in seen or len(box)!=4 or not all(math.isfinite(x) for x in box) or box[2]<=box[0] or box[3]<=box[1]:raise ValueError('Invalid vehicle observation')
            seen.add(key)
            if box[0]<=0 or box[2]>=w-1 or box[3]>=h-1:
                ambiguous.append(key);continue
            anchor=((box[0]+box[2])/2,box[3]);inside=self.contains(anchor) if self.contains else cv2.pointPolygonTest(self.polygon,anchor,False)>=0
            self.vehicles[key]={'inside':inside,'last_seen':timestamp,'bbox':list(box),'anchor':list(anchor)}
            if inside:present.append(key)
        lost=[k for k,v in self.vehicles.items() if v['inside'] and k not in present]
        # An observed outside anchor is the only automatic release of that ID's prior occupancy.
        lost=[k for k in lost if k not in seen or k in ambiguous]
        held=[k for k in lost if timestamp-self.vehicles[k]['last_seen']<=self.hold]
        state='observed_in_lane' if present else 'recent_vehicle_missing_hold' if held else 'vehicle_observation_unknown' if lost or ambiguous else 'no_vehicle_detected_in_lane'
        evidence=[{'track_id':k,'last_seen_seconds':self.vehicles[k]['last_seen'],'bbox_xyxy':self.vehicles[k]['bbox'],'anchor_xy':self.vehicles[k]['anchor'],'age_seconds':timestamp-self.vehicles[k]['last_seen']} for k in present+lost]
        for event in events:
            inside=event['inside']
            if event['event_type']=='zone_dwell':event['dwell_time_band']=('SAFE' if event.get('observed_dwell_seconds',0)<self.safe else 'WARNING' if event.get('observed_dwell_seconds',0)<self.critical else 'CRITICAL') if self.policy=='timed' else event['severity']
            event.update(vehicle_lane_state=state,vehicle_observation_status='confirmed' if present else 'unconfirmed' if held or lost or ambiguous else 'not_detected',
                         vehicle_track_ids=present+lost,vehicle_evidence=evidence,lane_rule='pedestrian_inside_WARNING; observed_vehicle_CRITICAL; lost_vehicle_hold_then_UNKNOWN',
                         vehicle_absence_confirmed=False,rule_validation_status='development_image_anchor_rule')
            if inside is None or event['observation_status']!='confirmed':event['severity']=None
            elif not inside:event['severity']='SAFE';event['risk_reason']='person_outside_vehicle_lane'
            elif state in {'observed_in_lane','recent_vehicle_missing_hold'}:
                event['severity']='CRITICAL' if self.policy=='immediate' or event.get('observed_dwell_seconds',0)>=self.critical else 'WARNING';event['risk_reason']=state
            elif state=='vehicle_observation_unknown':event['severity']=None;event['observation_status']='unconfirmed';event['risk_reason']=state
            else:
                event['severity']='SAFE' if self.policy=='timed' and event.get('observed_dwell_seconds',0)<self.safe else 'WARNING';event['risk_reason']='person_in_lane_no_vehicle_detected'
            event['lane_rule']=self.policy
            # A person mostly within a vehicle may be its driver, not a pedestrian.
            if inside:
                p=event.get('person_bbox_xyxy')
                for vehicle in forklifts:
                    f=vehicle.get('detected_bbox_xyxy',vehicle['bbox_xyxy'])
                    overlap=max(0,min(p[2],f[2])-max(p[0],f[0]))*max(0,min(p[3],f[3])-max(p[1],f[1])) if p else 0
                    if p and overlap/((p[2]-p[0])*(p[3]-p[1]))>=.8:
                        event.update(severity=None,observation_status='unconfirmed',risk_reason='possible_vehicle_operator_or_occluded_person');break
        return {'state':state,'present_vehicle_ids':present,'missing_vehicle_ids':lost,'ambiguous_vehicle_ids':ambiguous}
