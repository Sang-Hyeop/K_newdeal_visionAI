import unittest
from src.ppe_vehicle_guard import apply_ppe_vehicle_guard
from src.event_contract import normalize_event
from src.feature_status import feature_status

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

    def test_overlap_warning_survives_public_contract_and_banner(self):
        source=dict(self.event(),event_type='ppe',timestamp_seconds=1,track_id='person1')
        event=apply_ppe_vehicle_guard([source],[[0,0,100,100]])[0]
        public=normalize_event(event,camera_id='test',video='test.mp4',source_sha256='source',model_version='model',config_version='config')
        self.assertEqual(public['severity'],'WARNING')
        self.assertEqual(public['evidence']['classification_status'],'unconfirmed')
        self.assertTrue(public['evidence']['vehicle_overlap_review_required'])
        self.assertEqual(feature_status([event])['display_state'],'WARNING')

    def test_unobserved_warning_is_not_promoted(self):
        source=dict(self.event(),observation_status='unconfirmed')
        out=apply_ppe_vehicle_guard([source],[[0,0,100,100]])[0]
        self.assertEqual(feature_status([out])['display_state'],'UNKNOWN')

    def test_partial_overlap_keeps_warning(self):
        out=apply_ppe_vehicle_guard([self.event(box=[80,10,120,80])],[[0,0,100,100]])[0]
        self.assertEqual(out['severity'],'WARNING')
    def test_does_not_mutate_input(self):
        source=self.event('SAFE');apply_ppe_vehicle_guard([source],[[0,0,100,100]])
        self.assertEqual(source['severity'],'SAFE')
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):apply_ppe_vehicle_guard([],[],minimum_overlap=0)
