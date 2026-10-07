import unittest,numpy as np
from src.forklift_proximity import ForkliftProximity
from src.lane_hazard import LaneHazard
from src.scenario_zone import ScenarioZone
from src.scenario_render import roi_overlay
from src.event_contract import normalize_event
P=[[10,10],[290,10],[290,290],[10,290]]
def e(dwell=0):return {'event_type':'zone_dwell','track_id':'p','inside':True,'severity':'SAFE','observation_status':'confirmed','observed_dwell_seconds':dwell,'person_bbox_xyxy':[200,30,230,90]}
V={'track_id':'f','bbox_xyxy':[20,20,90,90]}
class ScenarioTests(unittest.TestCase):
 def test_v7_no_vehicle_exact_three_seconds(self):
  rule=LaneHazard(P,policy='timed');a=e(2.999);rule.update(0,[a],[],(300,300));self.assertEqual(a['severity'],'SAFE');b=e(3);rule.update(.2,[b],[],(300,300));self.assertEqual(b['severity'],'WARNING');c=e(20);rule.update(.4,[c],[],(300,300));self.assertEqual(c['severity'],'WARNING')
 def test_v7_vehicle_exact_five_seconds(self):
  rule=LaneHazard(P,policy='timed');a=e();rule.update(0,[a],[V],(300,300));self.assertEqual(a['severity'],'WARNING');b=e(4.999);rule.update(.2,[b],[V],(300,300));self.assertEqual(b['severity'],'WARNING');c=e(5);rule.update(.4,[c],[V],(300,300));self.assertEqual(c['severity'],'CRITICAL')
 def test_v4_vehicle_immediately_critical(self):
  a=e();LaneHazard(P).update(0,[a],[V],(300,300));self.assertEqual(a['severity'],'CRITICAL')
 def test_vehicle_outside_lane_does_not_escalate(self):
  a=e();LaneHazard(P,contains=lambda point:point[0]>150,policy='timed').update(0,[a],[V],(300,300));self.assertEqual(a['severity'],'SAFE')
 def test_lost_vehicle_becomes_unknown(self):
  rule=LaneHazard(P,policy='timed');rule.update(0,[e(5)],[V],(300,300));a=e(8);rule.update(2,[a],[],(300,300));self.assertIsNone(a['severity'])
 def test_potential_driver_unknown(self):
  a=e();a['person_bbox_xyxy']=[30,30,40,80];LaneHazard(P,policy='timed').update(0,[a],[V],(300,300));self.assertIsNone(a['severity'])
 def test_vehicle_pair_symmetric_close_and_missing(self):
  rule=ForkliftProximity();a={'track_id':'a','bbox_xyxy':[20,40,100,140]};b={'track_id':'b','bbox_xyxy':[110,40,190,140]};rows=rule.update(0,[b,a],(300,300));self.assertEqual(rows[0]['severity'],'CRITICAL');self.assertEqual(rows[0]['forklift_track_ids'],['a','b']);lost=rule.update(.2,[a],(300,300));self.assertIsNone(lost[0]['severity'])
 def test_vehicle_pair_clipping_unknown(self):
  a={'track_id':'a','bbox_xyxy':[0,40,100,140]};b={'track_id':'b','bbox_xyxy':[100,40,200,140]};self.assertIsNone(ForkliftProximity().update(0,[a,b],(300,300))[0]['severity'])
 def test_vehicle_pair_contract(self):
  row=normalize_event({'event_type':'forklift_forklift_proximity','forklift_track_ids':['a','b'],'timestamp_seconds':0,'severity':'WARNING','observation_status':'confirmed'},camera_id='c',video='v',source_sha256='s',model_version='m',config_version='cfg');self.assertEqual(row['track_ids'],['a','b'])
 def test_roi_alpha_and_hole(self):
  image=np.full((300,300,3),100,np.uint8);hole=[[100,100],[150,100],[150,150],[100,150]];roi_overlay(image,P,[hole],'WARNING');self.assertEqual(image[50,50].tolist(),[80,108,131]);self.assertEqual(image[120,120].tolist(),[85,112,85])
 def test_unknown_roi_is_not_green_fill(self):
  image=np.full((300,300,3),100,np.uint8);roi_overlay(image,P,[],None);self.assertEqual(image[50,50].tolist(),[100,100,100])
 def config(self):return {'camera_id':'c','roi_id':'z','max_gap_seconds':1,'safe_seconds':3,'critical_seconds':5,'vehicle_missing_hold_seconds':1,'monitor_floor_normalized':[[.1,.1],[.9,.1],[.9,.9],[.1,.9]],'safe_polygons_normalized':[[[.4,.4],[.6,.4],[.6,.6],[.4,.6]]]}
 def test_safe_zone_is_not_vehicle_lane(self):
  rule=ScenarioZone(self.config(),(500,500),5);r=rule.update(0,[{'class':'person','confidence':.9,'bbox_xyxy':[230,200,270,250]}],(500,500));self.assertFalse(r['events'][0]['inside']);self.assertEqual(r['events'][0]['severity'],'SAFE')
 def test_unmonitored_floor_is_unknown(self):
  rule=ScenarioZone(self.config(),(500,500),5);r=rule.update(0,[{'class':'person','confidence':.9,'bbox_xyxy':[20,20,40,80]}],(500,500));self.assertIsNone(r['events'][0]['severity'])
 def test_long_gap_does_not_prove_vehicle_absence(self):
  rule=ScenarioZone(self.config(),(500,500),5);p={'class':'person','confidence':.9,'bbox_xyxy':[380,50,410,100]};f={'class':'forklift','confidence':.9,'bbox_xyxy':[70,70,140,150]};rule.update(0,[p,f],(500,500));r=rule.update(2,[p],(500,500));self.assertIsNone(r['events'][0]['severity'])
 def test_adaptation_only_helmet_cannot_claim_safe(self):
  from src.ppe_events import PPEEvents
  policy={'minimum_consecutive_frames':3,'minimum_confirmed_seconds':.4,'maximum_observation_gap_seconds':.45,'minimum_head_confidence':.5,'require_baseline_helmet_confirmation':True};rule=PPEEvents(policy);track={'track_id':'p','bbox_xyxy':[10,10,50,100],'ppe':{'state':'helmet_detected','head_candidates':[{'class':'helmeted_head','confidence':.99,'bbox_xyxy':[15,10,40,35],'model_sources':['helmet_specialist']}]}}
  for t in[0,.2,.4]:rows,_=rule.update(t,[track])
  self.assertIsNone(rows[0]['severity']);self.assertEqual(rows[0]['reason'],'supplement_only_helmet_unconfirmed')
  track['ppe']['head_candidates'].append({'class':'helmeted_head','confidence':.7,'bbox_xyxy':[15,10,40,35],'model_sources':['baseline']})
  for t in[.6,.8,1.01]:rows,_=rule.update(t,[track])
  self.assertEqual(rows[0]['severity'],'SAFE')
