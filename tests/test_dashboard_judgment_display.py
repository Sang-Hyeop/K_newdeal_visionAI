# 역할: 판정 근거·한글 설명·설정 캐시 동작을 회귀 검증합니다.
"""관제 표시: 화재 상태 일치·설정 캐시·내부 약어 미노출."""
import unittest

import pandas as pd

from dashboard.criteria_runtime import criteria_bundle, criteria_cache
from dashboard.display_text import (
    fire_evidence_lines,
    fire_reason_label,
    operator_message_for_row,
)
from dashboard.judgment import judgment_panel_html, judgment_sections
from dashboard.ui import (
    evidence_lines_for_row,
    live_detail_summary_html,
    live_judgment_html,
    reason_label_for_row,
    table_html,
)


def _row(**kwargs):
    base = {
        "event_id": "t1",
        "scenario": "fire",
        "event_type": "fire",
        "status": "관측 소실",
        "grade": "미확인",
        "timestamp": "2026-10-19 09:00:10",
        "camera": "CAM06",
        "zone": "옥외 주차장",
        "area": "P1",
        "dwell_sec": "",
        "distance_px": "",
        "message": "현재 불꽃 관측 소실 · 진화 여부 확인 필요",
        "frame": "",
        "video": "6_parking_lot_fire.mp4",
        "person_no": 0,
        "worker": "불꽃",
        "obj_x": "",
        "track_id": "",
    }
    base.update(kwargs)
    return base


class FireStatusDisplayTests(unittest.TestCase):
    def test_lost_observation_not_suspected(self):
        row = pd.Series(_row())
        self.assertEqual(reason_label_for_row(row), "불꽃 관측 소실")
        evidence, check = evidence_lines_for_row(row)
        self.assertIn("끊긴", evidence)
        self.assertNotIn("반복 관측으로 불꽃 의심 조건 충족", evidence)
        self.assertNotIn("조건 충족", evidence)
        self.assertNotIn("현장 안전", evidence)
        self.assertNotIn("진화 완료", evidence)
        html = live_detail_summary_html(pd.DataFrame([_row()]), elapsed=12.0, window=12.0)
        self.assertIn("불꽃 관측 소실", html)
        self.assertNotIn("불꽃 의심", html)
        self.assertNotIn("반복 관측으로 불꽃 의심 조건 충족", html)
        panel = judgment_panel_html(row)
        self.assertIn("관측 소실", panel)
        self.assertIn("안전 복귀", panel)

    def test_fire_status_labels_distinct(self):
        cases = {
            "확인 중": ("불꽃 확인 중", "확인 중"),
            "화재 의심": ("불꽃 의심", "충족"),
            "관측 소실": ("불꽃 관측 소실", "끊긴"),
            "판정 불가": ("불꽃 판정 불가", "근거 부족"),
        }
        for status, (reason, evidence_bit) in cases.items():
            self.assertEqual(fire_reason_label(status), reason)
            self.assertIn(evidence_bit, fire_evidence_lines(status)[0])
        self.assertEqual(fire_reason_label("기타"), "불꽃 상태 확인 필요")
        self.assertNotIn("의심 조건 충족", fire_evidence_lines("기타")[0])

    def test_past_danger_and_latest_lost_not_mixed(self):
        rows = [
            _row(
                event_id="hot",
                status="화재 의심",
                grade="위험",
                timestamp="2026-10-19 09:00:08",
                message="반복 관측에 따른 화재 의심",
            ),
            _row(
                event_id="lost",
                status="관측 소실",
                grade="미확인",
                timestamp="2026-10-19 09:00:11",
            ),
        ]
        html = live_detail_summary_html(pd.DataFrame(rows), elapsed=12.0, window=12.0)
        self.assertIn("불꽃 의심", html)
        self.assertIn("09:00:08", html)
        self.assertIn("최근 기록", html)
        self.assertIn("최신 관측 상태", html)
        self.assertIn("관측 소실", html)
        self.assertIn("09:00:11", html)
        self.assertIn("별개", html)
        # 대표 행과 패널도 같은 위험 기록
        panel = live_judgment_html(pd.DataFrame(rows), elapsed=12.0, window=12.0)
        self.assertIn("화재 의심", panel)


