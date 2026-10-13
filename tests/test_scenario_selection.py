import unittest
from src.scenario_selection import review_video_numbers
class ScenarioSelectionTests(unittest.TestCase):
 def test_default_excludes_disabled_scenario(self):
  m={'scenarios':[{'video_number':n,'review_enabled':n!=6}for n in range(1,8)]}
  self.assertEqual(review_video_numbers(None,m),[1,2,3,4,5,7])
 def test_explicit_disabled_request_is_explained(self):
  with self.assertRaisesRegex(ValueError,'excluded by user'):review_video_numbers([6],{'scenarios':[{'video_number':6,'review_enabled':False}]})
