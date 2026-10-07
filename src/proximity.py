"""Image-plane proximity candidates, not calibrated collision prediction."""
import math


def closest_point(point,rect):
    x,y=point;a,b,c,d=rect
    return max(a,min(c,x)),max(b,min(d,y))


class Proximity:
    def __init__(self, warning_ratio=1.0, critical_ratio=.3, hysteresis=.1, max_gap=1.0):
        if not all(math.isfinite(x) for x in [warning_ratio,critical_ratio,hysteresis,max_gap]) or not 0<=critical_ratio<warning_ratio or hysteresis<0 or max_gap<=0:
            raise ValueError('Invalid proximity thresholds')
        self.warning=warning_ratio;self.critical=critical_ratio;self.hysteresis=hysteresis;self.gap=max_gap
        self.previous={};self.last_timestamp=None

    def reset(self):self.previous.clear();self.last_timestamp=None

    def update(self,timestamp,people,forklifts,shape):
        if not math.isfinite(timestamp) or timestamp<0 or (self.last_timestamp is not None and timestamp<=self.last_timestamp):
            raise ValueError('Timestamps must strictly increase')
        self.last_timestamp=timestamp;events=[];current=set();height,width=shape
        for group in [people,forklifts]:
            if len({t['track_id'] for t in group})!=len(group):raise ValueError('Duplicate track ID')
        for person in people:
            for forklift in forklifts:
                key=(person['track_id'],forklift['track_id']);current.add(key)
                p=person.get('detected_bbox_xyxy',person['bbox_xyxy']);f=forklift.get('detected_bbox_xyxy',forklift['bbox_xyxy'])
                if len(p)!=4 or len(f)!=4 or not all(math.isfinite(x) for x in [*p,*f]) or p[2]<=p[0] or p[3]<=p[1] or f[2]<=f[0] or f[3]<=f[1]:raise ValueError('Invalid box')
                old=self.previous.get(key);reason=None
                point=((p[0]+p[2])/2,p[3]);footprint=[f[0],f[3]-.15*(f[3]-f[1]),f[2],f[3]]
                nearest=closest_point(point,footprint);distance=math.dist(point,nearest);ratio=distance/(p[3]-p[1])
                if p[3]>=height-1:reason='person_anchor_bottom_clipped'
                elif f[0]<=0 or f[2]>=width-1 or f[3]>=height-1:reason='forklift_extent_clipped'
                else:
                    intersection=max(0,min(p[2],f[2])-max(p[0],f[0]))*max(0,min(p[3],f[3])-max(p[1],f[1]))
                    # High overlap cannot distinguish driver, occluded pedestrian, or a false person box.
                    # A foot at the vehicle bottom must not turn this ambiguity into CRITICAL.
                    if intersection/((p[2]-p[0])*(p[3]-p[1]))>=.8:
                        reason='possible_operator_or_occluded_person'
                continuous=old is not None and old['severity'] is not None and timestamp-old['timestamp']<=self.gap
                trend=None
                if reason:severity=None
                else:
                    critical=self.critical+(self.hysteresis if continuous and old['severity']=='CRITICAL' else 0)
                    warning=self.warning+(self.hysteresis if continuous and old['severity'] in {'WARNING','CRITICAL'} else 0)
                    severity='CRITICAL' if ratio<=critical else 'WARNING' if ratio<=warning else 'SAFE'
                    if continuous:trend=(old['ratio']-ratio)/(timestamp-old['timestamp'])
                self.previous[key]={'timestamp':timestamp,'ratio':ratio,'severity':severity}
                events.append({'event_type':'person_forklift_proximity','person_track_id':key[0],'forklift_track_id':key[1],
                    'timestamp_seconds':timestamp,'severity':severity,'observation_status':'unconfirmed' if reason else 'confirmed',
                    'reason':reason or 'image_plane_proximity_rule','person_bbox_xyxy':list(p),'forklift_bbox_xyxy':list(f),'person_anchor_xy':list(point),'forklift_ground_proxy_xyxy':footprint,
                    'nearest_vehicle_point_xy':list(nearest),'image_gap_pixels':distance,'normalized_image_gap':ratio,
                    'image_gap_closing_rate':trend,'orientation_status':'unknown','distance_meters':None,
                    'scope':'camera_image_plane_proximity_candidate'})
        for key,old in list(self.previous.items()):
            if key in current:continue
            events.append({'event_type':'person_forklift_proximity','person_track_id':key[0],'forklift_track_id':key[1],
                           'timestamp_seconds':timestamp,'severity':None,'observation_status':'unconfirmed',
                           'reason':'pair_not_observed','scope':'camera_image_plane_proximity_candidate',
                           'orientation_status':'unknown','distance_meters':None})
            if timestamp-old['timestamp']>self.gap:del self.previous[key]
            else:old['severity']=None
        return events
