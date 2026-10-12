import unittest

from src.scenario_render import exclude_driver_overlap_pairs, select_ppe_review_candidates, select_proximity_display_events


class ScenarioRenderTests(unittest.TestCase):
    def test_near_unknown_is_not_hidden_by_distant_safe_pair(self):
        distant_safe = {
            'observation_status': 'confirmed', 'severity': 'SAFE',
            'person_anchor_xy': [100, 200], 'nearest_vehicle_point_xy': [500, 200],
            'normalized_image_gap': 2.4,
        }
        close_ambiguous = {
            'observation_status': 'unconfirmed', 'severity': None,
            'reason': 'possible_operator_or_occluded_person',
            'person_anchor_xy': [100, 200], 'nearest_vehicle_point_xy': [105, 200],
            'normalized_image_gap': 0.03,
        }

        selected = select_proximity_display_events([distant_safe, close_ambiguous])

        self.assertEqual(selected, [close_ambiguous])

    def test_all_dangerous_people_pairs_are_selected(self):
        events = [
            {'person_track_id': 'p1', 'observation_status': 'confirmed', 'severity': 'CRITICAL', 'normalized_image_gap': .3, 'person_anchor_xy': [1, 1], 'nearest_vehicle_point_xy': [2, 2]},
            {'person_track_id': 'p2', 'observation_status': 'confirmed', 'severity': 'CRITICAL', 'normalized_image_gap': .4, 'person_anchor_xy': [3, 3], 'nearest_vehicle_point_xy': [4, 4]},
            {'person_track_id': 'p3', 'observation_status': 'confirmed', 'severity': 'SAFE', 'normalized_image_gap': 2.2, 'person_anchor_xy': [5, 5], 'nearest_vehicle_point_xy': [6, 6]},
        ]

        self.assertEqual(select_proximity_display_events(events), events[:2])

    def test_safe_fallback_shows_one_nearest_pair_per_person(self):
        events = [
            {'person_track_id': 'p1', 'observation_status': 'confirmed', 'severity': 'SAFE', 'normalized_image_gap': 2.0, 'person_anchor_xy': [1, 1], 'nearest_vehicle_point_xy': [2, 2]},
            {'person_track_id': 'p1', 'observation_status': 'confirmed', 'severity': 'SAFE', 'normalized_image_gap': 1.8, 'person_anchor_xy': [1, 1], 'nearest_vehicle_point_xy': [3, 3]},
            {'person_track_id': 'p2', 'observation_status': 'confirmed', 'severity': 'SAFE', 'normalized_image_gap': 2.1, 'person_anchor_xy': [4, 4], 'nearest_vehicle_point_xy': [5, 5]},
        ]

        self.assertEqual(select_proximity_display_events(events), [events[1], events[2]])

    def test_conflicting_ppe_candidates_are_preserved_but_duplicates_collapsed(self):
        event = {'head_candidates': [
            {'class': 'helmeted_head', 'confidence': .93, 'bbox_xyxy': [10, 10, 30, 30]},
            {'class': 'helmeted_head', 'confidence': .8, 'bbox_xyxy': [10, 10, 30, 30]},
            {'class': 'no_helmet_head', 'confidence': .89, 'bbox_xyxy': [10, 10, 30, 30]},
        ]}

        candidates = select_ppe_review_candidates([event])

        self.assertEqual({item['class'] for _, item in candidates}, {'helmeted_head', 'no_helmet_head'})
        self.assertEqual(len(candidates), 2)

    def test_person_mostly_inside_forklift_box_is_excluded_from_display_pairs(self):
        driver = {
            'person_track_id': 'p-driver', 'observation_status': 'unconfirmed',
            'severity': None, 'normalized_image_gap': .2,
            'person_anchor_xy': [50, 90], 'nearest_vehicle_point_xy': [50, 90],
            'person_bbox_xyxy': [40, 40, 60, 90], 'forklift_bbox_xyxy': [0, 0, 100, 100],
        }
        pedestrian = {
            'person_track_id': 'p-worker', 'observation_status': 'confirmed',
            'severity': 'CRITICAL', 'normalized_image_gap': .3,
            'person_anchor_xy': [130, 90], 'nearest_vehicle_point_xy': [150, 90],
            'person_bbox_xyxy': [110, 40, 140, 90], 'forklift_bbox_xyxy': [0, 0, 100, 100],
        }

        self.assertEqual(exclude_driver_overlap_pairs([driver, pedestrian]), [pedestrian])
        self.assertEqual(select_proximity_display_events([driver, pedestrian]), [pedestrian])


if __name__ == '__main__':
    unittest.main()

class LaneOverlayScopeTests(unittest.TestCase):
 def test_only_monitored_lane_is_colored_and_unknown_is_neutral(self):
  import numpy as np
  from src.scenario_render import roi_overlay
  outer=np.array([[2,2],[98,2],[98,98],[2,98]],np.float32)
  excluded=np.array([[20,20],[40,20],[40,40],[20,40]],np.float32)
  for severity in ['SAFE','WARNING','CRITICAL',None]:
   image=np.full((100,100,3),100,np.uint8);roi_overlay(image,outer,[excluded],severity)
   self.assertTrue(np.array_equal(image[30,30],[100,100,100]))
   if severity is None:self.assertEqual(len(set(image[60,60].tolist())),1)
   else:self.assertGreater(len(set(image[60,60].tolist())),1)
