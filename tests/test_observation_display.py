# 역할: 관측 근거와 배너 표시 동작을 회귀 검증합니다.
import unittest
from src.observation_display import event_display, display_summary
from src.feature_status import feature_status
from src.event_contract import normalize_event

class ObservationDisplayTests(unittest.TestCase):
    def event(self, **kw):
        return dict(event_type='ppe', timestamp_seconds=0, severity=None, observation_status='unconfirmed', **kw)
    def test_empty_is_not_safe_and_has_no_risk_alert(self):
        s=feature_status([])
        self.assertEqual(s['dashboard_state'],'no_observed_subjects')
        self.assertIsNone(s['severity']); self.assertEqual(s['risk_alert_count'],0)
    def test_pending_not_unassessable(self):
        self.assertEqual(event_display(self.event(reason='pending_temporal_confirmation'))['assessment_state'],'pending')
    def test_missing_pair_is_loss_not_safe(self):
        e=self.event(reason='pair_not_observed')
        self.assertEqual(event_display(e)['assessment_state'],'observation_lost')
        self.assertIsNone(feature_status([e])['severity'])
    def test_unresolved_head_never_alerts(self):
        e=self.event(reason='conflicting_or_missing_or_low_confidence_head')
        self.assertEqual(event_display(e)['assessment_state'],'unassessable')
        self.assertFalse(event_display(e)['alert_eligible'])
    def test_partial_coverage_keeps_risk_alert(self):
        e=self.event(); e.update(severity='WARNING',observation_status='confirmed')
        s=feature_status([e,self.event(reason='pair_not_observed')])
        self.assertEqual(s['severity'],'WARNING');self.assertEqual(s['risk_alert_count'],1)
        self.assertEqual(s['coverage'],'partial')
    def test_unconfirmed_severity_never_eligible(self):
        e=self.event();e['severity']='CRITICAL'
        self.assertFalse(event_display(e)['alert_eligible'])
    def test_export_exposes_routing_without_changing_verdict(self):
        e=self.event(reason='pending_temporal_confirmation')
        r=normalize_event(e,camera_id='c',video='v',source_sha256='s',model_version='m',config_version='c')
        self.assertEqual(r['assessment_state'],'pending');self.assertIsNone(r['severity'])
        self.assertEqual(r['notification_category'],'status')

    def test_empty_transition_is_not_an_unassessable_person(self):
        e=self.event(reason='no_observed_subject_pair_or_person')
        self.assertEqual(event_display(e)['assessment_state'],'no_observed_subjects')
        self.assertFalse(event_display(e)['alert_eligible'])
