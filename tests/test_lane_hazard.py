import unittest
from src.lane_hazard import LaneHazard
from src.tracked_zone import TrackedZone
P=[[100,100],[400,100],[400,400],[100,400]]
def event(inside=True,kind='zone_access'):
 return dict(event_type=kind,track_id='p',inside=inside,severity='CRITICAL' if inside else 'SAFE',observation_status='confirmed',person_bbox_xyxy=[110,120,130,240])
def fork(inside=True):return {'track_id':'f','bbox_xyxy':[200,150,260,300] if inside else [420,100,480,200]}
class LaneTests(unittest.TestCase):
 def test_full_pipeline_tracks_both_classes_and_holds_missing_vehicle(self):
  cfg=dict(polygon_normalized=[[x/500,y/500] for x,y in P],max_gap_seconds=1,safe_seconds=3,critical_seconds=5,access_enabled=True,approach_margin_ratio=.01,vehicle_conditioned=True,vehicle_missing_hold_seconds=1,lane_policy='timed',camera_id='c',roi_id='lane',roi_purpose='vehicle_lane')
  pipe=TrackedZone(cfg,(500,500),5)
  d=[{'class':'person','bbox_xyxy':[110,120,130,240],'confidence':.9},{'class':'forklift','bbox_xyxy':[200,150,260,300],'confidence':.9}]
  r=pipe.update(0,d,(500,500));self.assertTrue(r['forklifts']);self.assertTrue(all(e['severity']=='WARNING' for e in r['events'] if e['event_type']=='zone_dwell'))
  r=pipe.update(.2,d[:1],(500,500));self.assertEqual(r['vehicle_lane_state']['state'],'recent_vehicle_missing_hold');self.assertTrue(all(e['severity']=='WARNING' for e in r['events'] if e['event_type']=='zone_dwell'))
  for i in range(1,30):
   r=pipe.update(.2+i/5,d,(500,500))
  dwell=[e for e in r['events'] if e['event_type']=='zone_dwell'][0]
  self.assertEqual(dwell['severity'],'CRITICAL');self.assertGreaterEqual(dwell['observed_dwell_seconds'],5)
  self.assertEqual(dwell['roi_polygon_normalized'],cfg['polygon_normalized'])
 def test_pedestrian_without_vehicle_warning_even_long_dwell(self):
  r=LaneHazard(P);e=event(kind='zone_dwell');e['observed_dwell_seconds']=12
  state=r.update(0,[e],[],(500,500));self.assertEqual(e['severity'],'WARNING');self.assertEqual(e['dwell_time_band'],'CRITICAL');self.assertEqual(state['state'],'no_vehicle_detected_in_lane');self.assertFalse(e['vehicle_absence_confirmed'])
 def test_vehicle_inside_critical_outside_not_critical(self):
  for inside,expected in [(True,'CRITICAL'),(False,'WARNING')]:
   r=LaneHazard(P);e=event();r.update(0,[e],[fork(inside)],(500,500));self.assertEqual(e['severity'],expected)
 def test_missing_holds_then_unknown_never_drops_to_warning(self):
  r=LaneHazard(P);r.update(0,[event()],[fork()],(500,500))
  e=event();r.update(.2,[e],[],(500,500));self.assertEqual(e['severity'],'CRITICAL');self.assertEqual(e['vehicle_observation_status'],'unconfirmed')
  e=event();r.update(1.2,[e],[],(500,500));self.assertIsNone(e['severity']);self.assertEqual(e['observation_status'],'unconfirmed')
 def test_observed_vehicle_exit_releases_hold(self):
  r=LaneHazard(P);r.update(0,[event()],[fork()],(500,500));e=event();r.update(.2,[e],[fork(False)],(500,500));self.assertEqual(e['severity'],'WARNING')
 def test_person_outside_allowed_area_safe_even_vehicle_present(self):
  r=LaneHazard(P);e=event(False);r.update(0,[e],[fork()],(500,500));self.assertEqual(e['severity'],'SAFE')
 def test_unobserved_person_not_safe(self):
  r=LaneHazard(P);e=event();e.update(inside=None,observation_status='unconfirmed');r.update(0,[e],[],(500,500));self.assertIsNone(e['severity'])
 def test_driver_overlap_unknown(self):
  r=LaneHazard(P);e=event();e['person_bbox_xyxy']=[220,160,240,200];r.update(0,[e],[fork()],(500,500));self.assertIsNone(e['severity']);self.assertEqual(e['risk_reason'],'possible_vehicle_operator_or_occluded_person')
 def test_clipped_vehicle_unknown(self):
  r=LaneHazard(P);e=event();r.update(0,[e],[{'track_id':'f','bbox_xyxy':[200,200,250,500]}],(500,500));self.assertIsNone(e['severity'])
if __name__=='__main__':unittest.main()

class UserThreeSecondLaneTests(unittest.TestCase):
 def test_multiple_people_vehicle_and_no_vehicle_boundary(self):
  for has_vehicle in [False,True]:
   rule=LaneHazard(P,policy='timed',safe_seconds=3,critical_seconds=3)
   for timestamp in [0,2.99,3,3.01]:
    events=[]
    for key in ['p1','p2']:
     e=event(kind='zone_dwell');e.update(track_id=key,observed_dwell_seconds=timestamp);events.append(e)
    rule.update(timestamp,events,[fork()] if has_vehicle else [],(500,500))
    expected=('WARNING' if timestamp<3 else 'CRITICAL') if has_vehicle else ('SAFE' if timestamp<3 else 'WARNING')
    self.assertEqual([e['severity'] for e in events],[expected,expected])
 def test_configured_camera_routes_use_user_vehicle_threshold(self):
  import json
  from pathlib import Path
  from src.scenario_zone import ScenarioZone
  root=Path(__file__).resolve().parents[1]
  for name,cls in [('dwell-demo.json',TrackedZone),('warehouse-summary.json',ScenarioZone)]:
   cfg=json.loads((root/'configs/cameras'/name).read_text());pipe=cls(cfg,(720,1280),5)
   self.assertEqual(pipe.lane.safe,3);self.assertEqual(pipe.lane.critical,3)
