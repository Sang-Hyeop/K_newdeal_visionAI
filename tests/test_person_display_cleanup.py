import unittest
from unittest.mock import patch
import numpy as np
from src.person_display_cleanup import deduplicate_people,draw_compact_people

def person(box,source,confidence=.9):return dict(bbox_xyxy=box,model_source=source,confidence=confidence,**{'class':'person'})
class CleanupTests(unittest.TestCase):
 def test_reviewed_duplicate_removed(self):
  a=person([251,33,340,228],'adaptation');b=person([247,98,291,235],'coco',.36)
  kept,rejected=deduplicate_people([b,a]);self.assertEqual(kept,[a]);self.assertEqual(len(rejected),1)
 def test_adjacent_people_preserved(self):
  people=[person([250,30,340,230],'a'),person([310,30,400,230],'b')]
  self.assertEqual(len(deduplicate_people(people)[0]),2)
 def test_depth_overlap_with_different_feet_preserved(self):
  people=[person([250,30,340,230],'a'),person([255,30,330,150],'b')]
  self.assertEqual(len(deduplicate_people(people)[0]),2)
 def test_same_model_and_unknown_source_preserved(self):
  for source in ['a',None]:self.assertEqual(len(deduplicate_people([person([0,0,100,200],'a'),person([0,0,100,200],source)])[0]),2)
 def test_render_draws_one_body_without_head_or_zone_rectangle(self):
  d=person([10,100,100,250],'a');events=[dict(person_bbox_xyxy=d['bbox_xyxy'],severity='WARNING',observation_status='confirmed',inside=True,observed_dwell_seconds=4)]
  with patch('src.person_display_cleanup.cv2.rectangle') as rectangles:
   draw_compact_people(np.zeros((300,400,3),np.uint8),[d],dict(zone_dwell=events,ppe=[]))
  self.assertEqual(rectangles.call_count,1)
