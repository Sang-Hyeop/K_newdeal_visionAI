import unittest
from src.detection_review_profile import exclude_confirmed_equipment
class ConfirmedEquipmentTests(unittest.TestCase):
 def test_only_confirmed_left_equipment_is_removed(self):
  profile={'confirmed_equipment_regions':[{'bbox_normalized':[170/1920,90/1080,245/1920,220/1080],'excluded_classes':['person','helmeted_head','no_helmet_head']}]}
  objects=[{'class':'person','bbox_xyxy':[180,133,217,195]},{'class':'no_helmet_head','bbox_xyxy':[198,117,222,144]},{'class':'person','bbox_xyxy':[258,68,320,218]},{'class':'no_helmet_head','bbox_xyxy':[270,70,290,95]}]
  kept,rejected=exclude_confirmed_equipment(objects,(1080,1920),profile)
  self.assertEqual(kept,objects[2:]);self.assertEqual(len(rejected),2)
 def test_other_camera_without_confirmed_region_unchanged(self):
  p=[{'class':'person','bbox_xyxy':[180,133,217,195]}]
  self.assertEqual(exclude_confirmed_equipment(p,(1080,1920),{}),(p,[]))
 def test_reference_profile_requires_current_image_before_exclusion(self):
  import json
  from pathlib import Path
  profile=json.loads((Path(__file__).resolve().parents[1]/'configs/video4-object-review.json').read_text())
  proposals=[{'class':'person','bbox_xyxy':[181.9,111.2,266.7,250.5]},{'class':'person','bbox_xyxy':[258,68,320,218]}]
  kept,rejected=exclude_confirmed_equipment(proposals,(1080,1920),profile)
  self.assertEqual(kept,proposals);self.assertEqual(rejected,[])
 def test_manual_source_does_not_regenerate_equipment_person(self):
  import json,ast
  from pathlib import Path
  root=Path(__file__).resolve().parents[1]
  for row in json.loads((root/'configs/review/demo-adaptation-v1.json').read_text()):
   if row['source']!='4_hazard_zone_dwell.mp4':continue
   w,h=row['coordinate_reference']
   for cls,x1,y1,x2,y2 in row['boxes_xyxy']:
    cx=(x1+x2)*960/w;cy=(y1+y2)*540/h
    self.assertFalse(cls==0 and 170<cx<245 and 90<cy<215)
  tree=ast.parse((root/'scripts/prepare_full_scene_expansion.py').read_text())
  manual=next(ast.literal_eval(node.value)for node in tree.body if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='MANUAL'for t in node.targets))
  for name,boxes in manual.items():
   if not name.startswith(('source2_','source3_')):continue
   for cls,x1,y1,x2,y2 in boxes:self.assertFalse(cls==0 and 170<(x1+x2)<245 and 90<(y1+y2)<215)
