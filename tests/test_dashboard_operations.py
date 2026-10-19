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
        cases=[dict(link_key='one',opened_at='2026-10-18 12:00:00'),dict(link_key='two',opened_at='2026-10-19 12:00:00'),dict(link_key='unknown')]
        result=operational_metrics(cases,'오늘 등록',now=datetime(2026,10,19))
        self.assertEqual(result['total'],1)
