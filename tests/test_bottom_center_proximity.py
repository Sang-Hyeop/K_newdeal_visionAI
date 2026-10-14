import unittest
from src.proximity import Proximity
class BottomCenterTests(unittest.TestCase):
 def person(self,box):return dict(track_id='p',bbox_xyxy=box)
 def vehicle(self,box):return dict(track_id='f',bbox_xyxy=box)
 def test_above_box_edge_different_from_ground_point(self):
  p=self.person([140,30,160,90]);f=self.vehicle([100,100,200,250])
  a=Proximity(1,.3,distance_geometry='box_boundary').update(0,[p],[f],(500,500))[0]
  b=Proximity(1,.3,distance_geometry='bottom_center').update(0,[p],[f],(500,500))[0]
  self.assertEqual(a['severity'],'CRITICAL');self.assertEqual(b['severity'],'SAFE');self.assertEqual(b['nearest_vehicle_point_xy'],[150.,250])
 def test_side_close_case_exposes_point_method_blind_spot(self):
  p=self.person([205,150,225,250]);f=self.vehicle([100,100,200,250])
  a=Proximity(1,.3,distance_geometry='box_boundary').update(0,[p],[f],(500,500))[0]
  b=Proximity(1,.3,distance_geometry='bottom_center').update(0,[p],[f],(500,500))[0]
  self.assertEqual(a['severity'],'CRITICAL');self.assertEqual(b['severity'],'WARNING')
 def test_clipped_foot_stays_unknown(self):
  e=Proximity(1,.3,distance_geometry='bottom_center').update(0,[self.person([50,100,70,500])],[self.vehicle([100,100,200,250])],(500,500))[0]
  self.assertIsNone(e['severity']);self.assertIsNone(e['distance_meters'])
