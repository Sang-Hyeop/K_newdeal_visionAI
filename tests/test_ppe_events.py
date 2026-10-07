import unittest
from src.ppe_events import PPEEvents
CFG=dict(minimum_consecutive_frames=3,minimum_confirmed_seconds=.4,maximum_observation_gap_seconds=.45,minimum_head_confidence=.5)
def track(state='helmet_detected',confidence=.9):
 cls='helmeted_head' if state=='helmet_detected' else 'no_helmet_head'
 return {'track_id':'p','bbox_xyxy':[10,10,80,200],'ppe':{'state':state,'head_candidates':[{'class':cls,'confidence':confidence,'bbox_xyxy':[20,10,50,40]}]}}
class PPEEventTests(unittest.TestCase):
 def test_three_frames_and_duration_required(self):
  r=PPEEvents(CFG)
  for t in [0,.2]:self.assertIsNone(r.update(t,[track()])[0][0]['severity'])
  self.assertEqual(r.update(.4,[track()])[0][0]['severity'],'SAFE')
 def test_three_fast_frames_not_enough_duration(self):
  r=PPEEvents(CFG)
  for t in [0,.05,.1]:e=r.update(t,[track()])[0][0]
  self.assertIsNone(e['severity'])
 def test_missing_breaks_confirmation(self):
  r=PPEEvents(CFG)
  for t in [0,.2,.4]:r.update(t,[track()])
  e=r.update(.6,[],[{'track_id':'p'}])[0][0];self.assertIsNone(e['severity']);self.assertNotIn('person_bbox_xyxy',e)
  self.assertIsNone(r.update(.8,[track()])[0][0]['severity'])
 def test_no_helmet_candidate_not_verified_violation(self):
  r=PPEEvents(CFG)
  for t in [0,.2,.4]:e=r.update(t,[track('no_helmet_candidate')])[0][0]
  self.assertEqual(e['severity'],'WARNING');self.assertEqual(e['violation_status'],'not_verified')
 def test_conflict_or_low_confidence_not_confirmed(self):
  for state,conf in [('conflicting_evidence',.9),('helmet_detected',.49)]:
   r=PPEEvents(CFG)
   for t in [0,.2,.4]:e=r.update(t,[track(state,conf)])[0][0]
   self.assertIsNone(e['severity'])
 def test_scene_cut_resets_confirmation(self):
  r=PPEEvents(CFG)
  for t in [0,.2,.4]:r.update(t,[track()])
  self.assertIsNone(r.update(.6,[track()],scene_cut=True)[0][0]['severity'])
if __name__=='__main__':unittest.main()
