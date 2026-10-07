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
