# 역할: 시간 창 안전모 판정 동작을 회귀 검증합니다.
import unittest,json
from pathlib import Path
from src.ppe_events import PPEEvents
CFG=json.loads((Path(__file__).resolve().parents[1]/'configs/ppe-user-approved-policy-2026-10-15.json').read_text())
def tr(cls='no_helmet_head',conf=.9,key='p'):
 return {'track_id':key,'bbox_xyxy':[0,0,100,200],'ppe':{'state':'unknown','head_candidates':[] if cls is None else [{'class':cls,'confidence':conf,'model_sources':['baseline'],'bbox_xyxy':[20,10,50,50]}]}}
class WindowTests(unittest.TestCase):
 def run_votes(self,rule,values):
  for t,c in values:e=rule.update(t,[tr(c)])[0][0]
  return e
 def test_three_votes_not_consecutive(self):
  r=PPEEvents(CFG);e=self.run_votes(r,[(0,'no_helmet_head'),(.2,None),(.4,'no_helmet_head'),(.6,'no_helmet_head')]);self.assertEqual(e['severity'],'WARNING')
 def test_hold_expiry(self):
  r=PPEEvents(CFG);self.run_votes(r,[(0,'helmeted_head'),(.2,'helmeted_head'),(.4,'helmeted_head')]);e=r.update(1.,[tr(None)])[0][0];self.assertEqual(e['severity'],'SAFE');self.assertTrue(e['observation_held']);self.assertIsNone(r.update(1.01,[tr(None)])[0][0]['severity'])
 def test_opposite_cancels_and_cannot_restore_without_new_support(self):
  r=PPEEvents(CFG);self.run_votes(r,[(0,'helmeted_head'),(.2,'helmeted_head'),(.4,'helmeted_head')]);self.assertIsNone(r.update(.6,[tr('no_helmet_head')])[0][0]['severity']);self.assertIsNone(r.update(.8,[tr(None)])[0][0]['severity'])
 def test_ratio_requires_75percent(self):
  r=PPEEvents(CFG);e=self.run_votes(r,[(0,'helmeted_head'),(.2,'no_helmet_head'),(.4,'no_helmet_head')]);self.assertIsNone(e['severity']);self.assertEqual(r.update(.6,[tr('no_helmet_head')])[0][0]['severity'],'WARNING')
 def test_thresholds(self):
  for cls,c in [('helmeted_head',.39),('no_helmet_head',.29)]:
   r=PPEEvents(CFG)
   for t in [0,.2,.4]:e=r.update(t,[tr(cls,c)])[0][0]
   self.assertIsNone(e['severity'])
 def test_cut_and_identity_reset(self):
  r=PPEEvents(CFG);self.run_votes(r,[(0,'helmeted_head'),(.2,'helmeted_head'),(.4,'helmeted_head')]);self.assertIsNone(r.update(.6,[tr('helmeted_head',key='new')])[0][0]['severity']);self.assertIsNone(r.update(.8,[tr('helmeted_head',key='new')],scene_cut=True)[0][0]['severity'])
 def test_missing_body_no_stale_hold(self):
  r=PPEEvents(CFG);self.run_votes(r,[(0,'helmeted_head'),(.2,'helmeted_head'),(.4,'helmeted_head')]);e=r.update(.6,[],[{'track_id':'p'}])[0][0];self.assertIsNone(e['severity']);self.assertNotIn('person_bbox_xyxy',e);self.assertIsNone(r.update(.8,[tr('helmeted_head')])[0][0]['severity'])
 def test_old_votes_expire(self):
  r=PPEEvents(CFG);self.run_votes(r,[(0,'helmeted_head'),(.2,'helmeted_head')]);self.assertIsNone(r.update(1.3,[tr('helmeted_head')])[0][0]['severity'])
 def test_same_frame_conflict_not_safe(self):
  r=PPEEvents(CFG);v=tr('helmeted_head');v['ppe']['head_candidates']+=tr('no_helmet_head')['ppe']['head_candidates']
  for t in [0,.2,.4]:e=r.update(t,[v])[0][0]
  self.assertIsNone(e['severity'])
