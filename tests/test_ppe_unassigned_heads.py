import unittest
from src.ppe_unassigned_heads import UnassignedHeadEvents
P={'minimum_consecutive_frames':3,'minimum_confirmed_seconds':.4,'maximum_observation_gap_seconds':.45,'minimum_head_confidence':.5}
def head(c):return {'class':c,'confidence':.9,'bbox_xyxy':[10,10,40,50]}
class HeadEvidenceTests(unittest.TestCase):
 def test_real_bare_head_warns_without_fake_person(self):
  rule=UnassignedHeadEvents(5,P)
  for t in [0,.2,.4]:events,_=rule.update(t,[head('no_helmet_head')],[],(300,300))
  self.assertEqual(events[0]['severity'],'WARNING');self.assertNotIn('person_bbox_xyxy',events[0]);self.assertEqual(events[0]['person_link_status'],'unconfirmed')
  missing,_=rule.update(.6,[],[],(300,300));self.assertTrue(all(e['severity'] is None for e in missing))
 def test_unlinked_helmet_never_safe(self):
  rule=UnassignedHeadEvents(5,P)
  for t in [0,.2,.4]:events,_=rule.update(t,[head('helmeted_head')],[],(300,300))
  self.assertTrue(all(e['severity'] is None for e in events))
 def test_conflict_not_forced_warning(self):
  rule=UnassignedHeadEvents(5,P)
  for t in [0,.2,.4]:events,_=rule.update(t,[head('helmeted_head'),head('no_helmet_head')],[],(300,300))
  self.assertTrue(all(e['severity'] is None for e in events))
 def test_owned_head_not_duplicated(self):
  rule=UnassignedHeadEvents(5,P);events,_=rule.update(0,[head('no_helmet_head')],[[0,0,60,200]],(300,300));self.assertFalse(events)

 def test_body_loss_retains_real_observed_head_history(self):
  rule=UnassignedHeadEvents(5,P)
  for t in [0,.2]:events,_=rule.update(t,[head('no_helmet_head')],[[0,0,60,200]],(300,300))
  self.assertFalse(events)
  events,_=rule.update(.4,[head('no_helmet_head')],[],(300,300))
  self.assertEqual(events[0]['severity'],'WARNING')
  self.assertNotIn('person_bbox_xyxy',events[0])

 def test_owned_head_warning_retains_continuity_when_body_id_changes(self):
  rule=UnassignedHeadEvents(5,{**P,'head_candidate_continuity':True})
  for t in [0,.2,.4]:events,_=rule.update(t,[head('no_helmet_head')],[[0,0,60,200]],(300,300),body_events=[])
  self.assertEqual(events[0]['severity'],'WARNING')
  duplicate,_=rule.update(.6,[head('no_helmet_head')],[[0,0,60,200]],(300,300),body_events=[{'severity':'WARNING','head_candidates':[head('no_helmet_head')]}])
  self.assertFalse(duplicate)
 def test_fast_weak_head_and_context_crop_retain_real_history(self):
  policy={**P,'head_candidate_continuity':True,'minimum_no_helmet_candidate_confidence':.25}
  rule=UnassignedHeadEvents(5,policy)
  boxes=[[255,576,328,636],[254,534,352,630],[277,494,368,588]]
  for i,(box,conf) in enumerate(zip(boxes,[.612,.379,.749])):
   heads=[{'class':'no_helmet_head','confidence':conf,'bbox_xyxy':box}]
   if i==1:heads.append({'class':'no_helmet_head','confidence':.631,'bbox_xyxy':[259,532,352,607],'source':'weak_head_context_recheck'})
   events,_=rule.update(i*.21,heads,[],(720,1280),body_events=[])
  self.assertTrue(any(e['severity']=='WARNING' for e in events))
