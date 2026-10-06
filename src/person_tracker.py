"""ByteTrack adapter with source-time gap handling and scene-scoped identities."""
from types import SimpleNamespace
import math
import itertools
import numpy as np
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker, STrack


class PersonTracker:
    def __init__(self, processed_fps, max_gap_seconds=1.0, target_class='person', namespace=''):
        if processed_fps <= 0 or max_gap_seconds <= 0:
            raise ValueError('Positive FPS and gap required')
        self.gap = max_gap_seconds
        self.target_class=target_class;self.namespace=namespace
        self._counter=itertools.count(1)
        self.backend = BYTETracker(SimpleNamespace(track_high_thresh=.25,
            track_low_thresh=.1, new_track_thresh=.25,
            track_buffer=max(1, math.ceil(processed_fps*max_gap_seconds)),
            match_thresh=.8, fuse_score=True))
        # Independent counters prevent one class's reset reusing another class's ID.
        self.backend.track_class=type('LocalSTrack',(STrack,),
            {'next_id':staticmethod(lambda:next(self._counter))})
        self.scene = 0
        self.last_timestamp = None
        self.last_seen = {}

    def reset(self):
        self.backend.reset()
        self._counter=itertools.count(1)
        self.scene += 1
        self.last_seen.clear()

    def update(self, timestamp, detections, shape, scene_cut=False):
        if not math.isfinite(timestamp) or timestamp < 0 or (
                self.last_timestamp is not None and timestamp <= self.last_timestamp):
            raise ValueError('Source timestamps must strictly increase')
        if scene_cut or (self.last_timestamp is not None and timestamp-self.last_timestamp>self.gap):
            self.reset()
        self.last_timestamp=timestamp
        rows=[]
        for detection in detections:
            if detection['class']!=self.target_class:
                continue
            box=detection['bbox_xyxy'];score=detection['confidence']
            if len(box)!=4 or not all(math.isfinite(v) for v in box) or not 0 <= score <= 1:
                raise ValueError('Invalid detection')
            if box[2]<=box[0] or box[3]<=box[1]:
                raise ValueError('Invalid detection dimensions')
            rows.append([*box,score,0])
        boxes=Boxes(np.asarray(rows,dtype=np.float32).reshape(-1,6),shape)
        tracks=self.backend.update(boxes)
        observed=[]
        for track in tracks:
            identity=f'{self.namespace}{self.scene}:{int(track[4])}'
            self.last_seen[identity]=timestamp
            observed.append({'track_id':identity,'bbox_xyxy':track[:4].tolist(),
                             'detected_bbox_xyxy':rows[int(track[-1])][:4],
                             'confidence':float(track[5]),'observation_status':'confirmed'})
        observed_ids={row['track_id'] for row in observed}
        missing=[]
        for identity,last_seen in list(self.last_seen.items()):
            if identity in observed_ids:
                continue
            missing.append({'track_id':identity,'observation_status':'unconfirmed',
                            'ppe_state':'unknown','gap_seconds':timestamp-last_seen})
            if timestamp-last_seen>self.gap:
                del self.last_seen[identity]
        return observed, missing
