import unittest
from src.forklift_proximity import ForkliftProximity,unreliable_vehicle_pair

class ForkliftProximityTests(unittest.TestCase):
    def vehicles(self,a,b):
        return [{'track_id':'A','bbox_xyxy':a},{'track_id':'B','bbox_xyxy':b}]
    def test_separate_pair_can_be_critical(self):
        # Nearby distinct boxes; shape is (height, width).
        r=ForkliftProximity().update(0,self.vehicles([20,20,120,220],[110,20,210,220]),(480,640))[0]
        self.assertEqual(r['severity'],'CRITICAL')
        self.assertEqual(r['reason'],'image_plane_vehicle_pair_rule')
    def test_high_iou_pair_is_unknown(self):
        a,b=[20,20,120,220],[30,30,130,230]
        r=ForkliftProximity().update(0,self.vehicles(a,b),(480,640))[0]
        self.assertIsNone(r['severity'])
        self.assertEqual(r['reason'],'merged_or_duplicate_vehicle_boxes')
        self.assertTrue(unreliable_vehicle_pair(a,b))
    def test_contained_small_box_is_unknown(self):
        a,b=[20,20,220,220],[70,70,120,120]
        self.assertTrue(unreliable_vehicle_pair(a,b))
        r=ForkliftProximity().update(0,self.vehicles(a,b),(480,640))[0]
        self.assertIsNone(r['severity'])
    def test_clipped_pair_is_unknown(self):
        r=ForkliftProximity().update(0,self.vehicles([0,20,100,220],[250,20,350,220]),(480,400))[0]
        self.assertIsNone(r['severity'])
        self.assertEqual(r['reason'],'forklift_extent_clipped')
