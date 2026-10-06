"""Conservative dwell state for externally tracked people; no detector/tracker here."""
from dataclasses import dataclass
import math
import cv2
import numpy as np

@dataclass
class Visit:
    elapsed: float = 0.0
    last_seen: float = 0.0
    observed_previous: bool = True

class ZoneDwell:
    def __init__(self, polygon, safe_seconds=3.0, critical_seconds=8.0, max_gap_seconds=1.0):
        self.polygon=np.asarray(polygon,dtype=np.float32)
        if self.polygon.ndim!=2 or self.polygon.shape[1]!=2 or len(self.polygon)<3 or not np.isfinite(self.polygon).all():
            raise ValueError('ROI requires at least three finite XY points')
        if abs(cv2.contourArea(self.polygon))<=0:
            raise ValueError('ROI must have nonzero area')
        if not 0<=safe_seconds<critical_seconds or max_gap_seconds<=0:
            raise ValueError('Invalid time thresholds')
        self.safe=safe_seconds;self.critical=critical_seconds;self.max_gap=max_gap_seconds
        self.visits={};self.last_timestamp=None

    def reset(self):
        """Call on scene cut, ROI change or tracking identity reset."""
        self.visits.clear();self.last_timestamp=None

    def update(self, timestamp, tracks):
        """tracks: [{track_id, bbox_xyxy}]; timestamps are source video seconds.

        Footpoint (bottom-center) inside/on polygon means inside. Unobserved time
        is not counted. Short gaps retain accumulated observed time but emit
        unknown; long gaps discard the old visit. IDs must be supplied by tracker.
        """
        if not math.isfinite(timestamp) or timestamp<0 or (self.last_timestamp is not None and timestamp<=self.last_timestamp):
            raise ValueError('Video timestamps must strictly increase')
        prepared={}
        for track in tracks:
            key=track['track_id'];box=track['bbox_xyxy']
            if key in prepared or len(box)!=4 or not all(math.isfinite(v) for v in box):
                raise ValueError('Duplicate ID or invalid box')
            x1,y1,x2,y2=box
            if x2<=x1 or y2<=y1:raise ValueError('Invalid box dimensions')
            prepared[key]=((x1+x2)/2,y2)
        self.last_timestamp=timestamp;result=[]
        for key,point in prepared.items():
            inside=cv2.pointPolygonTest(self.polygon,point,False)>=0
            if inside:
                visit=self.visits.get(key)
                if visit is None or timestamp-visit.last_seen>self.max_gap:
                    visit=Visit(last_seen=timestamp);self.visits[key]=visit
                elif visit.observed_previous:
                    visit.elapsed+=timestamp-visit.last_seen
                visit.last_seen=timestamp;visit.observed_previous=True
                severity='SAFE' if visit.elapsed<=self.safe else 'WARNING' if visit.elapsed<self.critical else 'CRITICAL'
                elapsed=visit.elapsed
            else:
                self.visits.pop(key,None);severity='SAFE';elapsed=0.0
            result.append({'track_id':key,'event_type':'zone_dwell','severity':severity,
                           'observation_status':'confirmed','inside':inside,
                           'observed_dwell_seconds':elapsed,'timestamp_seconds':timestamp})
        for key,visit in list(self.visits.items()):
            if key in prepared:continue
            visit.observed_previous=False
            result.append({'track_id':key,'event_type':'zone_dwell','severity':None,
                           'observation_status':'unconfirmed','inside':None,
                           'observed_dwell_seconds':visit.elapsed,'timestamp_seconds':timestamp})
            if timestamp-visit.last_seen>self.max_gap:del self.visits[key]
        return result
