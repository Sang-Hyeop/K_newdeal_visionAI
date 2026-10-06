"""Connect observed person tracks to a camera-specific demonstration dwell rule."""
from .person_tracker import PersonTracker
from .zone_dwell import ZoneDwell


class TrackedZone:
    def __init__(self, config, shape, processed_fps):
        h,w=shape
        points=config['polygon_normalized']
        if any(len(p)!=2 or not all(0<=v<=1 for v in p) for p in points):
            raise ValueError('ROI requires normalized XY coordinates')
        self.polygon=[[x*w,y*h] for x,y in points]
        self.tracker=PersonTracker(processed_fps,config['max_gap_seconds'])
        self.dwell=ZoneDwell(self.polygon,config['safe_seconds'],config['critical_seconds'],config['max_gap_seconds'])
        self.config=config
        self.previous={}
        self.roi_active=True

    def update(self,timestamp,detections,shape,scene_cut=False):
        old_scene=self.tracker.scene
        tracks,missing=self.tracker.update(timestamp,detections,shape,scene_cut)
        if self.tracker.scene!=old_scene:
            self.dwell.reset();self.previous.clear()
        # A new camera view needs new ROI configuration, not reused old pixels.
        if scene_cut:self.roi_active=False
        events=self.dwell.update(timestamp,tracks) if self.roi_active else []
        transitions=[]
        current_ids=set()
        for event in events:
            event.update(camera_id=self.config['camera_id'],roi_id=self.config['roi_id'],
                         scope='configured_demo_dwell_rule',roi_purpose=self.config['roi_purpose'])
            key=event['track_id'];current_ids.add(key)
            state=(event['severity'],event['observation_status'],event['inside'])
            if self.previous.get(key)!=state:transitions.append(event.copy())
            self.previous[key]=state
        for key in set(self.previous)-current_ids:self.previous.pop(key,None)
        return {'timestamp_seconds':timestamp,'scene_id':self.tracker.scene,
                'tracks':tracks,'missing_tracks':missing,'events':events,'transitions':transitions,
                'roi_active':self.roi_active,
                'global_safety_status':'not_evaluated',
                'zone_observation_status':'confirmed_person_observations' if tracks and self.roi_active else 'unconfirmed'}