class CriteriaRuntimeTests(unittest.TestCase):
    def test_cache_loads_once_and_matches_files(self):
        a = criteria_cache()
        b = criteria_cache()
        self.assertIs(a, b)
        src, lines = criteria_bundle("collision", "A1")
        self.assertIn("설정 파일", src)
        joined = " ".join(lines)
        self.assertIn("1.0", joined)
        self.assertIn("0.5", joined)
        self.assertNotIn("약 3초 이후 위험", joined)

    def test_dwell_uses_vehicle_critical_not_generic(self):
        src, lines = criteria_bundle("dwell", "A4")
        joined = " ".join(lines)
        self.assertIn("3", joined)
        self.assertIn("차량", joined)
        self.assertNotIn("약 3초 이후 위험", joined)
        # LaneHazard 위험 임계는 vehicle_critical(3). critical_seconds(5)를 위험처럼 쓰지 않음
        self.assertNotIn("≥ 5초이면 위험", joined)
        self.assertNotIn("5초이면 위험", joined)

    def test_warehouse_dwell_mentions_co_presence(self):
        _, lines = criteria_bundle("dwell", "B1")
        joined = " ".join(lines)
        self.assertIn("동시 관측", joined)

    def test_ppe_from_policy(self):
        src, lines = criteria_bundle("ppe", "A3")
        joined = " ".join(lines)
        self.assertTrue("load_policy" in src or "설정 파일" in src or "실행 정책" in src)
        self.assertIn("1.0", joined)
        self.assertIn("0.75", joined)

    def test_fire_temporal(self):
        src, lines = criteria_bundle("fire", "P1")
        joined = " ".join(lines)
        self.assertIn("0.4", joined)
        self.assertIn("3", joined)


class OperatorMessageTests(unittest.TestCase):
    def test_structured_proximity_no_crit(self):
        row = pd.Series(
            _row(
                scenario="collision",
                status="위험",
                grade="위험",
                worker="작업자 B",
                person_no=2,
                distance_px=1.0,
                message="2 사람 CRIT · 1px",
                area="A1",
            )
        )
        text = operator_message_for_row(row)
        self.assertIn("작업자 B", text)
        self.assertIn("위험", text)
        self.assertIn("1px", text)
        self.assertNotIn("CRIT", text)
        self.assertNotIn("WARN", text)

    def test_unknown_zero_gap_not_contact(self):
        row = pd.Series(
            _row(
                scenario="collision",
                status="미확인",
                grade="미확인",
                worker="",
                person_no=2,
                distance_px=0.0,
                message="2 사람 UNKNOWN · 0px",
                area="A1",
            )
        )
        text = operator_message_for_row(row)
        self.assertIn("간격 확인 불가", text)
        self.assertNotIn("충돌", text)
        self.assertNotIn("UNKNOWN", text)

    def test_legacy_message_in_table(self):
        frame = pd.DataFrame(
            [
                _row(
                    scenario="collision",
                    status="위험",
                    grade="위험",
                    worker="",
                    person_no=2,
                    distance_px=1.0,
                    message="2 사람 CRIT · 1px",
                    area="A1",
                    camera="CAM01",
                    zone="하역장",
                )
            ]
        )
        html = table_html(frame)
        self.assertNotIn("CRIT", html)
        self.assertIn("위험", html)
        self.assertIn("화면상 간격 1px", html)

    def test_summary_and_panel_same_row(self):
        rows = [
            _row(
                scenario="collision",
                status="위험",
                grade="위험",
                worker="작업자 B",
                person_no=2,
                distance_px=1.0,
                message="2 사람 CRIT · 1px",
                area="A1",
                camera="CAM01",
                zone="하역장 진입로",
                timestamp="2026-10-19 09:00:12",
            )
        ]
        part = pd.DataFrame(rows)
        summary = live_detail_summary_html(part, elapsed=20.0, window=12.0)
        panel = live_judgment_html(part, elapsed=20.0, window=12.0)
        self.assertIn("09:00:12", summary)
        self.assertIn("09:00:12", panel)
        self.assertIn("작업자 B", summary)
        self.assertNotIn("CRIT", summary + panel)
        sec = judgment_sections(pd.Series(rows[0]), cam={"id": "A1"})
        self.assertIn("설정 파일", sec["criteria_source"])


if __name__ == "__main__":
    unittest.main()
