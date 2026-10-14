import unittest
import numpy as np
from unittest.mock import patch
from src.equipment_reference import matches_empty_equipment
from src.detection_review_profile import exclude_confirmed_equipment
class ReferenceTests(unittest.TestCase):
 def config(self):return dict(empty_reference=dict(frame_size=[100,100],comparison_box_xyxy=[0,0,100,100],image_path='unused',pixel_difference_threshold=25,maximum_changed_fraction=.06),bbox_normalized=[0,0,1,1],excluded_classes=['person'],minimum_coverage=.8)
 def test_static_reference_blocks_but_changed_person_not_removed(self):
  region=self.config();p={'class':'person','bbox_xyxy':[10,10,90,90]};empty=np.zeros((100,100,3),np.uint8);changed=empty.copy();changed[20:80,20:80]=200
  with patch('src.equipment_reference._reference',return_value=empty[:,:,0]):
   self.assertFalse(exclude_confirmed_equipment([p],(100,100),dict(confirmed_equipment_regions=[region]),empty)[0])
   self.assertEqual(exclude_confirmed_equipment([p],(100,100),dict(confirmed_equipment_regions=[region]),changed)[0],[p])
 def test_no_image_cannot_assert_static_equipment(self):
  self.assertFalse(matches_empty_equipment(None,self.config()))
 def test_wrong_camera_dimensions_rejected(self):
  with self.assertRaises(ValueError):matches_empty_equipment(np.zeros((10,10,3),np.uint8),self.config())
 def test_reviewed_moving_box_at_16s_survives_static_region_boundary(self):
  import json
  from pathlib import Path
  profile=json.loads((Path(__file__).resolve().parents[1]/'configs/video4-object-review.json').read_text())
  person={'class':'person','bbox_xyxy':[165.9549560546875,114.76364135742188,246.33358764648438,247.4011688232422]}
  with patch('src.equipment_reference.matches_empty_equipment',return_value=True):
   kept,_=exclude_confirmed_equipment([person],(1080,1920),profile,np.zeros((1080,1920,3),np.uint8))
  self.assertEqual(kept,[person])
