# 역할: 한글 표시와 CSV 변환 동작을 회귀 검증합니다.
import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from dashboard_labels import (
    assessment_state_label,
    camera_label,
    csv_header_order,
    display_view,
    empty_events_message,
    empty_observations_message,
    event_to_csv_row,
    event_type_label,
    format_distance_meters,
    format_timestamp_seconds,
    load_labels,
    object_class_label,
    observation_status_label,
    ppe_state_label,
    presentation_video,
    reload_labels,
    severity_label,
    violation_status_label,
    write_display_json,
    write_events_csv,
    zone_label,
)

ROOT = Path(__file__).resolve().parents[1]
LABELS_PATH = ROOT / "configs" / "dashboard-labels.ko.json"
SAMPLE_JSON = (
    Path(__file__).parent / "samples" / "display" / "events_display_sample.json"
)


class DashboardLabelTests(unittest.TestCase):
    def setUp(self):
        reload_labels()

    def test_mapping_json_utf8_no_bom(self):
        raw = LABELS_PATH.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        data = load_labels()
        self.assertEqual(data["language"], "ko")
        self.assertEqual(data["version"], "1.0")
        roundtrip = json.loads(
            json.dumps(data, ensure_ascii=False).encode("utf-8").decode("utf-8")
        )
        self.assertEqual(
            roundtrip["event_types"]["proximity"], "지게차·작업자 근접 위험"
        )

    def test_known_event_types_and_severities(self):
        self.assertEqual(event_type_label("proximity"), "지게차·작업자 근접 위험")
        self.assertEqual(event_type_label("zone_access"), "구역 접근·진입")
        self.assertEqual(event_type_label("zone_dwell"), "구역 체류")
        self.assertEqual(event_type_label("ppe"), "안전모 착용 상태")
        self.assertEqual(event_type_label("status"), "상태 정보")
        self.assertEqual(severity_label("SAFE"), "안전")
        self.assertEqual(severity_label("WARNING"), "주의")
        self.assertEqual(severity_label("CRITICAL"), "위험")
        self.assertEqual(severity_label(None, "unconfirmed"), "미확인")
        self.assertNotEqual(severity_label(None), "안전")

    def test_observation_assessment_ppe_objects(self):
        self.assertEqual(observation_status_label("confirmed"), "확인됨")
        self.assertEqual(observation_status_label("unconfirmed"), "미확인")
        self.assertEqual(assessment_state_label("pending"), "판정 대기")
        self.assertEqual(
            assessment_state_label("no_observed_subjects"), "관측 대상 없음"
        )
        self.assertEqual(ppe_state_label("helmet_detected"), "안전모 착용 감지")
        self.assertEqual(ppe_state_label("no_helmet_candidate"), "안전모 미착용 감지")
        self.assertEqual(ppe_state_label("conflicting_evidence"), "안전모 미착용 감지")
        self.assertEqual(violation_status_label("not_verified"), "위험")
        self.assertEqual(object_class_label("person"), "작업자")
        self.assertEqual(object_class_label("no_helmet_head"), "안전모 미착용 머리")

    def test_camera_video_zone_mapping(self):
        self.assertEqual(camera_label("demo-video1"), "1번 영상 카메라")
        self.assertEqual(
            camera_label("presentation2-robot-intrusion"), "2번 영상 카메라"
        )
        self.assertEqual(camera_label("demo-video3"), "3번 영상 카메라")
        self.assertEqual(camera_label("demo-video4"), "4번 영상 카메라")
        self.assertEqual(camera_label("demo-video5"), "5번 영상 카메라")
        self.assertEqual(presentation_video(1), "1_forklift_worker_collision_risk.mp4")
        self.assertEqual(presentation_video(5), "5_Logistics Warehouse.mp4")
        self.assertIn("시연", zone_label("yellow_line_vehicle_lane"))
        self.assertIn("로봇", zone_label("robot-red-floor"))

    def test_unknown_and_empty_messages(self):
        self.assertIn("알 수 없음", event_type_label("not_real"))
        self.assertIn("mystery-cam", camera_label("mystery-cam"))
        self.assertEqual(empty_events_message(), "조회 결과 없음")
        self.assertEqual(empty_observations_message(), "관측 없음")

    def test_time_and_meters(self):
        self.assertEqual(format_timestamp_seconds(0), "0초")
        self.assertEqual(format_timestamp_seconds(12.5), "12.5초")
        self.assertNotIn("2026", format_timestamp_seconds(10))
        self.assertEqual(format_distance_meters(None), "미제공")

    def test_display_view_does_not_mutate_source(self):
        event = {
            "schema_version": "1.0",
            "event_id": "abc",
            "camera_id": "demo-video2",
            "video": "1_forklift_worker_collision_risk.mp4",
            "timestamp_seconds": 1.5,
            "event_type": "proximity",
            "severity": None,
            "observation_status": "unconfirmed",
            "assessment_state": "unassessable",
            "alert_eligible": False,
            "notification_category": "status",
            "track_ids": ["P0:1"],
            "evidence": {"reason": "x", "distance_meters": None},
        }
        original = copy.deepcopy(event)
        view = display_view(event)
        self.assertEqual(event, original)
        self.assertEqual(view["severity_label"], "미확인")
        self.assertEqual(view["event_type_label"], "지게차·작업자 근접 위험")
        self.assertEqual(view["event_id"], "abc")

    def test_csv_header_order_and_roundtrip(self):
        header = csv_header_order()
        self.assertEqual(header[0], "schema_version")
        self.assertIn("event_type_label", header)
        self.assertIn("severity_label", header)
        event = {
            "schema_version": "1.0",
            "event_id": "id-1",
            "camera_id": "demo-video4",
            "video": "4_hazard_zone_dwell.mp4",
            "source_sha256": "abc",
            "timestamp_seconds": 0,
            "event_type": "zone_dwell",
            "severity": "WARNING",
            "observation_status": "confirmed",
            "assessment_state": "observed",
            "alert_eligible": True,
            "notification_category": "risk",
            "status_reason": "image_plane_proximity_rule",
            "track_ids": ["P1"],
            "evidence": {
                "roi_id": "yellow_line_vehicle_lane",
                "observed_dwell_seconds": 4.2,
                "note": 'comma, "quote",\nline',
            },
            "model_version": "m",
            "config_version": "c",
            "scope": "s",
        }
        text = write_events_csv([event])
        self.assertFalse(text.startswith("\ufeff"))
        rows = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(list(rows[0].keys()), header)
        self.assertEqual(rows[0]["severity"], "WARNING")
        self.assertEqual(rows[0]["severity_label"], "주의")
        self.assertEqual(rows[0]["timestamp_seconds"], "0")
        self.assertEqual(json.loads(rows[0]["track_ids"]), ["P1"])
        evidence = json.loads(rows[0]["evidence"])
        self.assertIn("comma", evidence["note"])
        self.assertEqual(rows[0]["alert_eligible"], "true")
        # null severity stays not SAFE
        null_event = copy.deepcopy(event)
        null_event["severity"] = None
        null_event["observation_status"] = "unconfirmed"
        null_row = event_to_csv_row(null_event)
        self.assertIsNone(null_row["severity"])
        self.assertEqual(null_row["severity_label"], "미확인")

    def test_utf8_sig_option_separate_from_default(self):
        event = {
            "schema_version": "1.0",
            "event_id": "x",
            "camera_id": "demo-video2",
            "video": "1_forklift_worker_collision_risk.mp4",
            "timestamp_seconds": 1,
            "event_type": "ppe",
            "severity": "SAFE",
            "observation_status": "confirmed",
            "evidence": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "plain.csv"
            excel = Path(tmp) / "excel.csv"
            write_events_csv([event], plain, utf8_sig=False)
            write_events_csv([event], excel, utf8_sig=True)
            self.assertFalse(plain.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertTrue(excel.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertIn("안전", plain.read_text(encoding="utf-8"))

    def test_sample_files_preserve_codes(self):
        self.assertTrue(SAMPLE_JSON.is_file())
        payload = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
        self.assertGreaterEqual(payload["count"], 5)
        for item in payload["events"]:
            self.assertIn(item["event_type"], load_labels()["event_types"])
            self.assertTrue(item["event_id"])
            if item["severity"] is None:
                self.assertEqual(item["severity_label"], "미확인")

    def test_presentation_logs_codes_covered(self):
        labels = load_labels()
        events_root = ROOT / "outputs" / "events"
        if not events_root.is_dir():
            self.skipTest("presentation logs not installed")
        missing_types, missing_cams, missing_videos = set(), set(), set()
        for path in events_root.rglob("events_v1.jsonl"):
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    if record.get("event_type") not in labels["event_types"]:
                        missing_types.add(record.get("event_type"))
                    if record.get("camera_id") not in labels["cameras"]:
                        missing_cams.add(record.get("camera_id"))
                    if record.get("video") not in labels["videos"]:
                        missing_videos.add(record.get("video"))
        self.assertEqual(missing_types, set())
        self.assertEqual(missing_cams, set())
        self.assertEqual(missing_videos, set())


if __name__ == "__main__":
    unittest.main()
