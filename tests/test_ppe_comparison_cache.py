import importlib.util,json,unittest
from pathlib import Path
from src.ppe_events import PPEEvents
spec=importlib.util.spec_from_file_location('ppe_comparison',Path(__file__).resolve().parents[1]/'scripts/compare_ppe_video1.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ComparisonCacheTests(unittest.TestCase):
 def test_saved_tracks_replay_new_heads_instead_of_cached_old_class(self):
  old={'class':'helmeted_head','confidence':.9,'bbox_xyxy':[30,0,50,30],'model_sources':['baseline']}
  fresh={'class':'no_helmet_head','confidence':.8,'bbox_xyxy':[30,0,50,30],'model_sources':['baseline']}
  track={'track_id':'p','detected_bbox_xyxy':[0,0,100,200],'bbox_xyxy':[0,0,100,200],'ppe':{'head_candidates':[old],'state':'helmet_detected'}}
  row={'ppe_tracks':[track]};updated=m.assign_head_observations([track],[fresh],300)
  m.save_ppe_observations(row,updated,[fresh]);stored=json.loads(json.dumps(row))
  policy=json.loads((Path(__file__).resolve().parents[1]/'configs/ppe-user-approved-policy-2026-10-15.json').read_text())
  direct=PPEEvents(policy);replay=PPEEvents(policy)
  for t in [0,.2,.4]:
   expected,_=direct.update(t,updated);actual,_=replay.update(t,stored['ppe_tracks']);self.assertEqual(expected,actual)
  self.assertEqual(actual[0]['severity'],'WARNING')
  self.assertEqual(track['ppe']['head_candidates'],[old]);self.assertEqual(stored['ppe_tracks'][0]['ppe']['head_candidates'],[fresh])
 def test_serialized_observations_are_independent_of_later_mutation(self):
  heads=[{'class':'no_helmet_head','confidence':.8,'bbox_xyxy':[30,0,50,30]}]
  tracks=m.assign_head_observations([{'track_id':'p','detected_bbox_xyxy':[0,0,100,200]}],heads,300)
  row={};m.save_ppe_observations(row,tracks,heads);heads[0]['confidence']=.1;tracks[0]['ppe']['head_candidates'].clear()
  self.assertEqual(row['head_detections'][0]['confidence'],.8);self.assertEqual(len(row['ppe_tracks'][0]['ppe']['head_candidates']),1)
 def test_missing_ppe_tracks_can_be_rebuilt_from_observed_events(self):
  row={'ppe_tracks':[],'feature_events':{'ppe':[{'track_id':'present','person_bbox_xyxy':[0,0,10,20],'head_candidates':[]},{'track_id':'missing','reason':'person_not_observed'}]}}
  self.assertEqual([t['track_id']for t in m.tracks_from_row(row)],['present'])
