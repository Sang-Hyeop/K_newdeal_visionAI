"""Connect observed person tracks to a camera-specific demonstration dwell rule."""
from .person_tracker import PersonTracker
from .zone_dwell import ZoneDwell
from .zone_access import ZoneAccess
from .lane_hazard import LaneHazard


class TrackedZone:
    def __init__(self, config, shape, processed_fps):
        h,w=shape
        points=config['polygon_normalized']
        if any(len(p)!=2 or not all(0<=v<=1 for v in p) for p in points):
            raise ValueError('ROI requires normalized XY coordinates')
        self.polygon=[[x*w,y*h] for x,y in points]
        self.tracker=PersonTracker(processed_fps,config['max_gap_seconds'])
        self.dwell=ZoneDwell(self.polygon,config['safe_seconds'],config['critical_seconds'],config['max_gap_seconds'])
        self.access=None
        if config.get('access_enabled',False):
            ratio=config['approach_margin_ratio']
            if not 0<ratio<1:raise ValueError('Approach margin must be a normalized image ratio')
            self.access=ZoneAccess(self.polygon,min(w,h)*ratio,config['max_gap_seconds'])
        self.forklift_tracker=PersonTracker(processed_fps,config['max_gap_seconds'],target_class='forklift',namespace='F') if config.get('vehicle_conditioned',False) else None
        self.lane=LaneHazard(self.polygon,config.get('vehicle_missing_hold_seconds',1.0)) if self.forklift_tracker else None
        self.config=config
        self.previous={}
        self.roi_active=True

    def update(self,timestamp,detections,shape,scene_cut=False):
        old_scene=self.tracker.scene
        ft,fm=self.forklift_tracker.update(timestamp,detections,shape,scene_cut) if self.forklift_tracker else ([],[])
        tracks,missing=self.tracker.update(timestamp,detections,shape,scene_cut)
        if self.tracker.scene!=old_scene:
            self.dwell.reset();self.previous.clear()
            if self.access:self.access.reset()
        # A new camera view needs new ROI configuration, not reused old pixels.
        if scene_cut:
            self.roi_active=False
            if self.lane:self.lane.reset()
        # Bottom-clipped boxes do not provide a usable footpoint. They must not
        # fabricate a zone exit merely because the image ends at that pixel.
        rule_tracks=[];invalid_anchors=[]
        for track in tracks:
            detected_box=track['detected_bbox_xyxy']
            usable=detected_box[3]<shape[0]-1
            track['anchor_status']='bbox_bottom_center_proxy' if usable else 'unconfirmed_bottom_clipped'
            if usable:rule_tracks.append({**track,'bbox_xyxy':detected_box})
            else:invalid_anchors.append(track['track_id'])
        observed_boxes={t['track_id']:t['detected_bbox_xyxy'] for t in tracks}
        events=self.dwell.update(timestamp,rule_tracks) if self.roi_active else []
        if self.roi_active and self.access:events+=self.access.update(timestamp,rule_tracks)
        for event in events:
            if event['observation_status']=='confirmed' and event['track_id'] in observed_boxes:event['person_bbox_xyxy']=observed_boxes[event['track_id']]
        vehicle_state=self.lane.update(timestamp,events,ft,shape) if self.lane and self.roi_active else None
        transitions=[]
        current_ids=set()
        for event in events:
            if event['observation_status']=='confirmed' and event['track_id'] in observed_boxes:event['person_bbox_xyxy']=observed_boxes[event['track_id']]
            event.update(camera_id=self.config['camera_id'],roi_id=self.config['roi_id'],
                         scope='configured_demo_dwell_rule' if event['event_type']=='zone_dwell' else 'configured_demo_access_rule',roi_purpose=self.config['roi_purpose'],roi_review_status=self.config.get('roi_review_status','not_reviewed'))
            key=(event['event_type'],event['track_id']);current_ids.add(key)
            state=(event['severity'],event['observation_status'],event['inside'],event.get('vehicle_lane_state'),event.get('risk_reason'),tuple(event.get('vehicle_track_ids',[])))
            if self.previous.get(key)!=state:transitions.append(event.copy())
            self.previous[key]=state
        for key in set(self.previous)-current_ids:self.previous.pop(key,None)
        return {'timestamp_seconds':timestamp,'scene_id':self.tracker.scene,
                'tracks':tracks,'missing_tracks':missing,'events':events,'transitions':transitions,
                'roi_active':self.roi_active,'forklifts':ft,'missing_forklifts':fm,'vehicle_lane_state':vehicle_state,
                'invalid_anchor_track_ids':invalid_anchors,
                'global_safety_status':'not_evaluated',
                'zone_observation_status':'confirmed_person_observations' if rule_tracks and self.roi_active else 'unconfirmed'}
