# 역할: 사건 화면의 표시 시각과 저장 이력이 분리되는지 검증합니다.
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from dashboard.case_ui import case_display_payload
from dashboard.shared_cases import load_local_config


class CaseDisplayTests(unittest.TestCase):
    def test_video_and_playback_times_do_not_change_history_or_input(self):
        state = dict(link_key="case", cam_id="A1", event_ids=["E"], operator_at="2026-10-19 15:00:00")
        payload = dict(state=state, history=[dict(operator_at=state["operator_at"])])
        before = copy.deepcopy(payload)
        frame = pd.DataFrame([dict(area="A1",event_id="E",_video_seconds=4.6)])
        ep = [dict(link_key="case",first_sec=20000,last_sec=20004)]
        result = case_display_payload(payload,frame,ep,datetime(2026,10,23,14,0))
        self.assertEqual(result["state"]["video_first_position"], "00:00:04.6")
        self.assertEqual(result["state"]["playback_first_at"], "2026-10-23 14:00:04")
        self.assertEqual(result["history"], before["history"])
        self.assertEqual(payload, before)

    def test_past_case_has_no_current_playback_time_and_zero_is_valid(self):
        frame = pd.DataFrame([dict(area="A1",event_id="E",_video_seconds=0)])
        result = case_display_payload(dict(cases=[dict(cam_id="A1",event_ids=["E"])]),frame,[],datetime.now())
        self.assertEqual(result["cases"][0]["video_first_position"], "00:00:00")
        self.assertEqual(result["cases"][0]["playback_first_at"], "")

    def test_missing_source_is_not_assumed_nine_am(self):
        result = case_display_payload(dict(state=dict(event_first_clock="09:00:04")),None,[],datetime.now())
        self.assertEqual(result["state"]["video_first_position"], "")

    def test_config_only_applies_at_app_start_and_explicit_environment_wins(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            f=Path(tmp)/"connection.json"
            f.write_text(json.dumps(dict(server="http://localhost:8020",token="test-only")))
            load_local_config(f)
            self.assertEqual(os.environ["SISUN_CASE_SERVER"],"http://localhost:8020")
            os.environ["SISUN_CASE_SERVER"]=""
            load_local_config(f)
            self.assertEqual(os.environ["SISUN_CASE_SERVER"],"")
