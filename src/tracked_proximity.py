"""Full-frame proximity; fixed forbidden-area ROIs belong to TrackedZone."""
from .person_tracker import PersonTracker
from .proximity import Proximity

class TrackedProximity:
    def __init__(self,config,processed_fps):
        if config.get('distance_mode')!='image_plane':
            raise ValueError('Meter mode requires reviewed calibration; currently image_plane only')
        if config.get('detection_scope')!='full_frame' or 'forklift_ground_roi_normalized' in config:
            raise ValueError('Proximity requires full_frame configuration without a zone ROI')
        self.config=config
        self.people=PersonTracker(processed_fps,config['max_gap_seconds'],namespace='P',fuse_score=config.get('tracker_fuse_score',True))
        self.forklifts=PersonTracker(processed_fps,config['max_gap_seconds'],target_class='forklift',namespace='F',fuse_score=config.get('forklift_tracker_fuse_score',config.get('tracker_fuse_score',True)))
        self.rule=Proximity(config['warning_ratio'],config['critical_ratio'],config['hysteresis_ratio'],config['max_gap_seconds'])
        self.previous={}

    def update(self,timestamp,detections,shape,scene_cut=False):
        scene=self.people.scene
        pt,pm=self.people.update(timestamp,detections,shape,scene_cut)
        ft,fm=self.forklifts.update(timestamp,detections,shape,scene_cut)
        if self.people.scene!=scene:
            self.rule.reset();self.previous.clear()
        events=self.rule.update(timestamp,pt,ft,shape);transitions=[]
        for event in events:
            event.update(camera_id=self.config['camera_id'],distance_unit='person_height_normalized_image_gap',zone_roi_used=False)
            key=(event['person_track_id'],event['forklift_track_id']);state=(event['severity'],event['reason'])
            if self.previous.get(key)!=state:transitions.append(event.copy())
            self.previous[key]=state
        active={(e['person_track_id'],e['forklift_track_id']) for e in events}
        self.previous={k:v for k,v in self.previous.items() if k in active}
        return {'timestamp_seconds':timestamp,'scene_id':self.people.scene,'people':pt,'forklifts':ft,
                'missing_people':pm,'missing_forklifts':fm,'events':events,'transitions':transitions,
                'scene_cut':scene_cut,'zone_roi_used':False,'detection_scope':'full_frame',
                'global_safety_status':'not_evaluated','pair_observation_status':'some_pairs_observed' if any(e['severity'] is not None for e in events) else 'unconfirmed'}
