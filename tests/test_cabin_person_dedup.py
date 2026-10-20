# 역할: 운전석 사람 중복 제거 동작을 회귀 검증합니다.
import unittest
from src.detection_review_profile import select_review_objects
class CabinDedupTests(unittest.TestCase):
 def select(self,boxes):
  people=[{'class':'person','confidence':.8-i*.1,'bbox_xyxy':b,'model_source':str(i)}for i,b in enumerate(boxes)]
  v={'class':'forklift','confidence':.9,'bbox_xyxy':[10,10,300,350]}
  return select_review_objects({'people':people,'vehicles':[v]},(800,800),{'person_prediction_keys':['people'],'vehicle_prediction_keys':['vehicles'],'maximum_vehicle_frame_area':.35,'deduplicate_cabin_people':True})
 def test_nested_operator_is_one(self):
  kept,rejected=self.select([[50,50,150,200],[65,65,110,175]])
  self.assertEqual(sum(d['class']=='person'for d in kept),1);self.assertEqual(rejected[0]['review_reason'],'duplicate_person_cross_model_same_cabin')
 def test_two_people_same_vehicle_are_not_forced_to_one(self):
  kept,_=self.select([[30,50,100,200],[180,50,250,200]])
  self.assertEqual(sum(d['class']=='person'for d in kept),2)
 def test_outside_pedestrians_are_preserved(self):
  kept,_=self.select([[400,50,500,200],[415,65,470,175]])
  self.assertEqual(sum(d['class']=='person'for d in kept),2)
