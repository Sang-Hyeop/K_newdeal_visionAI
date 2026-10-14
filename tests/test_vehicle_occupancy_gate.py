import unittest
from src.vehicle_occupancy import gate_proximity,VehicleOccupancy
CFG={'monitor_floor_normalized':[[0,0],[.5,0],[.5,1],[0,1]],'safe_polygons_normalized':[]}
class OccupancyGateTests(unittest.TestCase):
 def event(self,x,severity='WARNING'):
  return dict(person_track_id='p',forklift_track_id='f',person_anchor_xy=[x,50],severity=severity,observation_status='confirmed')
 def occupied(self):return {'f':dict(status='occupied_observed',rider_track_ids=['driver'])}
 def test_unconfirmed_occupancy_cannot_emit_distance_alarm(self):
  visible,_=gate_proximity([self.event(20,'CRITICAL')],{},(100,100),CFG)
  self.assertIsNone(visible[0]['severity']);self.assertFalse(visible[0]['notification_enabled'])
 def test_inside_warning_visible(self):
  visible,_=gate_proximity([self.event(20)],self.occupied(),(100,100),CFG)
  self.assertTrue(visible[0]['distance_display_enabled']);self.assertTrue(visible[0]['notification_enabled'])
 def test_outside_warning_suppressed_but_critical_visible(self):
  visible,suppressed=gate_proximity([self.event(80)],self.occupied(),(100,100),CFG)
  self.assertFalse(visible);self.assertEqual(len(suppressed),1)
  visible,_=gate_proximity([self.event(80,'CRITICAL')],self.occupied(),(100,100),CFG)
  self.assertTrue(visible[0]['notification_enabled'])
 def test_self_vehicle_rider_never_alerts(self):
  e=self.event(20,'CRITICAL');e['person_track_id']='driver'
  visible,suppressed=gate_proximity([e],self.occupied(),(100,100),CFG)
  self.assertFalse(visible);self.assertEqual(suppressed[0]['suppression_reason'],'self_vehicle_rider')
 def test_rider_loss_does_not_confirm_empty_vehicle(self):
  p=VehicleOccupancy(2);v={'track_id':'f','bbox_xyxy':[0,0,50,50]};person={'track_id':'driver'}
  p.update(0,[person],[v],{'driver':'f'});self.assertEqual(p.update(.2,[person],[v],{'driver':'f'})['f']['status'],'occupied_observed')
  result=p.update(.4,[],[v],{})['f'];self.assertEqual(result['status'],'unconfirmed');self.assertFalse(result['absence_confirmed'])
