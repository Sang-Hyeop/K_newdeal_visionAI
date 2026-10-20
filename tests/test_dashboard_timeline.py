# 역할: 시각 정밀도·일시정지·탐색·반복 재생 동작을 회귀 검증합니다.
"""시각 정밀도·일시정지·탐색·반복 재생 동작을 회귀 검증합니다."""
import unittest
import pandas as pd
from dashboard.config import clock_start
from dashboard.events import live_until, live_positions
from dashboard.ui import _time_bin_labels
from dashboard.timeline import event_seconds


class DashboardTimelineTests(unittest.TestCase):
    def fixture(self):
        base=clock_start().strftime('%Y-%m-%d %H:%M:')
        return pd.DataFrame([
            {'timestamp':base+'01','area':'A1','scenario':'collision','grade':'주의','status':'주의','worker':'작업자 A','event_id':'a'},
            {'timestamp':base+'04.0','area':'P1','scenario':'fire','grade':'미확인','status':'확인 중','worker':'불꽃','event_id':'b'},
            {'timestamp':base+'04.6','area':'P1','scenario':'fire','grade':'위험','status':'화재 의심','worker':'불꽃','event_id':'c'},
            {'timestamp':base+'08.8','area':'P1','scenario':'fire','grade':'위험','status':'화재 의심','worker':'불꽃','event_id':'d'},
            {'timestamp':'invalid','area':'P1','scenario':'fire','grade':'미확인','status':'판정 불가','worker':'불꽃','event_id':'bad'},
        ])

    def test_mixed_precision_has_no_future_or_invalid_events(self):
        d=self.fixture()
        self.assertEqual(len(live_until(d,.1)),0)
        self.assertEqual(list(live_until(d,4.5).event_id),['a','b'])
        self.assertEqual(list(live_until(d,4.6).event_id),['a','b','c'])
        self.assertNotIn('bad',live_until(d,100).event_id.values)

    def test_independent_cameras_pause_seek_and_loop(self):
        d=self.fixture()
        def ids(pos):return list(live_positions(d,pos).event_id)
        self.assertEqual(ids({'A1':10,'P1':.1}),['a'])
        self.assertEqual(ids({'P1':5}),['b','c'])
        self.assertEqual(ids({'P1':5}),['b','c'])  # unchanged while paused
        self.assertEqual(ids({'P1':9}),['b','c','d'])
        self.assertEqual(ids({'P1':2}),[])  # seek backward
        self.assertEqual(ids({'P1':0}),[])  # loop/restart
        self.assertEqual(ids({}),[])  # media not ready

    def test_cached_events_keep_video_seconds_after_calendar_rollover(self):
        from datetime import timedelta
        d = self.fixture()
        original = event_seconds(d)
        valid = d.timestamp != 'invalid'
        d.loc[valid, 'timestamp'] = (
            pd.to_datetime(d.loc[valid, 'timestamp'], format='ISO8601')
            - timedelta(days=1)
        ).astype(str)
        pd.testing.assert_series_equal(event_seconds(d), original)
        self.assertEqual(list(live_positions(d, {'A1': 10, 'P1': 5}).event_id), ['a', 'b', 'c'])

    def test_statistics_accept_mixed_precision_and_unknown_time(self):
        d=self.fixture()
        self.assertEqual(_time_bin_labels(d).iloc[-1],'시각 미상')
        self.assertTrue(pd.isna(event_seconds(d).iloc[-1]))
