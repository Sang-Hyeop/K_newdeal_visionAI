# 역할: 확정 안전모 정책·관측 저장·문맥 탐색 동작을 회귀 검증합니다.
import importlib.util,json,unittest
from pathlib import Path
from src.ppe_events import PPEEvents
from src import ppe_runtime as m

class RuntimeCacheTests(unittest.TestCase):
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

class ConservativeHelmetGuardTests(unittest.TestCase):
 def test_upper_crop_helmet_alone_cannot_create_safe(self):
  head={'class':'helmeted_head','confidence':.95,'bbox_xyxy':[30,0,50,30],'source':'experimental_v6_upper_body','model_sources':['baseline']}
  kept,blocked=m.conservative_extra_heads([],[head]);self.assertEqual(kept,[]);self.assertEqual(blocked,[head])
  policy=json.loads((Path(__file__).resolve().parents[1]/'configs/ppe-user-approved-policy-2026-10-15.json').read_text());rule=PPEEvents(policy)
  tracks=m.assign_head_observations([{'track_id':'hood','detected_bbox_xyxy':[0,0,100,200],'bbox_xyxy':[0,0,100,200]}],kept,300)
  for t in [0,.2,.4,.6]:events,_=rule.update(t,tracks)
  self.assertIsNone(events[0]['severity'])
 def test_existing_helmet_and_new_bare_head_evidence_are_preserved(self):
  original={'class':'helmeted_head','confidence':.8,'source':'final_v6_full_frame','bbox_xyxy':[10,10,20,20]}
  bare={'class':'no_helmet_head','confidence':.8,'source':'experimental_v6_upper_body','bbox_xyxy':[30,10,40,20]}
  kept,blocked=m.conservative_extra_heads([original],[original,bare]);self.assertEqual(kept,[original,bare]);self.assertEqual(blocked,[])

class RuntimePresentationDisplayTests(unittest.TestCase):
 def test_ppe_video_hides_legacy_cached_forklift_boxes(self):
  objects=[{'class':'person'},{'class':'forklift'}]
  self.assertEqual(m.display_detections(3,objects),[{'class':'person'}])
  self.assertEqual(objects,[{'class':'person'},{'class':'forklift'}])
 def test_integrated_video_keeps_people_and_vehicles(self):
  objects=[{'class':'person'},{'class':'forklift'}]
  self.assertEqual(m.display_detections(5,objects),objects)

class FixedContextRuntimeTests(unittest.TestCase):
 def infer(self,video,extra):
  import numpy as np
  from types import SimpleNamespace
  from unittest.mock import patch,Mock
  model=SimpleNamespace(model=SimpleNamespace(names={0:'helmeted_head',1:'no_helmet_head'}),predict_upper_body_context=Mock(return_value=[]),predict_fixed_context=Mock(return_value=extra))
  config={'guarded_upper_body_videos':[5],'fixed_context_videos':[5]}
  policy={'helmet_evidence_confidence':.4,'no_helmet_evidence_confidence':.3}
  with patch.object(m,'runtime_config',return_value=config),patch.object(m,'detect_current_heads',return_value=[]):
   heads,blocked=m.infer_runtime_heads(model,np.zeros((400,400,3),dtype=np.uint8),[[100,100,200,300]],policy,None,video)
  return heads,blocked,model
 def test_fixed_context_helmet_is_blocked_and_bare_head_retained(self):
  raw=[{'class':0,'confidence':.9,'box':[130,100,150,125]},{'class':1,'confidence':.8,'box':[130,100,150,125]}]
  heads,blocked,_=self.infer(5,raw)
  self.assertEqual([h['class']for h in heads],['no_helmet_head'])
  self.assertEqual([h['class']for h in blocked],['helmeted_head'])
 def test_fixed_context_cannot_assign_outside_person_head_region(self):
  heads,blocked,_=self.infer(5,[{'class':1,'confidence':.95,'box':[300,300,320,320]}])
  self.assertEqual(heads,[]);self.assertEqual(blocked,[])
 def test_ppe_only_video_does_not_run_additional_context(self):
  heads,blocked,model=self.infer(3,[])
  model.predict_fixed_context.assert_not_called();model.predict_upper_body_context.assert_not_called()

class RuntimeVersionScopeTests(unittest.TestCase):
 def test_only_integrated_video_gets_new_cache_version(self):
  self.assertEqual(m.runtime_version(2),m.runtime_version())
  self.assertEqual(m.runtime_version(3),m.runtime_version())
  self.assertNotEqual(m.runtime_version(5),m.runtime_version())

class ContextSearchCascadeTests(unittest.TestCase):
 def run_search(self,first,requires_head_candidate=False):
  import numpy as np
  from types import SimpleNamespace
  from unittest.mock import Mock,patch
  bare={'class':1,'confidence':.8,'box':[130,100,150,125]}
  model=SimpleNamespace(model=SimpleNamespace(names={0:'helmeted_head',1:'no_helmet_head'}),predict_upper_body_context=Mock(return_value=[]),predict_fixed_context=Mock(side_effect=[first,[bare]]))
  cfg={'guarded_upper_body_videos':[5],'fixed_context_videos':[5],'fixed_context_search':[{'context_size':320,'imgsz':640,'source':'v6_fixed_context'},{'context_size':480,'imgsz':960,'source':'v6_wide_context','requires_head_candidate':requires_head_candidate}]}
  with patch.object(m,'runtime_config',return_value=cfg),patch.object(m,'detect_current_heads',return_value=[]):
   heads,blocked=m.infer_runtime_heads(model,np.zeros((600,600,3),dtype=np.uint8),[[100,100,200,300]],{'helmet_evidence_confidence':.4,'no_helmet_evidence_confidence':.3},None,5)
  return heads,blocked,model
 def test_valid_first_pass_skips_more_expensive_second_pass(self):
  heads,_,model=self.run_search([{'class':1,'confidence':.8,'box':[130,100,150,125]}])
  self.assertEqual(model.predict_fixed_context.call_count,1);self.assertEqual(heads[0]['source'],'v6_fixed_context')
 def test_unresolved_first_pass_uses_wider_context(self):
  heads,_,model=self.run_search([])
  self.assertEqual(model.predict_fixed_context.call_count,2);self.assertEqual(heads[0]['source'],'v6_wide_context')
  self.assertEqual(model.predict_fixed_context.call_args.kwargs,{'context_size':480,'imgsz':960})
 def test_crop_only_helmet_cannot_skip_search_as_safe(self):
  heads,blocked,model=self.run_search([{'class':0,'confidence':.99,'box':[130,100,150,125]}])
  self.assertEqual(model.predict_fixed_context.call_count,2);self.assertEqual(blocked[0]['class'],'helmeted_head');self.assertEqual(heads[0]['class'],'no_helmet_head')

 def test_wide_search_skips_people_with_no_head_evidence(self):
  heads,blocked,model=self.run_search([],requires_head_candidate=True)
  self.assertEqual(model.predict_fixed_context.call_count,1);self.assertEqual(heads,[])
 def test_wide_search_rechecks_low_confidence_head(self):
  heads,blocked,model=self.run_search([{'class':1,'confidence':.2,'box':[130,100,150,125]}],requires_head_candidate=True)
  self.assertEqual(model.predict_fixed_context.call_count,2);self.assertEqual(heads[-1]['source'],'v6_wide_context')
