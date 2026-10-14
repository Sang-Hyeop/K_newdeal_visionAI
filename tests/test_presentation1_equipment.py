import json, unittest
from pathlib import Path
from src.detection_review_profile import exclude_confirmed_equipment

class PresentationEquipmentTests(unittest.TestCase):
 def setUp(self):
  self.profile=json.loads((Path(__file__).resolve().parents[1]/'configs/video2-object-review.json').read_text())
 def proposal(self,cls,box):return {'class':cls,'confidence':.9,'bbox_xyxy':box}
 def test_machine_person_and_head_rejected(self):
  for cls,box in [('person',[1113,138,1193,391]),('no_helmet_head',[1130,145,1170,178])]:
   kept,rejected=exclude_confirmed_equipment([self.proposal(cls,box)],(1080,1920),self.profile)
   self.assertFalse(kept);self.assertEqual(len(rejected),1)
 def test_storage_rejected_but_real_moving_vehicle_retained(self):
  fake=self.proposal('forklift',[0,110,237,465]);real=self.proposal('forklift',[162,25,379,349])
  kept,rejected=exclude_confirmed_equipment([fake,real],(1080,1920),self.profile)
  self.assertEqual(kept,[real]);self.assertEqual(len(rejected),1)
 def test_storage_person_is_not_excluded(self):
  person=self.proposal('person',[30,120,80,300]);kept,_=exclude_confirmed_equipment([person],(1080,1920),self.profile)
  self.assertEqual(kept,[person])
 def test_partial_overlap_walker_not_excluded(self):
  person=self.proposal('person',[1080,120,1170,400]);kept,_=exclude_confirmed_equipment([person],(1080,1920),self.profile)
  self.assertEqual(kept,[person])
