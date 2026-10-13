"""Image-plane proximity candidates, not calibrated collision prediction."""
import math


def closest_point(point,rect):
    x,y=point;a,b,c,d=rect
    return max(a,min(c,x)),max(b,min(d,y))


class Proximity:
    def __init__(self, warning_ratio=1.0, critical_ratio=.3, hysteresis=.1, max_gap=1.0, recent_pedestrian_overlap=False, distance_geometry="ground_band", exclude_probable_operator=False):
        if not all(math.isfinite(x) for x in [warning_ratio,critical_ratio,hysteresis,max_gap]) or not 0<=critical_ratio<warning_ratio or hysteresis<0 or max_gap<=0:
            raise ValueError('Invalid proximity thresholds')
        self.warning=warning_ratio;self.critical=critical_ratio;self.hysteresis=hysteresis;self.gap=max_gap
        self.previous={};self.last_timestamp=None;self.recent_pedestrian_overlap=recent_pedestrian_overlap
        if distance_geometry not in {"ground_band","box_boundary"}:raise ValueError("Unknown distance geometry")
        self.geometry=distance_geometry;self.exclude_operator=exclude_probable_operator;self.roles={}

    def reset(self):self.previous.clear();self.roles.clear();self.last_timestamp=None

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
                old=self.previous.get(key);reason=None;pedestrian_evidence=False
                pedestrian_seen=old.get('pedestrian_seen') if old else None
                margin=max(2.0,.02*(p[3]-p[1]))
                foot_outside=p[3]>f[3]+margin or (p[0]+p[2])/2<f[0]-margin or (p[0]+p[2])/2>f[2]+margin
                point=((p[0]+p[2])/2,p[3]);footprint=[f[0],f[3]-.15*(f[3]-f[1]),f[2],f[3]]
                nearest=closest_point(point,f if self.geometry=="box_boundary" else footprint);distance=math.dist(point,nearest);ratio=distance/(p[3]-p[1])
                if p[3]>=height-1:reason='person_anchor_bottom_clipped'
                elif f[0]<=0 or f[2]>=width-1 or f[3]>=height-1:reason='forklift_extent_clipped'
                else:
                    intersection=max(0,min(p[2],f[2])-max(p[0],f[0]))*max(0,min(p[3],f[3])-max(p[1],f[1]))
                    # High overlap cannot distinguish driver, occluded pedestrian, or a false person box.
                    # A foot near the bottom alone is insufficient; optional recent outside-vehicle evidence is required.
                    overlap=intersection/((p[2]-p[0])*(p[3]-p[1]))
                    if overlap<.8 and foot_outside:pedestrian_seen=timestamp
                    if overlap>=.8:
                        pedestrian_evidence=bool(self.recent_pedestrian_overlap and foot_outside and pedestrian_seen is not None and timestamp-pedestrian_seen<=self.gap)
                        if not pedestrian_evidence:reason='possible_operator_or_occluded_person'
                # Camera-local operator association uses current geometry and repeated observations.
                overlap_area=max(0,min(p[2],f[2])-max(p[0],f[0]))*max(0,min(p[3],f[3])-max(p[1],f[1]))
                overlap_fraction=overlap_area/((p[2]-p[0])*(p[3]-p[1]))
                role=self.roles.setdefault(key,{'inside_count':0,'pedestrian_seen':False,'last_seen':timestamp})
                if timestamp-role['last_seen']>self.gap:role['inside_count']=0
                if foot_outside and overlap_fraction<.8:role['pedestrian_seen']=True
                cabin_candidate=overlap_fraction>=.9 and p[3]<f[1]+.65*(f[3]-f[1]) and not role['pedestrian_seen']
                role['inside_count']=role['inside_count']+1 if cabin_candidate else 0;role['last_seen']=timestamp
                duplicate_operator=False
                if cabin_candidate:
                    for other_key,other in self.roles.items():
                        q=other.get('person_box')
                        if other_key==key or other_key[1]!=key[1] or other['inside_count']<3 or timestamp-other['last_seen']>self.gap or q is None:continue
                        inter=max(0,min(p[2],q[2])-max(p[0],q[0]))*max(0,min(p[3],q[3])-max(p[1],q[1]))
                        union=(p[2]-p[0])*(p[3]-p[1])+(q[2]-q[0])*(q[3]-q[1])-inter
                        if inter/max(1e-9,union)>=.3:duplicate_operator=True;break
                role['person_box']=list(p)
                operator=bool(self.exclude_operator and (role['inside_count']>=3 or duplicate_operator))
                if operator:self.previous.pop(key,None);continue
                if self.geometry=='box_boundary' and role['pedestrian_seen'] and overlap_fraction>=.8 and reason=='possible_operator_or_occluded_person':reason=None;pedestrian_evidence=True
                if person.get('observation_status')=='unconfirmed':reason='person_track_confirmation_pending'
                continuous=old is not None and old['severity'] is not None and timestamp-old['timestamp']<=self.gap
                trend=None
                if reason:severity=None
                else:
                    critical=self.critical+(self.hysteresis if continuous and old['severity']=='CRITICAL' else 0)
                    warning=self.warning+(self.hysteresis if continuous and old['severity'] in {'WARNING','CRITICAL'} else 0)
                    severity='CRITICAL' if ratio<=critical else 'WARNING' if ratio<=warning else 'SAFE'
                    if continuous:trend=(old['ratio']-ratio)/(timestamp-old['timestamp'])
                self.previous[key]={'timestamp':timestamp,'ratio':ratio,'severity':severity,'pedestrian_seen':pedestrian_seen}
                events.append({'event_type':'person_forklift_proximity','person_track_id':key[0],'forklift_track_id':key[1],
                    'timestamp_seconds':timestamp,'severity':severity,'observation_status':'unconfirmed' if reason else 'confirmed',
                    'reason':reason or 'image_plane_proximity_rule','recent_pedestrian_overlap_evidence':pedestrian_evidence,'person_bbox_xyxy':list(p),'forklift_bbox_xyxy':list(f),'person_anchor_xy':list(point),'forklift_ground_proxy_xyxy':footprint,
                    'nearest_vehicle_point_xy':list(nearest),'image_gap_pixels':distance,'normalized_image_gap':ratio,
                    'image_gap_closing_rate':trend,'orientation_status':'unknown','distance_meters':None,
                    'distance_geometry':self.geometry,'scope':'camera_image_plane_proximity_candidate'})
        for key,old in list(self.previous.items()):
            if key in current:continue
            events.append({'event_type':'person_forklift_proximity','person_track_id':key[0],'forklift_track_id':key[1],
                           'timestamp_seconds':timestamp,'severity':None,'observation_status':'unconfirmed',
                           'reason':'pair_not_observed','scope':'camera_image_plane_proximity_candidate',
                           'orientation_status':'unknown','distance_meters':None})
            if timestamp-old['timestamp']>self.gap:del self.previous[key]
            else:old['severity']=None
        return events
