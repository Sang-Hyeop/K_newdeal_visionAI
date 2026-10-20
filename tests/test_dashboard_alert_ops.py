# 역할: 반복 경보 묶음과 재알림 동작을 회귀 검증합니다.
"""운영 경보 묶음·재알림·확인 상태 분리 회귀."""
import tempfile
import unittest
from unittest import mock

import pandas as pd

from dashboard import alert_response as ar
from dashboard.alert_ops import process_alerts, reset_alert_ops, subject_key
from dashboard.sound import notify, reset_notify_state


def _row(**kw):
    base = {
        "event_id": "E1",
        "scenario": "collision",
        "event_type": "proximity",
        "status": "위험",
        "grade": "위험",
        "timestamp": "2026-10-19 09:00:08",
        "camera": "CAM01",
        "zone": "하역장 진입로",
        "area": "A1",
        "dwell_sec": "",
        "distance_px": 68,
        "message": "2 사람 CRIT · 68px",
        "frame": "",
        "video": "1.mp4",
        "person_no": 2,
        "worker": "작업자 B",
        "obj_x": "",
        "track_id": "P0:9",
    }
    base.update(kw)
    return base


class AlertOpsTests(unittest.TestCase):
    def setUp(self):
        reset_notify_state()
        self._tmp = tempfile.TemporaryDirectory()
        self._patch = mock.patch.object(ar, "LOCAL", self._tmp.name)
        self._patch.start()
        ar.reset_response_memory()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()
        ar.reset_response_memory()
        reset_notify_state()

    def test_same_event_id_not_duplicated(self):
        df = pd.DataFrame([_row()])
        k1, ops1 = process_alerts(df)
        self.assertEqual(k1, "hot")
        self.assertEqual(len(ops1), 1)
        k2, ops2 = process_alerts(df)
        self.assertIsNone(k2)
        self.assertEqual(ops2, [])

    def test_same_subject_same_grade_updates_without_sound(self):
        rows = [
            _row(event_id="BC02D", grade="위험", status="위험", timestamp="2026-10-19 09:00:08"),
            _row(event_id="BC02D2", grade="위험", status="위험", timestamp="2026-10-19 09:00:12", distance_px=1),
        ]
        df1 = pd.DataFrame(rows[:1])
        k1, ops1 = process_alerts(df1)
        self.assertEqual(k1, "hot")
        self.assertEqual(ops1[0]["op"], "new")
        ep = ops1[0]["episode_id"]
        df2 = pd.DataFrame(rows)
        k2, ops2 = process_alerts(df2)
        # 두 번째 id만 신규 처리 → update, 소리 없음
        self.assertIsNone(k2)
        self.assertEqual(len(ops2), 1)
        self.assertEqual(ops2[0]["op"], "update")
        self.assertEqual(ops2[0]["episode_id"], ep)
        self.assertEqual(ops2[0]["related_count"], 2)
        self.assertIn("관련 기록 2건", ops2[0]["text"])

    def test_warn_to_hot_upgrade_sounds(self):
        w = _row(event_id="BC02W", grade="주의", status="주의", timestamp="2026-10-19 09:00:07", distance_px=162)
        d = _row(event_id="BC02D", grade="위험", status="위험", timestamp="2026-10-19 09:00:08")
        k1, ops1 = process_alerts(pd.DataFrame([w]))
        # 주의는 목록만 — 소리 kind 없음
        self.assertIsNone(k1)
        self.assertEqual(ops1[0]["op"], "new")
        self.assertEqual(ops1[0]["level"], "warn")
        k2, ops2 = process_alerts(pd.DataFrame([w, d]))
        self.assertEqual(k2, "hot")
        self.assertEqual(ops2[0]["op"], "upgrade")
        self.assertTrue(ops2[0]["ack_reset"])

    def test_warn_only_notify_has_no_sound_kind(self):
        w = _row(event_id="W1", grade="주의", status="주의", timestamp="2026-10-19 09:00:07")
        self.assertEqual(notify(pd.DataFrame([w])), "")

    def test_batch_multiple_hot_one_sound_kind(self):
        a = _row(event_id="H1", person_no=1, worker="작업자 A", track_id="P0:1", timestamp="2026-10-19 09:00:01")
        b = _row(event_id="H2", person_no=2, worker="작업자 B", track_id="P0:9", timestamp="2026-10-19 09:00:08")
        k, ops = process_alerts(pd.DataFrame([a, b]))
        self.assertEqual(k, "hot")
        self.assertEqual(len(ops), 2)

    def test_different_subjects_separate(self):
        a = _row(event_id="A", person_no=1, worker="작업자 A", track_id="P0:1", timestamp="2026-10-19 09:00:01")
        b = _row(event_id="B", person_no=2, worker="작업자 B", track_id="P0:9", timestamp="2026-10-19 09:00:08")
        k, ops = process_alerts(pd.DataFrame([a, b]))
        self.assertEqual(k, "hot")
        self.assertEqual(len(ops), 2)
        self.assertNotEqual(ops[0]["episode_id"], ops[1]["episode_id"])

    def test_fire_tracks_separate(self):
        f1 = _row(
            event_id="f1", scenario="fire", status="화재 의심", grade="위험",
            area="P1", camera="CAM06", zone="옥외 주차장",
            person_no=0, worker="불꽃", track_id="FIRE2:1",
            timestamp="2026-10-19 09:00:04.6",
        )
        f2 = _row(
            event_id="f2", scenario="fire", status="화재 의심", grade="위험",
            area="P1", camera="CAM06", zone="옥외 주차장",
            person_no=0, worker="불꽃", track_id="FIRE3:2",
            timestamp="2026-10-19 09:00:08.8",
        )
        _, ops = process_alerts(pd.DataFrame([f1, f2]))
        self.assertEqual(len(ops), 2)
        self.assertNotEqual(ops[0]["episode_id"], ops[1]["episode_id"])

    def test_lost_observation_not_alert(self):
        lost = _row(
            event_id="lost", scenario="fire", status="관측 소실", grade="미확인",
            area="P1", track_id="FIRE2:1", person_no=0, worker="불꽃",
        )
        k, ops = process_alerts(pd.DataFrame([lost]))
        self.assertIsNone(k)
        self.assertEqual(ops, [])

    def test_no_subject_not_merged(self):
        a = _row(event_id="x1", person_no=0, worker="", track_id="", timestamp="2026-10-19 09:00:01")
        b = _row(event_id="x2", person_no=0, worker="", track_id="", timestamp="2026-10-19 09:00:02")
        self.assertIsNone(subject_key(pd.Series(a)))
        _, ops = process_alerts(pd.DataFrame([a, b]))
        self.assertEqual(len(ops), 2)
        self.assertNotEqual(ops[0]["episode_id"], ops[1]["episode_id"])

    def test_notify_pending_updates_without_sound_kind(self):
        rows = [
            _row(event_id="D1", timestamp="2026-10-19 09:00:08"),
            _row(event_id="D2", timestamp="2026-10-19 09:00:12"),
        ]
        self.assertEqual(notify(pd.DataFrame(rows[:1])), "hot")
        # 두 번째: update only → 빈 문자열(소리 없음), None 아님
        kind = notify(pd.DataFrame(rows))
        self.assertEqual(kind, "")

    def test_reset_allows_refire(self):
        df = pd.DataFrame([_row()])
        self.assertEqual(notify(df), "hot")
        self.assertIsNone(notify(df))
        reset_notify_state()
        self.assertEqual(notify(df), "hot")

    def test_idle_gap_starts_new_episode(self):
        a = _row(event_id="t1", timestamp="2026-10-19 09:00:08")
        b = _row(event_id="t2", timestamp="2026-10-19 09:00:20")  # +12s > gap 5
        k1, ops1 = process_alerts(pd.DataFrame([a]))
        k2, ops2 = process_alerts(pd.DataFrame([a, b]))
        self.assertEqual(ops1[0]["op"], "new")
        self.assertEqual(ops2[0]["op"], "new")
        self.assertNotEqual(ops1[0]["episode_id"], ops2[0]["episode_id"])

    def test_idle_split_then_update_binds_to_latest(self):
        """1초 new → 8초(>5s) new → 9초 update(8초 묶음)."""
        r1 = _row(event_id="t1", timestamp="2026-10-19 09:00:01")
        r8 = _row(event_id="t8", timestamp="2026-10-19 09:00:08")
        r9 = _row(event_id="t9", timestamp="2026-10-19 09:00:09")
        _, ops1 = process_alerts(pd.DataFrame([r1]))
        self.assertEqual(ops1[0]["op"], "new")
        ep1 = ops1[0]["episode_id"]
        _, ops8 = process_alerts(pd.DataFrame([r1, r8]))
        self.assertEqual(ops8[0]["op"], "new")
        ep8 = ops8[0]["episode_id"]
        self.assertNotEqual(ep1, ep8)
        _, ops9 = process_alerts(pd.DataFrame([r1, r8, r9]))
        self.assertEqual(len(ops9), 1)
        self.assertEqual(ops9[0]["op"], "update")
        self.assertEqual(ops9[0]["episode_id"], ep8)
        self.assertEqual(ops9[0]["related_count"], 2)

    def test_vehicle_pair_separates_collision(self):
        a = _row(
            event_id="v1", person_no=1, track_id="P0:1",
            vehicle_track_id="F0:3", timestamp="2026-10-19 09:00:01",
        )
        b = _row(
            event_id="v2", person_no=1, track_id="P0:1",
            vehicle_track_id="F0:9", timestamp="2026-10-19 09:00:02",
        )
        _, ops = process_alerts(pd.DataFrame([a, b]))
        self.assertEqual(len(ops), 2)
        self.assertNotEqual(ops[0]["episode_id"], ops[1]["episode_id"])
        self.assertIn("link_key", ops[0])
        self.assertTrue(ops[0]["link_key"])

    def test_ops_include_stable_link_fields(self):
        _, ops = process_alerts(pd.DataFrame([_row(event_id="L1")]))
        self.assertIn("anchor_event_id", ops[0])
        self.assertEqual(ops[0]["anchor_event_id"], "L1")
        self.assertIn("event_ids", ops[0])

    def test_new_episode_assigns_demo_assignee_once(self):
        _, ops1 = process_alerts(pd.DataFrame([_row(event_id="AS1", timestamp="2026-10-19 09:00:01")]))
        self.assertIn(ops1[0].get("assigned_to"), ar.DEMO_ASSIGNEES)
        a1 = ops1[0]["assigned_to"]
        link = ops1[0]["link_key"]
        _, ops2 = process_alerts(pd.DataFrame([
            _row(event_id="AS1", timestamp="2026-10-19 09:00:01"),
            _row(event_id="AS2", timestamp="2026-10-19 09:00:02"),
        ]))
        self.assertEqual(ops2[0]["op"], "update")
        st = ar.get_state_by_link(link)
        self.assertEqual(st["state"]["assigned_to"], a1)


if __name__ == "__main__":
    unittest.main()
