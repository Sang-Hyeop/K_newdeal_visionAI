"""Observed ROI approach/occupancy; authorization cannot be inferred from video."""
import math
import cv2
import numpy as np


class ZoneAccess:
    def __init__(self, polygon, approach_pixels, max_gap_seconds=1):
        self.polygon=np.asarray(polygon,dtype=np.float32)
        if self.polygon.ndim!=2 or self.polygon.shape[1]!=2 or len(self.polygon)<3 or not np.isfinite(self.polygon).all() or abs(cv2.contourArea(self.polygon))<=0:
            raise ValueError('Invalid ROI')
        if not math.isfinite(approach_pixels) or approach_pixels<=0 or max_gap_seconds<=0:
            raise ValueError('Positive approach margin and gap required')
        self.margin=approach_pixels;self.gap=max_gap_seconds;self.previous={};self.last_timestamp=None

    def reset(self):
        self.previous.clear();self.last_timestamp=None

    def update(self,timestamp,tracks):
        if not math.isfinite(timestamp) or timestamp<0 or (self.last_timestamp is not None and timestamp<=self.last_timestamp):
            raise ValueError('Timestamps must strictly increase')
        prepared={}
        for track in tracks:
            identity=track['track_id'];box=track['bbox_xyxy']
            if identity in prepared or len(box)!=4 or not all(math.isfinite(x) for x in box) or box[2]<=box[0] or box[3]<=box[1]:
                raise ValueError('Invalid track')
            prepared[identity]=((box[0]+box[2])/2,box[3])
        self.last_timestamp=timestamp;events=[]
        for identity,point in prepared.items():
            distance=float(cv2.pointPolygonTest(self.polygon,point,True))
            inside=distance>=0
            region='inside' if inside else 'approach' if distance>=-self.margin else 'outside'
            severity={'inside':'CRITICAL','approach':'WARNING','outside':'SAFE'}[region]
            old=self.previous.get(identity)
            continuous=old is not None and old['confirmed'] and timestamp-old['last_seen']<=self.gap
            entered=continuous and old['region']!='inside' and inside
            exited=continuous and old['region']=='inside' and not inside
            self.previous[identity]={'region':region,'confirmed':True,'last_seen':timestamp}
            events.append({'event_type':'zone_access','track_id':identity,'timestamp_seconds':timestamp,
                           'severity':severity,'observation_status':'confirmed','inside':inside,'region':region,
                           'signed_distance_pixels':distance,'approach_margin_pixels':self.margin,
                           'entry_observed':bool(entered),'exit_observed':bool(exited),
                           'authorization_status':'not_assessed','anchor_xy':list(point)})
        for identity,old in list(self.previous.items()):
            if identity in prepared:continue
            old['confirmed']=False
            events.append({'event_type':'zone_access','track_id':identity,'timestamp_seconds':timestamp,
                           'severity':None,'observation_status':'unconfirmed','inside':None,'region':'unknown',
                           'signed_distance_pixels':None,'approach_margin_pixels':self.margin,
                           'entry_observed':False,'exit_observed':False,'authorization_status':'not_assessed',
                           'anchor_xy':None})
            if timestamp-old['last_seen']>self.gap:del self.previous[identity]
        return events
