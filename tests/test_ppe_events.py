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
 def test_optional_conflict_warns_without_classification_confirmation(self):
  r=PPEEvents(dict(CFG,conflicting_bare_head_policy='warning_candidate'))
  subject=track('conflicting_evidence');subject['ppe']['head_candidates'].append({'class':'helmeted_head','confidence':.9,'bbox_xyxy':[20,10,50,40]})
  for t in [0,.2,.4]:e=r.update(t,[subject])[0][0]
  self.assertEqual(e['severity'],'WARNING');self.assertEqual(e['ppe_state'],'conflicting_evidence');self.assertEqual(e['classification_status'],'unconfirmed');self.assertEqual(e['violation_status'],'not_verified')
 def test_optional_conflict_does_not_warn_without_strong_bare_head(self):
  r=PPEEvents(dict(CFG,conflicting_bare_head_policy='warning_candidate'))
  subject=track('conflicting_evidence',.3);subject['ppe']['head_candidates'].append({'class':'helmeted_head','confidence':.9,'bbox_xyxy':[20,10,50,40]})
  for t in [0,.2,.4]:e=r.update(t,[subject])[0][0]
  self.assertIsNone(e['severity'])
 def test_bare_evidence_continues_across_conflict_state_changes(self):
  r=PPEEvents(dict(CFG,conflicting_bare_head_policy='warning_candidate'))
  for t,state in [(0,'no_helmet_candidate'),(.2,'conflicting_evidence'),(.4,'no_helmet_candidate')]:e=r.update(t,[track(state)])[0][0]
  self.assertEqual(e['severity'],'WARNING')
 def test_sensitive_candidate_is_warning_only_not_confirmed_violation(self):
  cfg=dict(CFG,minimum_no_helmet_candidate_confidence=.25,conflicting_bare_head_policy='warning_candidate');r=PPEEvents(cfg)
  for t in [0,.2,.4]:e=r.update(t,[track('no_helmet_candidate',.3)])[0][0]
  self.assertEqual(e['severity'],'WARNING');self.assertEqual(e['classification_status'],'unconfirmed');self.assertEqual(e['violation_status'],'not_verified')
  self.assertIsNone(r.update(.6,[],[{'track_id':'p'}])[0][0]['severity'])
  r=PPEEvents(cfg)
  for t in [0,.2,.4]:e=r.update(t,[track('helmet_detected',.3)])[0][0]
  self.assertIsNone(e['severity'])
 def test_scene_cut_resets_confirmation(self):
  r=PPEEvents(CFG)
  for t in [0,.2,.4]:r.update(t,[track()])
  self.assertIsNone(r.update(.6,[track()],scene_cut=True)[0][0]['severity'])
if __name__=='__main__':unittest.main()
