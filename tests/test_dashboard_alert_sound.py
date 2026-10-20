# 역할: 알림음 중복 방지와 재생 조건 동작을 회귀 검증합니다.
"""알림음: 위험만·요청 id 1회·주의 무음 · busy 해제 계약(JS)."""
import re
import tempfile
import unittest
from unittest import mock

import pandas as pd

from dashboard import alert_response as ar
from dashboard import style as style_mod
from dashboard.sound import beep_html, notify, reset_notify_state, write_beep


def _row(**kw):
    base = {
        "event_id": "E1",
        "scenario": "collision",
        "event_type": "proximity",
        "status": "위험",
        "grade": "위험",
        "timestamp": "2026-10-19 09:00:08",
        "camera": "CAM01",
        "zone": "하역장",
        "area": "A1",
        "dwell_sec": "",
        "distance_px": 1,
        "message": "x",
        "frame": "",
        "video": "1.mp4",
        "person_no": 2,
        "worker": "작업자 B",
        "obj_x": "",
        "track_id": "P0:9",
    }
    base.update(kw)
    return base


class AlertSoundTests(unittest.TestCase):
    def setUp(self):
        reset_notify_state()
        write_beep()
        self._tmp = tempfile.TemporaryDirectory()
        self._patch = mock.patch.object(ar, "LOCAL", self._tmp.name)
        self._patch.start()
        ar.reset_response_memory()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()
        ar.reset_response_memory()
        reset_notify_state()

    def test_hot_beep_has_unique_sound_id_no_autoplay(self):
        notify(pd.DataFrame([_row(event_id="S1")]))
        html1 = beep_html("hot")
        self.assertIn("sisun-beep", html1)
        self.assertIn("data-sound-id=", html1)
        self.assertNotIn("autoplay", html1)
        m1 = re.search(r"data-sound-id=['\"](\d+)['\"]", html1)
        self.assertIsNotNone(m1)
        notify(pd.DataFrame([_row(event_id="S2", timestamp="2026-10-19 09:00:10", person_no=3)]))
        html2 = beep_html("hot")
        m2 = re.search(r"data-sound-id=['\"](\d+)['\"]", html2)
        self.assertIsNotNone(m2)
        self.assertNotEqual(m1.group(1), m2.group(1))

    def test_warn_beep_html_has_no_audio(self):
        notify(pd.DataFrame([_row(event_id="W1", grade="주의", status="주의")]))
        html = beep_html("")
        self.assertNotIn("<audio", html)
        self.assertIn("sisun-toast-payload", html)

    def test_warn_kind_ignored_for_audio(self):
        notify(pd.DataFrame([_row(event_id="W2", grade="주의", status="주의")]))
        html = beep_html("warn")
        self.assertNotIn("<audio", html)

    def test_update_only_no_sound_kind(self):
        rows = [
            _row(event_id="D1", timestamp="2026-10-19 09:00:08"),
            _row(event_id="D2", timestamp="2026-10-19 09:00:12"),
        ]
        self.assertEqual(notify(pd.DataFrame(rows[:1])), "hot")
        beep_html("hot")  # drain pending
        self.assertEqual(notify(pd.DataFrame(rows)), "")

    def test_boot_js_uses_dedicated_player_and_request_guard(self):
        js = style_mod.BOOT_JS
        self.assertIn("__sisunBeepPlayer", js)
        self.assertIn("__sisunBeepReq", js)
        self.assertIn("finishBeepReq", js)
        # Gradio audio 제거 후에도 busy가 요청 id로만 해제
        self.assertIn("window.__sisunBeepReq === req", js)
        # 300ms 폴링에서 play() 재호출 구조로 돌아가지 않음
        self.assertIn("allOf(\"audio.sisun-beep\").forEach(armBeepOnce)", js)
        self.assertNotIn("setInterval(armBeepOnce", js)


if __name__ == "__main__":
    unittest.main()
