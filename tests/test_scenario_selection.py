# 역할: 영상 번호·캐시·기능 선택 동작을 회귀 검증합니다.
import unittest
from src.scenario_selection import review_video_numbers


class ScenarioSelectionTests(unittest.TestCase):
 def test_default_includes_active_presentation_videos(self):
  m={'scenarios':[{'video_number':n} for n in range(1,6)]}
  self.assertEqual(review_video_numbers(None,m),[1,2,3,4,5])
 def test_explicit_disabled_request_is_explained(self):
  with self.assertRaisesRegex(ValueError,'excluded by user'):review_video_numbers([6],{'scenarios':[{'video_number':6,'review_enabled':False}]})


class PresentationDirectoryTests(unittest.TestCase):
 def test_presentation_folders_match_video_numbers(self):
  import json
  from pathlib import Path
  from src.scenario_selection import scenario_directory
  rows=json.loads((Path(__file__).resolve().parents[1]/'configs/demo-scenarios.json').read_text())['scenarios']
  actual={row['video_number']:scenario_directory(row) for row in rows if row.get('review_enabled',True)}
  self.assertEqual(actual,{1:'video1',2:'video2',3:'video3',4:'video4',5:'video5'})
 def test_unmapped_scenario_keeps_its_number(self):
  from src.scenario_selection import scenario_directory
  self.assertEqual(scenario_directory({'video_number':4}), 'video4')


class FeatureSelectionTests(unittest.TestCase):
 def test_removed_features_do_not_reach_display_or_logs(self):
  from src.scenario_selection import presentation_groups,presentation_detections
  spec={'enabled_features':['zone_dwell']}
  self.assertEqual(presentation_groups({'ppe':[1],'zone_access':[2],'zone_dwell':[3]},spec),{'zone_dwell':[3]})
  self.assertEqual(presentation_detections([{'class':'person'},{'class':'forklift'}],spec),[{'class':'person'}])
 def test_all_features_preserve_objects_and_events(self):
  from src.scenario_selection import presentation_groups,presentation_detections
  spec={'enabled_features':['proximity','zone_access','zone_dwell','ppe']}
  groups={'proximity':[],'zone_access':[],'zone_dwell':[],'ppe':[]}
  objects=[{'class':'person'},{'class':'forklift'}]
  self.assertEqual(presentation_groups(groups,spec),groups)
  self.assertEqual(presentation_detections(objects,spec),objects)


class CacheFeatureScopeTests(unittest.TestCase):
 def test_disabled_ppe_allows_new_ppe_weights(self):
  from src.scenario_selection import cache_model_hashes_match
  self.assertTrue(cache_model_hashes_match({'objects':'same','ppe':'old'},{'objects':'same','ppe':'new'},False,'ppe'))
 def test_enabled_ppe_rejects_old_head_cache(self):
  from src.scenario_selection import cache_model_hashes_match
  self.assertFalse(cache_model_hashes_match({'objects':'same','ppe':'old'},{'objects':'same','ppe':'new'},True,'ppe'))
 def test_disabled_ppe_still_requires_identical_object_model(self):
  from src.scenario_selection import cache_model_hashes_match
  self.assertFalse(cache_model_hashes_match({'objects':'old','ppe':'old'},{'objects':'new','ppe':'new'},False,'ppe'))
