# 역할: 차량 경계의 사람 관측 검수 동작을 회귀 검증합니다.
import unittest
from src.forklift_proximity import ForkliftProximity
from src.detection_review_profile import select_review_objects
class BoundaryReviewTests(unittest.TestCase):
 def test_nearest_extents_and_default_preserved(self):
  v=[dict(track_id='a',bbox_xyxy=[50,50,150,250]),dict(track_id='b',bbox_xyxy=[180,150,400,350])]
  old=ForkliftProximity().update(0,v,(600,600))[0]
  new=ForkliftProximity(distance_geometry='box_boundary',critical=.35).update(0,v,(600,600))[0]
  self.assertGreater(old['image_gap_pixels'],new['image_gap_pixels']);self.assertEqual(new['image_gap_pixels'],30);self.assertEqual(new['severity'],'CRITICAL')
 def test_unsupported_background_person_kept_diagnostic(self):
  d=dict(class_='person',confidence=.31,bbox_xyxy=[20,20,50,60],model_source='person_adaptation');d['class']=d.pop('class_')
  profile=dict(person_prediction_keys=['person_adaptation'],vehicle_prediction_keys=[],maximum_vehicle_frame_area=.35,weak_person_requires_context=True)
  kept,rejected=select_review_objects(dict(person_adaptation=[d]),(500,500),profile)
  self.assertEqual(kept,[]);self.assertEqual(rejected[0]['review_reason'],'weak_person_without_vehicle_or_coco_support')
 def test_weak_observed_operator_is_retained(self):
  p={'class':'person','confidence':.3,'bbox_xyxy':[40,50,70,90],'model_source':'person_adaptation'};v={'class':'forklift','confidence':.7,'bbox_xyxy':[20,20,100,120]}
  profile=dict(person_prediction_keys=['person_adaptation'],vehicle_prediction_keys=['vehicle'],maximum_vehicle_frame_area=.35,weak_person_requires_context=True)
  kept,_=select_review_objects(dict(person_adaptation=[p],vehicle=[v]),(500,500),profile);self.assertEqual(len(kept),2)
 def test_far_vehicle_keeps_ground_separation(self):
  v=[dict(track_id='a',bbox_xyxy=[450,260,700,470]),dict(track_id='b',bbox_xyxy=[615,60,670,200])]
  e=ForkliftProximity(distance_geometry='box_boundary',critical=.35).update(0,v,(720,1280))[0]
  self.assertEqual(e['severity'],'SAFE');self.assertGreater(e['normalized_image_gap'],1)
