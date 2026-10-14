import unittest,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np,torch
from src.ppe_final_detector import FinalPPEDetector
from src.scenario_render import roi_overlay
from src.detection_review_profile import select_review_objects,exclude_confirmed_equipment
class Video4BatchReviewTests(unittest.TestCase):
 def test_unknown_roi_remains_visible(self):
  im=np.zeros((100,100,3),np.uint8)
  roi_overlay(im,[[10,10],[90,10],[90,90],[10,90]],[],None,unknown_color=[255,180,0])
  self.assertGreater(im[50,50,0],im[50,50,2]);self.assertGreater(im[50,50,0],0)
 def test_context_maps_heads_and_rejects_artificial_crop_edge(self):
  class Model:
   def predict(self,image,**kwargs):
    return [SimpleNamespace(boxes=[SimpleNamespace(cls=torch.tensor(1),conf=torch.tensor(.6),xyxy=torch.tensor([[180.,150.,220.,200.]])),SimpleNamespace(cls=torch.tensor(1),conf=torch.tensor(.8),xyxy=torch.tensor([[0.,150.,30.,200.]]))])]
  d=FinalPPEDetector.__new__(FinalPPEDetector);d.model=Model();d.filter=lambda rows,**kw:rows
  result=d.predict_person_context(np.zeros((1000,1000,3),np.uint8),[[300,400,500,600]])
  self.assertEqual(len(result),1);self.assertEqual(result[0]['box'],[330.,410.,370.,460.])
 def test_supported_real_vehicle_is_kept_unmatched_equipment_rejected(self):
  real={'class':'forklift','confidence':.8,'bbox_xyxy':[20,30,100,150]};fake={'class':'forklift','confidence':.7,'bbox_xyxy':[300,30,400,150]}
  profile={'person_prediction_keys':[],'vehicle_prediction_keys':['base'],'maximum_vehicle_frame_area':.35,'vehicle_support_required':True,'vehicle_support_minimum_confidence':.25,'vehicle_support_minimum_iou':.5}
  kept,rejected=select_review_objects({'base':[real,fake],'vehicle_support':[real]},(600,600),profile)
  self.assertEqual(kept,[real]);self.assertEqual(rejected[0]['review_reason'],'vehicle_not_supported_by_review_model')
 def test_moving_worker_must_not_be_removed_without_reference_evidence(self):
  p=json.loads((Path(__file__).resolve().parents[1]/'configs/video4-object-review.json').read_text())
  rows=[{'class':'person','bbox_xyxy':[137,112,244,247]},{'class':'person','bbox_xyxy':[264,9,354,223]}]
  kept,rejected=exclude_confirmed_equipment(rows,(1080,1920),p);self.assertEqual(kept,rows);self.assertEqual(rejected,[])
 def test_tall_person_extent_can_reject_real_head_under_default_gate(self):
  from src.ppe_person_crop import head_owner
  head=[284,94,298,117];people=[[260,6,340,230]]
  self.assertIsNone(head_owner(head,people,1080))
  self.assertEqual(head_owner(head,people,1080,upper_fraction=.5),0)
