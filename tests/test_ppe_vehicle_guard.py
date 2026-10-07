import unittest
from src.ppe_vehicle_guard import apply_ppe_vehicle_guard

class PPEVehicleGuardTests(unittest.TestCase):
    def event(self,severity='WARNING',box=None):
        return {'severity':severity,'observation_status':'confirmed','person_bbox_xyxy':box or [10,10,40,80],'ppe_state':'no_helmet_candidate'}
    def test_heavy_overlap_vetoes_safe(self):
        vehicle=[0,0,100,100]
        for state in ('SAFE',):
            out=apply_ppe_vehicle_guard([self.event(state)],[vehicle])[0]
            self.assertIsNone(out['severity'])
            self.assertEqual(out['reason'],'possible_operator_or_equipment_person_box')
    def test_heavy_overlap_keeps_warning_for_review(self):
        out=apply_ppe_vehicle_guard([self.event()],[[0,0,100,100]])[0]
        self.assertEqual(out['severity'],'WARNING')
        self.assertEqual(out['ppe_state'],'no_helmet_candidate')
        self.assertEqual(out['classification_status'],'unconfirmed')
        self.assertTrue(out['vehicle_overlap_review_required'])

    def test_partial_overlap_keeps_warning(self):
        out=apply_ppe_vehicle_guard([self.event(box=[80,10,120,80])],[[0,0,100,100]])[0]
        self.assertEqual(out['severity'],'WARNING')
    def test_does_not_mutate_input(self):
        source=self.event('SAFE');apply_ppe_vehicle_guard([source],[[0,0,100,100]])
        self.assertEqual(source['severity'],'SAFE')
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):apply_ppe_vehicle_guard([],[],minimum_overlap=0)
