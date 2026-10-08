import unittest

from src.scenario_render import select_proximity_display_event


class ScenarioRenderTests(unittest.TestCase):
    def test_closer_ambiguous_pair_is_not_hidden_by_distant_safe_pair(self):
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

        selected = select_proximity_display_event([distant_safe, close_ambiguous])

        self.assertIs(selected, close_ambiguous)

    def test_no_pair_is_returned_without_geometry(self):
        self.assertIsNone(select_proximity_display_event([{'severity': None, 'reason': 'pair_not_observed'}]))


if __name__ == '__main__':
    unittest.main()
