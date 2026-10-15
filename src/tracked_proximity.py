"""추적된 사람/지게차로 전체 화면 근접 이벤트를 만든다. 고정 금지 ROI는 TrackedZone 담당."""
from .person_tracker import PersonTracker
from .proximity import Proximity
from .operator_association import OperatorAssociation, TemporalOperatorAssociation
from .vehicle_occupancy import VehicleOccupancy, gate_proximity

class TrackedProximity:
    def __init__(self,config,processed_fps):
        if config.get('distance_mode')!='image_plane':
            raise ValueError('Meter mode requires reviewed calibration; currently image_plane only')
        if config.get('detection_scope')!='full_frame' or 'forklift_ground_roi_normalized' in config:
            raise ValueError('Proximity requires full_frame configuration without a zone ROI')
        self.config=config
        self.people=PersonTracker(processed_fps,config['max_gap_seconds'],namespace='P',expose_current_candidates=config.get('expose_current_person_candidates',False),fuse_score=config.get('tracker_fuse_score',True))
        self.forklifts=PersonTracker(processed_fps,config['max_gap_seconds'],target_class='forklift',namespace='F',fuse_score=config.get('forklift_tracker_fuse_score',config.get('tracker_fuse_score',True)),high_threshold=config.get('forklift_tracker_high_threshold',.25))
        self.rule=Proximity(config['warning_ratio'],config['critical_ratio'],config['hysteresis_ratio'],config['max_gap_seconds'],recent_pedestrian_overlap=config.get('recent_pedestrian_overlap',False),distance_geometry=config.get('distance_geometry','ground_band'),exclude_probable_operator=config.get('exclude_probable_operator',False))
        self.previous={}
        self.operators=(TemporalOperatorAssociation if config.get('temporal_riders') else OperatorAssociation)(config['max_gap_seconds']) if config.get('associate_riders') else None
        self.occupancy=VehicleOccupancy(config.get('occupancy_minimum_observations',3),config['max_gap_seconds']) if config.get('proximity_requires_observed_rider') else None

    def update(self,timestamp,detections,shape,scene_cut=False,roi_active=True):
        scene=self.people.scene
        pt,pm=self.people.update(timestamp,detections,shape,scene_cut)
        ft,fm=self.forklifts.update(timestamp,detections,shape,scene_cut)
        if self.people.scene!=scene:
            self.rule.reset();self.previous.clear()
            if self.operators:self.operators.reset()
            if self.occupancy:self.occupancy.reset()
        events=self.rule.update(timestamp,pt,ft,shape);transitions=[]
        associations=self.operators.update(timestamp,pt,ft) if self.operators else {}
        def rider_pair(e):return e['person_track_id'] in associations if self.config.get('exclude_riders_from_all_proximity') else associations.get(e['person_track_id'])==e['forklift_track_id']
        excluded=[{**e,'suppression_reason':'confirmed_rider_not_pedestrian'} for e in events if rider_pair(e)]
        events=[e for e in events if not rider_pair(e)]
        pending=set(self.operators.states)-set(associations) if self.config.get('temporal_riders') and self.operators else set()
        for event in events:
            if event['person_track_id'] in pending:event.update(severity=None,observation_status='unconfirmed',reason='person_role_confirmation_pending',person_role_pending=True,distance_display_enabled=False,notification_enabled=False)
        occupancy=self.occupancy.update(timestamp,pt,ft,associations) if self.occupancy else {}
        suppressed=[]
        if self.occupancy:events,suppressed=gate_proximity(events,occupancy,shape,self.config,roi_active)
        for event in events:
            event.update(camera_id=self.config['camera_id'],distance_unit='person_height_normalized_image_gap',zone_roi_used=bool(self.occupancy))
            key=(event['person_track_id'],event['forklift_track_id']);state=(event['severity'],event['reason'])
            if self.previous.get(key)!=state:transitions.append(event.copy())
            self.previous[key]=state
        active={(e['person_track_id'],e['forklift_track_id']) for e in events}
        self.previous={k:v for k,v in self.previous.items() if k in active}
        return {'timestamp_seconds':timestamp,'scene_id':self.people.scene,'people':pt,'forklifts':ft,
                'missing_people':pm,'missing_forklifts':fm,'events':events,'transitions':transitions,
                'scene_cut':scene_cut,'zone_roi_used':bool(self.occupancy),'detection_scope':'full_frame',
                'vehicle_occupancy':occupancy,'suppressed_proximity_events':suppressed,
                'pending_rider_ids':sorted(pending),'excluded_rider_pairs':excluded,'rider_associations':associations,'global_safety_status':'not_evaluated','pair_observation_status':'some_pairs_observed' if any(e['severity'] is not None for e in events) else 'unconfirmed'}
