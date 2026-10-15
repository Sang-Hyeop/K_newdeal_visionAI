import unittest
from src.scenario_selection import review_video_numbers
class ScenarioSelectionTests(unittest.TestCase):
 def test_default_excludes_disabled_scenario(self):
  m={'scenarios':[{'video_number':n,'review_enabled':n!=6}for n in range(1,8)]}
  self.assertEqual(review_video_numbers(None,m),[1,2,3,4,5,7])
 def test_explicit_disabled_request_is_explained(self):
  with self.assertRaisesRegex(ValueError,'excluded by user'):review_video_numbers([6],{'scenarios':[{'video_number':6,'review_enabled':False}]})

class PresentationDirectoryTests(unittest.TestCase):
 def test_current_presentation_folders_keep_legacy_rules_separate(self):
  import json
  from pathlib import Path
  from src.scenario_selection import scenario_directory
  rows=json.loads((Path(__file__).resolve().parents[1]/'configs/demo-scenarios.json').read_text())['scenarios']
  actual={row['video_number']:scenario_directory(row) for row in rows if row.get('review_enabled',True)}
  self.assertEqual(actual,{2:'video1',4:'video4',5:'video3',7:'video5'})
 def test_unmapped_scenario_keeps_its_number(self):
  from src.scenario_selection import scenario_directory
  self.assertEqual(scenario_directory({'video_number':4}), 'video4')
