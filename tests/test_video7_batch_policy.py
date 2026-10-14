import unittest
from src.operator_association import OperatorAssociation
from src.lane_hazard import LaneHazard
from src.tracked_proximity import TrackedProximity

class BatchPolicyTests(unittest.TestCase):
 def test_rider_own_vehicle_excluded_but_other_vehicle_retained(self):
  cfg=dict(distance_mode='image_plane',detection_scope='full_frame',max_gap_seconds=1,warning_ratio=1,critical_ratio=.3,hysteresis_ratio=.1,distance_geometry='box_boundary',associate_riders=True,camera_id='test')
  r=TrackedProximity(cfg,5)
  detections=[dict(class_='person',bbox_xyxy=[140,120,190,180],confidence=.9),dict(class_='forklift',bbox_xyxy=[100,100,240,300],confidence=.9),dict(class_='forklift',bbox_xyxy=[270,100,400,300],confidence=.9)]
  detections=[{**d,'class':d['class_']} for d in detections]
  out=r.update(0,detections,(500,500))
  self.assertEqual(len(out['excluded_rider_pairs']),1);self.assertEqual(len(out['events']),1)
  self.assertNotEqual(out['events'][0]['forklift_track_id'],out['excluded_rider_pairs'][0]['forklift_track_id'])
 def test_recent_pedestrian_overlap_not_misclassified_as_rider(self):
  r=OperatorAssociation();p=dict(track_id='p',bbox_xyxy=[40,100,70,170]);v=dict(track_id='v',bbox_xyxy=[100,90,240,300])
  self.assertEqual(r.update(0,[p],[v]),{})
  v['bbox_xyxy']=[20,90,240,300]
  self.assertEqual(r.update(.2,[p],[v]),{})
 def test_three_seconds_counts_shared_observation_not_prior_dwell(self):
  r=LaneHazard([[0,0],[490,0],[490,490],[0,490]],policy='timed',critical_seconds=3,co_presence_timing=True)
  vehicle=dict(track_id='v',bbox_xyxy=[250,50,350,250])
  def event():return dict(event_type='zone_dwell',track_id='p',inside=True,observation_status='confirmed',person_bbox_xyxy=[50,50,80,200],observed_dwell_seconds=100,severity='WARNING')
  for t in [0,.5,1,1.5,2,2.5,3]:
   e=event();r.update(t,[e],[vehicle],(500,500));self.assertEqual(e['severity'],'CRITICAL' if t>=3 else 'WARNING')
  self.assertEqual(e['observed_vehicle_co_presence_seconds'],3)
 def test_missing_vehicle_time_not_counted(self):
  r=LaneHazard([[0,0],[490,0],[490,490],[0,490]],policy='timed',critical_seconds=3,co_presence_timing=True)
  v=dict(track_id='v',bbox_xyxy=[250,50,350,250])
  def event():return dict(event_type='zone_dwell',track_id='p',inside=True,observation_status='confirmed',person_bbox_xyxy=[50,50,80,200],observed_dwell_seconds=100,severity='WARNING')
  for t,vs in [(0,[v]),(.5,[v]),(1,[]),(1.5,[v])]:
   e=event();r.update(t,[e],vs,(500,500))
  self.assertEqual(e['observed_vehicle_co_presence_seconds'],.5);self.assertEqual(e['severity'],'WARNING')

class ROIAndOpenRiderTests(unittest.TestCase):
 def test_user_storage_is_excluded_and_walkway_remains(self):
  import json
  from pathlib import Path
  from src.scenario_zone import ScenarioZone
  cfg=json.loads((Path(__file__).resolve().parents[1]/'configs/cameras/warehouse-summary.json').read_text())
  z=ScenarioZone(cfg,(720,1280),5)
  for point,inside in [((.12,.33),True),((.4,.3),False),((.65,.8),False),((.25,.6),True)]:
   self.assertEqual(z.contains((point[0]*1280,point[1]*720)),inside)
 def test_open_rider_preserves_person_but_excludes_own_pair(self):
  r=OperatorAssociation();p=dict(track_id='p',bbox_xyxy=[110,110,160,230]);v=dict(track_id='v',bbox_xyxy=[100,100,170,240])
  self.assertEqual(r.update(0,[p],[v]),{'p':'v'})
 def test_slim_standing_person_not_excluded_by_containment_alone(self):
  r=OperatorAssociation();p=dict(track_id='p',bbox_xyxy=[120,110,140,290]);v=dict(track_id='v',bbox_xyxy=[100,100,240,300])
  self.assertEqual(r.update(0,[p],[v]),{})

class SupportedTrackingTests(unittest.TestCase):
 def test_low_supported_vehicle_has_current_track_without_score_inflation(self):
  from src.person_tracker import PersonTracker
  t=PersonTracker(5,target_class='forklift',high_threshold=.12,fuse_score=False)
  d={'class':'forklift','confidence':.14,'bbox_xyxy':[100,100,240,300]}
  tracks,_=t.update(0,[d],(500,500))
  self.assertEqual(len(tracks),1);self.assertAlmostEqual(tracks[0]['confidence'],.14,places=5)
  track_id=tracks[0]['track_id']
  tracks,_=t.update(.2,[{**d,'bbox_xyxy':[102,100,242,300]}],(500,500))
  self.assertEqual(tracks[0]['track_id'],track_id)
 def test_default_tracker_still_rejects_weak_new_vehicle(self):
  from src.person_tracker import PersonTracker
  t=PersonTracker(5,target_class='forklift')
  tracks,_=t.update(0,[{'class':'forklift','confidence':.14,'bbox_xyxy':[100,100,240,300]}],(500,500))
  self.assertEqual(tracks,[])
