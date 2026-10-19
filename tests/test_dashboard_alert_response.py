"""운영 경보 대응 상태 전이·로그 (감지 상태와 분리)."""
import os
import tempfile
import threading
import unittest
from unittest import mock

from dashboard import alert_response as ar


def _base_payload(**kw):
    data = {
        "request_id": "req-1",
        "link_key": "A1|collision|person:2|e0:E1",
        "episode_id": "0|A1|collision|person:2",
        "cam_id": "A1",
        "scenario": "collision",
        "subject": "person:2",
        "anchor_event_id": "E1",
        "event_ids": ["E1"],
        "operator": "김상협",
        "prev_status": "new",
        "next_status": "acked",
        "note": "",
        "operator_at": "2026-10-19 13:30:00",
        "event_first_clock": "09:00:04",
        "detection_status": "위험",
    }
    data.update(kw)
    return data


class AlertResponseTests(unittest.TestCase):
    def setUp(self):
        ar.reset_response_memory()

    def test_labels_and_transitions(self):
        self.assertEqual(ar.response_label("acting"), "조치 중")
        self.assertEqual(ar.response_label("acked"), "확인함")
        self.assertEqual(ar.response_label("new"), "확인 전")
        self.assertTrue(ar.can_transition("new", "acked"))
        self.assertTrue(ar.can_transition("acked", "acting"))
        self.assertTrue(ar.can_transition("acting", "done"))
        self.assertFalse(ar.can_transition("new", "done"))
        self.assertFalse(ar.can_transition("done", "acked"))
        self.assertFalse(ar.can_transition("acting", "acked"))

    def test_note_required(self):
        self.assertFalse(ar.note_required("acked"))
        self.assertTrue(ar.note_required("acting"))
        self.assertTrue(ar.note_required("done"))

    def test_save_success_and_reject_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ar, "LOCAL", tmp):
                ar.reset_response_memory()
                result = ar.apply_transition(_base_payload())
                self.assertTrue(result["ok"])
                self.assertEqual(result["entry"]["next_label"], "확인함")
                self.assertIn("안전 보증", result["entry"]["disclaimer"])
                self.assertIn(result["state"]["assigned_to"], ar.DEMO_ASSIGNEES)
                self.assertEqual(result["state"]["last_operator"], "김상협")
                self.assertNotEqual(result["state"]["assigned_to"], "김상협")
                path = ar.log_path()
                self.assertTrue(os.path.isfile(path))

                with self.assertRaises(ValueError):
                    ar.apply_transition(
                        _base_payload(
                            request_id="req-2",
                            prev_status="acked",
                            next_status="acting",
                            note="",
                        )
                    )

                ar.apply_transition(
                    _base_payload(
                        request_id="req-3",
                        prev_status="acked",
                        next_status="acting",
                        note="현장 담당자에게 확인 요청",
                    )
                )
                with open(path, encoding="utf-8") as fh:
                    lines = [ln for ln in fh if ln.strip()]
                # case_open(배정) + acked + acting
                self.assertEqual(len(lines), 3)

    def test_idempotent_request_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ar, "LOCAL", tmp):
                ar.reset_response_memory()
                p = _base_payload(request_id="same-req")
                r1 = ar.apply_transition(p)
                r2 = ar.apply_transition(p)
                self.assertTrue(r1["ok"])
                self.assertTrue(r2["ok"])
                self.assertTrue(r2.get("duplicate"))
                with open(ar.log_path(), encoding="utf-8") as fh:
                    lines = [ln for ln in fh if ln.strip()]
                # case_open + 전이 1행 (재시도는 추가 안 함)
                self.assertEqual(len(lines), 2)

    def test_server_rejects_bad_transition_without_mutating(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ar, "LOCAL", tmp):
                ar.reset_response_memory()
                ar.apply_transition(_base_payload())
                with self.assertRaises(ValueError):
                    ar.apply_transition(
                        _base_payload(
                            request_id="bad",
                            prev_status="new",
                            next_status="done",
                            note="완료",
                        )
                    )
                st = ar.get_state_by_link("A1|collision|person:2|e0:E1")
                self.assertEqual(st["state"]["status"], "acked")

    def test_restore_by_event_id_not_epoch(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ar, "LOCAL", tmp):
                ar.reset_response_memory()
                ar.apply_transition(
                    _base_payload(
                        note="",
                        next_status="acked",
                    )
                )
                ar.apply_transition(
                    _base_payload(
                        request_id="req-act",
                        prev_status="acked",
                        next_status="acting",
                        note="출동",
                    )
                )
                ar.reset_response_memory()
                loaded = ar.load_logs_into_memory(force=True)
                self.assertTrue(loaded["ok"] or loaded["count"] >= 1)
                by_eid = ar.get_states_for_event_ids(["E1"])
                self.assertIn("E1", by_eid["by_event_id"])
                self.assertEqual(by_eid["by_event_id"]["E1"]["status"], "acting")
                self.assertEqual(by_eid["by_event_id"]["E1"]["note"], "출동")

    def test_history_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ar, "LOCAL", tmp):
                ar.reset_response_memory()
                ar.apply_transition(_base_payload())
                ar.apply_transition(
                    _base_payload(
                        request_id="r2",
                        prev_status="acked",
                        next_status="acting",
                        note="조치",
                    )
                )
                hist = ar.history_for_link("A1|collision|person:2|e0:E1")
                # case_open + acked + acting
                self.assertEqual(len(hist["history"]), 3)

    def test_corrupt_line_does_not_break_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ar, "LOCAL", tmp):
                ar.reset_response_memory()
                path = ar.log_path()
                os.makedirs(tmp, exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("not-json\n")
                    fh.write(
                        '{"request_id":"ok1","link_key":"A1|collision|person:2|e0:E1",'
                        '"next_status":"acked","operator":"A","event_ids":["E1"],'
                        '"anchor_event_id":"E1"}\n'
                    )
                info = ar.load_logs_into_memory(force=True)
                self.assertIsNotNone(info.get("error"))
                st = ar.get_state_by_link("A1|collision|person:2|e0:E1")
                self.assertEqual(st["state"]["status"], "acked")

    def test_concurrent_requests_serialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ar, "LOCAL", tmp):
                ar.reset_response_memory()
                results = []

                def worker(i):
                    try:
                        results.append(
                            ar.apply_transition(
                                _base_payload(request_id=f"c-{i}", next_status="acked")
                            )
                        )
                    except Exception as exc:
                        results.append({"ok": False, "error": str(exc)})

                threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                ok = [r for r in results if r.get("ok")]
                self.assertGreaterEqual(len(ok), 1)
                with open(ar.log_path(), encoding="utf-8") as fh:
                    lines = [ln for ln in fh if ln.strip()]
                # case_open + 성공 전이 1행
                kinds = []
                import json
                for ln in lines:
                    kinds.append(json.loads(ln).get("kind") or "transition")
                self.assertEqual(kinds.count("transition"), 1)
                self.assertGreaterEqual(kinds.count("case_open"), 1)

    def test_detection_loss_cannot_skip_to_done(self):
        """관측 소실 등으로 new→done 자동 전이 불가."""
        self.assertFalse(ar.can_transition("new", "done"))
        self.assertFalse(ar.can_transition("acked", "done"))

    def test_ensure_case_assigns_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ar, "LOCAL", tmp):
                ar.reset_response_memory()
                meta = {
                    "cam_id": "A1",
                    "scenario": "collision",
                    "subject": "person:2",
                    "anchor_event_id": "E9",
                    "event_ids": ["E9"],
                    "title": "위험 · 테스트",
                    "first_clock": "09:00:01",
                    "last_clock": "09:00:01",
                }
                r1 = ar.ensure_case(meta)
                r2 = ar.ensure_case(meta)
                self.assertTrue(r1["created"])
                self.assertFalse(r2["created"])
                self.assertEqual(r1["state"]["assigned_to"], r2["state"]["assigned_to"])
                self.assertIn(r1["state"]["assigned_to"], ar.DEMO_ASSIGNEES)

    def test_operator_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ar, "LOCAL", tmp):
                ar.reset_response_memory()
                with self.assertRaises(ValueError):
                    ar.apply_transition(_base_payload(operator=""))


if __name__ == "__main__":
    unittest.main()
