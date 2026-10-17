"""Current-image fire recovery and spatial/temporal suspicion; never infer SAFE."""
import math
from collections import deque


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2-x1) * max(0, y2-y1)
    return intersection / max(1e-9, (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection)


def containment(a, b):
    intersection = max(0,min(a[2],b[2])-max(a[0],b[0])) * max(0,min(a[3],b[3])-max(a[1],b[1]))
    return intersection / max(1e-9,min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1])))


def deduplicate(detections):
    kept = []
    for d in sorted(detections, key=lambda x: x['confidence'], reverse=True):
        if not any(d['class'] == k['class'] and (iou(d['bbox_xyxy'], k['bbox_xyxy']) >= .3 or containment(d['bbox_xyxy'],k['bbox_xyxy']) >= .7) for k in kept):
            kept.append(d)
    return kept


class FireDetector:
    def __init__(self, model, config):
        self.model, self.config = model, config
        self.last_full, self.last_time = [], -math.inf

    def predict(self, frame, timestamp, reset=False):
        if reset:
            self.last_full, self.last_time = [], -math.inf
        c = self.config
        result = self.model.predict(frame, imgsz=c['imgsz'], conf=c['proposal_confidence'], device='cpu', verbose=False)[0]
        raw = [{'class': self.model.names[int(b.cls)], 'confidence': float(b.conf), 'bbox_xyxy': b.xyxy[0].tolist(), 'source': 'full_frame'} for b in result.boxes]
        strong = [d for d in raw if d['class'] == 'fire' and d['confidence'] >= c['display_confidence']]
        weak = [d for d in raw if d['class'] == 'fire']
        extra = []
        if strong:
            self.last_full, self.last_time = strong, timestamp
        elif c['recovery']['enabled'] and (weak or timestamp-self.last_time <= c['recovery']['history_seconds']):
            h, w = frame.shape[:2]
            for d in (weak or self.last_full):
                x1, y1, x2, y2 = d['bbox_xyxy']
                size = min(max(c['recovery']['minimum_context_pixels'], 2*max(x2-x1, y2-y1)), max(w, h))
                x = max(0, min(w-int(size), int((x1+x2-size)/2)))
                y = max(0, min(h-int(size), int((y1+y2-size)/2)))
                xx, yy = min(w, x+int(size)), min(h, y+int(size))
                pred = self.model.predict(frame[y:yy, x:xx], imgsz=c['imgsz'], conf=c['recovery']['confidence'], device='cpu', verbose=False)[0]
                for b in pred.boxes:
                    if self.model.names[int(b.cls)] != 'fire':
                        continue
                    z = b.xyxy[0].tolist()
                    box = [z[0]+x, z[1]+y, z[2]+x, z[3]+y]
                    # Require proximity to the seed; a different light elsewhere is not a recovery.
                    if iou(box, d['bbox_xyxy']) < c['recovery']['minimum_seed_iou']:
                        continue
                    extra.append({'class': 'fire', 'confidence': float(b.conf), 'bbox_xyxy': box, 'source': 'current_image_context', 'crop_xyxy': [x, y, xx, yy]})
        fire = deduplicate(strong + extra)
        return raw, extra, fire


class SceneBoundary:
    """Visual cuts plus conservative clock-overlay changes, not hardcoded timestamps."""
    def __init__(self, config):
        self.config, self.previous, self.clock = config, None, None

    def update(self, frame):
        import cv2
        import numpy as np
        c = self.config
        small = cv2.resize(frame, (96, 54)).astype(float) / 255
        difference = float(np.abs(small-self.previous).mean()) if self.previous is not None else 0
        self.previous = small
        changed = False
        roi = c.get('clock_roi_normalized')
        if roi:
            h, w = frame.shape[:2]
            x1, y1, x2, y2 = [int(v*s) for v,s in zip(roi, [w,h,w,h])]
            clock = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY) > c['clock_binary_threshold']
            changed = self.clock is not None and float(np.not_equal(clock, self.clock).mean()) >= c['clock_change_fraction']
            self.clock = clock
        reason = 'visual_scene_cut' if difference >= c['scene_difference'] else 'clock_overlay_changed' if changed else None
        return reason


class FireTemporal:
    def __init__(self, policy):
        self.policy = policy
        self.scene = 0
        self.counter = 0
        self.tracks = {}
        self.previous_time = -math.inf

    def update(self, timestamp, detections, reset=False):
        if timestamp <= self.previous_time:
            raise ValueError('Source timestamps must increase')
        self.previous_time = timestamp
        if reset:
            self.scene += 1
            self.tracks = {}
        p = self.policy
        self.tracks = {key: tr for key,tr in self.tracks.items() if timestamp-tr['last_seen'] <= p['association_gap_seconds']}
        assigned = set()
        current = {}
        for d in deduplicate(detections):
            box = d['bbox_xyxy']
            candidates = [(iou(box,tr['box']),key) for key,tr in self.tracks.items() if key not in assigned]
            score,key = max(candidates, default=(0,None))
            if score < p['association_iou']:
                self.counter += 1
                key = f'FIRE{self.scene}:{self.counter}'
                self.tracks[key] = {'box':box,'last_seen':timestamp,'hits':deque(),'confirmed':False}
            tr = self.tracks[key]
            tr.update(box=box, last_seen=timestamp)
            tr['hits'].append(timestamp)
            assigned.add(key)
            current[key] = box
        events = []
        for key,tr in self.tracks.items():
            while tr['hits'] and timestamp-tr['hits'][0] > p['window_seconds']+1e-8:
                tr['hits'].popleft()
            hits = tr['hits']
            mature = len(hits) >= p['minimum_observations'] and hits[-1]-hits[0] >= p['minimum_span_seconds']-1e-8
            age = timestamp-tr['last_seen']
            confirmed = mature or (tr['confirmed'] and age <= p['hold_seconds']+1e-8)
            # Old window hits alone cannot keep a missing target confirmed beyond hold.
            confirmed = confirmed and age <= p['hold_seconds']+1e-8
            tr['confirmed'] = confirmed
            observed = key in current
            reason = ('repeated_fire_observations' if observed else 'fire_suspected_recent_evidence') if confirmed else 'pending_temporal_confirmation' if observed else 'fire_not_observed'
            events.append({'event_type':'fire','track_id':key,'timestamp_seconds':timestamp,'severity':'CRITICAL' if confirmed else None,'observation_status':'confirmed' if confirmed else 'unconfirmed','reason':reason,'current_detection':observed,'fire_bbox_xyxy':current.get(key),'last_seen_seconds':tr['last_seen'],'seconds_since_last_seen':age,'valid_observations':len(hits),'assessment_basis':'repeated_model_evidence_fire_suspected_not_certified_fire','distance_meters':None})
        return events
