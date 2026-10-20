"""Operational reports count cases, preserve unknowns and use operator clocks."""
import unittest
from datetime import datetime
from dashboard.config import build_tabs
from dashboard.operations import operational_metrics

class OperationsTests(unittest.TestCase):
    def test_navigation_roles(self):
        tabs=build_tabs()
        self.assertEqual([t['name'] for t in tabs if t['kind'] not in ('main','camera')], ['경보·조치 관리','이벤트 이력','운영 통계'])
        self.assertEqual(len({t['id'] for t in tabs}), len(tabs))

    def test_counts_unique_cases_not_observations(self):
        case=dict(link_key='one',status='acting',cam_id='A1',scenario='collision',related_count=500,opened_at='2026-10-19 10:00:00')
        result=operational_metrics([case,case,dict(case,link_key='two',status='done')])
        self.assertEqual(result['total'],2)
        self.assertEqual(result['unfinished'],1)
        self.assertEqual(result['features']['collision'],2)
        self.assertIsNone(result['mean_ack_seconds'])

    def test_elapsed_uses_server_clocks_and_excludes_invalid(self):
        cases=[dict(link_key='one',status='done',opened_at='2026-10-19 10:00:00',event_first_clock='09:00:01'),dict(link_key='two',status='new',opened_at='invalid')]
        history={'one':[dict(next_status='acked',operator_at='2026-10-19 10:01:00'),dict(next_status='done',operator_at='2026-10-19 10:03:00')]}
        result=operational_metrics(cases,histories=history)
        self.assertEqual(result['mean_ack_seconds'],60)
        self.assertEqual(result['mean_done_seconds'],180)
        self.assertEqual(result['done_samples'],1)

    def test_registration_period_is_not_video_date(self):
        cases=[dict(link_key='one',opened_at='2026-10-18 12:00:00'),dict(link_key='two',opened_at='2026-10-18 12:00:00',observed_dates=['2026-10-19']),dict(link_key='unknown')]
        result=operational_metrics(cases,'오늘 등록',now=datetime(2026,10,19))
        self.assertEqual(result['total'],1)

    def test_today_requires_playback_observation_not_operator_action(self):
        cases=[dict(link_key='old',opened_at='2026-10-18 09:00:00',observed_dates=['2026-10-20']),
               dict(link_key='manual',opened_at='2026-10-20 09:00:00')]
        result=operational_metrics(cases,'오늘 등록',now=datetime(2026,10,20))
        self.assertEqual(result['total'],1)

    def test_daily_observation_deduplicates_and_survives_reload(self):
        import tempfile
        from unittest.mock import patch
        from dashboard import alert_response as ar
        with tempfile.TemporaryDirectory() as tmp, patch.object(ar,'LOCAL',tmp), patch.object(ar,'_now',return_value='2026-10-20 10:00:00'):
            ar.reset_response_memory()
            st=ar.ensure_case(dict(link_key='camera|case',assigned_to='담당자 A'))
            ar.record_observation_day('camera|case')
            ar.record_observation_day('camera|case')
            self.assertEqual(sum(r.get('kind')=='observation_day' for r in ar.iter_history()),1)
            ar.reset_response_memory(); ar.load_logs_into_memory()
            self.assertEqual(ar.get_state_by_link('camera|case')['state']['observed_dates'],['2026-10-20'])
            ar.reset_response_memory()
