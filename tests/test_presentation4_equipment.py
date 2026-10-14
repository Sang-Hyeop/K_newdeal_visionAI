import json, unittest
from pathlib import Path
from src.detection_review_profile import exclude_confirmed_equipment

class Presentation4EquipmentTests(unittest.TestCase):
 def test_far_left_machine_rejected_right_worker_retained(self):
  profile=json.loads((Path(__file__).resolve().parents[1]/'configs/video4-object-review.json').read_text())
  machine={'class':'person','confidence':.421,'bbox_xyxy':[19.4,80.3,91.2,265.5]}
  worker={'class':'person','confidence':.591,'bbox_xyxy':[261.4,80.1,335.5,226.5]}
  kept,rejected=exclude_confirmed_equipment([machine,worker],(1080,1920),profile)
  self.assertEqual(kept,[worker]);self.assertEqual(rejected[0]['equipment_region_id'],'presentation4_far_upper_left_machine')
 def test_partial_overlap_not_entire_walkway_mask(self):
  profile=json.loads((Path(__file__).resolve().parents[1]/'configs/video4-object-review.json').read_text())
  worker={'class':'person','confidence':.9,'bbox_xyxy':[70,100,160,350]}
  kept,_=exclude_confirmed_equipment([worker],(1080,1920),profile)
  self.assertEqual(kept,[worker])
