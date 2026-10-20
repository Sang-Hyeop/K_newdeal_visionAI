# 운영 경보 대응 상태·조치 기록 (감지 상태와 분리)
"""감지 grade/status 는 바꾸지 않는다. 운영자 대응 단계와 로그만 다룬다.

상태: new(확인 전) → acked(확인함) → acting(조치 중) → done(조치 완료)
- 저장 성공 후에만 상태를 확정(서버 권위)
- link_key + event_id 인덱스 (epoch 제외)
- request_id 멱등
- 배정 담당자(A~D 시연용)와 실제 처리 사용자(로그인명) 분리
"""

from __future__ import annotations

import json
import os
import random
import threading
from datetime import datetime
from typing import Any

from .config import LOCAL
from . import shared_cases

RESPONSE_STATES = ("new", "acked", "acting", "done")

RESPONSE_LABELS = {
    "new": "확인 전",
    "acked": "확인함",
    "acting": "조치 중",
    "done": "조치 완료",
}

ALLOWED_TRANSITIONS = {
    "new": frozenset({"acked"}),
    "acked": frozenset({"acting"}),
    "acting": frozenset({"done"}),
    "done": frozenset(),
}

DEMO_ASSIGNEES = ("담당자 A", "담당자 B", "담당자 C", "담당자 D")
VALID_ASSIGNEES = frozenset(DEMO_ASSIGNEES)

_STORE = None  # SQLite journal is supplied only by the standalone shared service.
_REMOTE_ROWS = []

_LOG_NAME = "alert_response_log.jsonl"
_LOCK = threading.Lock()

_CURRENT: dict[str, dict[str, Any]] = {}
_SEEN_REQUESTS: dict[str, dict[str, Any]] = {}
_EVENT_INDEX: dict[str, str] = {}
_LOG_READ_ERROR: str | None = None
_LOADED = False
_MIGRATED_ASSIGN = False


def reset_response_memory():
    """테스트·LOCAL 교체 시 메모리 초기화. 운영 파일은 지우지 않음."""
    global _LOADED, _LOG_READ_ERROR, _MIGRATED_ASSIGN
    with _LOCK:
        _CURRENT.clear()
        _SEEN_REQUESTS.clear()
        _EVENT_INDEX.clear()
        _LOADED = False
        _LOG_READ_ERROR = None
        _MIGRATED_ASSIGN = False


def response_label(state: str) -> str:
    return RESPONSE_LABELS.get(str(state or ""), str(state or ""))


def can_transition(prev: str, nxt: str) -> bool:
    p = str(prev or "new")
    n = str(nxt or "")
    if p not in RESPONSE_STATES or n not in RESPONSE_STATES:
        return False
    return n in ALLOWED_TRANSITIONS.get(p, frozenset())


def note_required(nxt: str) -> bool:
    return str(nxt) in ("acting", "done")


def log_path() -> str:
    return os.path.join(LOCAL, _LOG_NAME)


def make_link_key(cam_id: str, scenario: str, subject: str, anchor_event_id: str) -> str:
    """epoch 없는 영속 연결 키. anchor=에피소드 최초 event_id."""
    return "|".join(
        [
            str(cam_id or "").strip(),
            str(scenario or "").strip(),
            str(subject or "").strip() or "alone",
            f"e0:{str(anchor_event_id or '').strip()}",
        ]
    )


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_line(line: str) -> dict[str, Any] | None:
    text = (line or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _pick_assignee() -> str:
    """균등 무작위(건수 균등 배분 보장 아님)."""
    return random.choice(DEMO_ASSIGNEES)


def _blank_case(link: str) -> dict[str, Any]:
    return {
        "link_key": link,
        "status": "new",
        "assigned_to": "",
        "last_operator": "",
        "note": "",
        "operator_at": "",
        "event_ids": [],
        "cam_id": "",
        "cam_code": "",
        "scenario": "",
        "subject": "",
        "anchor_event_id": "",
        "title": "",
        "action": "",
        "grade": "",
        "level": "",
        "detection_status": "",
        "event_first_clock": "",
        "event_last_clock": "",
        "related_count": 0,
        "opened_at": "",
        "done_at": "",
    }


def _merge_meta(cur: dict[str, Any], row: dict[str, Any]):
    for key in (
        "cam_id", "cam_code", "scenario", "subject", "anchor_event_id",
        "title", "action", "grade", "level", "detection_status",
        "event_first_clock", "event_last_clock",
    ):
        val = row.get(key)
        if val not in (None, ""):
            cur[key] = str(val)
    if row.get("related_count") not in (None, ""):
        try:
            cur["related_count"] = int(row.get("related_count") or 0)
        except (TypeError, ValueError):
            pass
    eids = row.get("event_ids") or []
    if isinstance(eids, list) and eids:
        merged = list(dict.fromkeys([*(cur.get("event_ids") or []), *[str(x) for x in eids if x]]))
        cur["event_ids"] = merged
        for eid in merged:
            _EVENT_INDEX[str(eid)] = cur["link_key"]
    anchor = str(row.get("anchor_event_id") or "")
    if anchor:
        _EVENT_INDEX[anchor] = cur["link_key"]


def _apply_row_to_memory(row: dict[str, Any]):
    link = str(row.get("link_key") or "").strip()
    if not link:
        return
    req = str(row.get("request_id") or "").strip()
    if req:
        _SEEN_REQUESTS[req] = {"ok": True, "entry": row}
    kind = str(row.get("kind") or "transition")
    cur = _CURRENT.get(link) or _blank_case(link)
    _merge_meta(cur, row)

    assigned = str(row.get("assigned_to") or "").strip()
    if assigned in VALID_ASSIGNEES:
        cur["assigned_to"] = assigned

    if kind == "case_observation":
        _CURRENT[link] = cur
        return

    if kind == "observation_day":
        days = set(cur.get("observed_dates") or [])
        days.add(str(row.get("observed_date") or ""))
        cur["observed_dates"] = sorted(days - {""})
        _CURRENT[link] = cur
        return

    if kind == "case_open":
        cur["status"] = str(cur.get("status") or "new")
        if cur["status"] not in RESPONSE_STATES:
            cur["status"] = "new"
        if not cur.get("opened_at"):
            cur["opened_at"] = str(row.get("operator_at") or row.get("opened_at") or "")
        _CURRENT[link] = cur
        return

    if kind == "reopen":
        cur["status"] = "new"
        cur["operator_at"] = str(row.get("operator_at") or cur.get("operator_at") or "")
        cur["last_operator"] = str(row.get("operator") or cur.get("last_operator") or "")
        _CURRENT[link] = cur
        return

    nxt = str(row.get("next_status") or "new")
    if nxt in RESPONSE_STATES:
        cur["status"] = nxt
    op = str(row.get("operator") or "").strip()
    if op:
        cur["last_operator"] = op
    if row.get("note") is not None:
        cur["note"] = str(row.get("note") or "")
    at = str(row.get("operator_at") or "")
    if at:
        cur["operator_at"] = at
    if nxt == "done" and at:
        cur["done_at"] = at
    if not cur.get("opened_at") and at:
        cur["opened_at"] = at
    _CURRENT[link] = cur


def _append_line_unlocked(row: dict[str, Any]) -> None:
    if _STORE is not None:
        _STORE.append(row)
    else:
        os.makedirs(LOCAL, exist_ok=True)
        line = json.dumps(row, ensure_ascii=False) + "\n"
        try:
            with open(log_path(), "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError as exc:
            raise ValueError(f"조치 이력 저장 실패: {exc}") from exc
    _apply_row_to_memory(row)


def _load_unlocked(force: bool = False) -> dict[str, Any]:
    global _LOADED, _LOG_READ_ERROR
    if _LOADED and not force:
        return {
            "ok": _LOG_READ_ERROR is None,
            "error": _LOG_READ_ERROR,
            "count": len(_CURRENT),
        }
    _CURRENT.clear()
    _SEEN_REQUESTS.clear()
    _EVENT_INDEX.clear()
    _LOG_READ_ERROR = None
    path = log_path()
    if _STORE is None and not os.path.isfile(path):
        _LOADED = True
        return {"ok": True, "error": None, "count": 0}
    bad = 0
    try:
        if _STORE is not None:
            rows = _STORE.rows()
        else:
            with open(path, encoding="utf-8") as fh:
                rows = [_parse_line(line) for line in fh]
        for row in rows:
            if row is None:
                bad += 1
                continue
            _apply_row_to_memory(row)
    except OSError as exc:
        _LOG_READ_ERROR = f"조치 이력 읽기 실패: {exc}"
        _LOADED = True
        return {"ok": False, "error": _LOG_READ_ERROR, "count": 0}
    if bad:
        _LOG_READ_ERROR = f"손상된 이력 {bad}행을 건너뛰었습니다"
    _LOADED = True
    return {
        "ok": bad == 0,
        "error": _LOG_READ_ERROR,
        "count": len(_CURRENT),
    }


def load_logs_into_memory(force: bool = False) -> dict[str, Any]:
    global _REMOTE_ROWS, _LOADED, _LOG_READ_ERROR
    if shared_cases.enabled():
        try:
            rows = shared_cases.snapshot(force=force)['rows']
            with _LOCK:
                reset = list(rows)
                _CURRENT.clear(); _SEEN_REQUESTS.clear(); _EVENT_INDEX.clear()
                for row in reset:
                    _apply_row_to_memory(row)
                _REMOTE_ROWS = reset
                _LOADED = True; _LOG_READ_ERROR = None
                return {'ok': True, 'count': len(_CURRENT), 'error': None}
        except ValueError as exc:
            _LOG_READ_ERROR = str(exc)
            return {'ok': False, 'error': str(exc), 'count': 0}
    with _LOCK:
        return _load_unlocked(force=force)


def migrate_missing_assignees() -> dict[str, Any]:
    """유효 배정 없는 기존 사건에 A~D를 한 번만 배정·저장. 유효 값은 덮지 않음."""
    global _MIGRATED_ASSIGN
    if shared_cases.enabled():
        return {'ok': True, 'migrated': 0}
    with _LOCK:
        _load_unlocked()
        if _MIGRATED_ASSIGN:
            return {"ok": True, "assigned": 0, "kept": 0}
        assigned = 0
        kept = 0
        for link, cur in list(_CURRENT.items()):
            if str(cur.get("assigned_to") or "") in VALID_ASSIGNEES:
                kept += 1
                continue
            who = _pick_assignee()
            row = {
                "kind": "case_open",
                "request_id": f"migrate-assign-{link}-{_now()}",
                "link_key": link,
                "assigned_to": who,
                "cam_id": cur.get("cam_id") or "",
                "scenario": cur.get("scenario") or "",
                "subject": cur.get("subject") or "",
                "anchor_event_id": cur.get("anchor_event_id") or "",
                "event_ids": list(cur.get("event_ids") or []),
                "operator_at": _now(),
                "next_status": cur.get("status") or "new",
                "note": "담당자 자동 배정",
            }
            _append_line_unlocked(row)
            assigned += 1
        _MIGRATED_ASSIGN = True
        return {"ok": True, "assigned": assigned, "kept": kept}


def ensure_case(meta: dict[str, Any]) -> dict[str, Any]:
    """사건 최초 생성 시 담당자 A~D 1회 배정·저장. 이미 있으면 재배정하지 않음."""
    if shared_cases.enabled():
        return shared_cases.call('ensure_case', meta)
    if not isinstance(meta, dict):
        raise ValueError("object required")
    with _LOCK:
        _load_unlocked()
        link = resolve_link_key_unlocked(meta)
        if not link:
            cam = str(meta.get("cam_id") or "").strip()
            sid = str(meta.get("scenario") or "").strip()
            sub = str(meta.get("subject") or "").strip()
            anchor = str(meta.get("anchor_event_id") or "").strip()
            if not anchor:
                eids = meta.get("event_ids") or []
                if isinstance(eids, list) and eids:
                    anchor = str(eids[0])
            if cam and sid and anchor:
                link = make_link_key(cam, sid, sub, anchor)
        if not link:
            raise ValueError("link_key or event_ids/anchor required")

        cur = _CURRENT.get(link)
        if cur and str(cur.get("assigned_to") or "") in VALID_ASSIGNEES:
            _merge_meta(cur, meta)
            _CURRENT[link] = cur
            return {"ok": True, "created": False, "state": dict(cur)}

        who = _pick_assignee()
        row = {
            "kind": "case_open",
            "request_id": str(meta.get("request_id") or f"open-{link}-{_now()}"),
            "link_key": link,
            "assigned_to": who,
            "episode_id": str(meta.get("episode_id") or ""),
            "cam_id": str(meta.get("cam_id") or ""),
            "cam_code": str(meta.get("cam_code") or ""),
            "scenario": str(meta.get("scenario") or ""),
            "subject": str(meta.get("subject") or ""),
            "anchor_event_id": str(meta.get("anchor_event_id") or ""),
            "event_ids": list(meta.get("event_ids") or []),
            "title": str(meta.get("title") or ""),
            "action": str(meta.get("action") or ""),
            "grade": str(meta.get("grade") or meta.get("detection_grade") or ""),
            "level": str(meta.get("level") or ""),
            "detection_status": str(meta.get("detection_status") or ""),
            "event_first_clock": str(meta.get("first_clock") or meta.get("event_first_clock") or ""),
            "event_last_clock": str(meta.get("last_clock") or meta.get("event_last_clock") or ""),
            "related_count": int(meta.get("related_count") or 1),
            "operator_at": _now(),
            "opened_at": _now(),
            "next_status": "new",
            "note": "담당자 자동 배정",
        }
        if row["request_id"] in _SEEN_REQUESTS:
            st = _CURRENT.get(link) or {}
            return {"ok": True, "created": False, "duplicate": True, "state": dict(st)}
        _append_line_unlocked(row)
        _SEEN_REQUESTS[row["request_id"]] = {"ok": True, "entry": row, "state": dict(_CURRENT[link])}
        return {"ok": True, "created": True, "state": dict(_CURRENT[link])}


def record_observation_day(link: str):
    """실제 재생 감지 경로에서 사건당 하루 한 줄만 저장한다."""
    if shared_cases.enabled():
        return shared_cases.call('record_observation_day', link)
    with _LOCK:
        _load_unlocked()
        cur = _CURRENT.get(link)
        day = _now()[:10]
        if not cur or day in (cur.get("observed_dates") or []):
            return
        _append_line_unlocked({"kind": "observation_day", "link_key": link,
                               "observed_date": day, "operator_at": _now()})


def touch_case_observation(meta: dict[str, Any]) -> dict[str, Any]:
    """반복 관측: 메모리 메타만 갱신(JSONL 전체 재기록·재배정 없음)."""
    if shared_cases.enabled():
        return shared_cases.call('touch_case_observation', meta)
    with _LOCK:
        _load_unlocked()
        link = resolve_link_key_unlocked(meta or {})
        if not link or link not in _CURRENT:
            return {"ok": False, "error": "case not found"}
        cur = _CURRENT[link]
        before = dict(cur)
        _merge_meta(cur, meta or {})
        if meta.get("last_clock"):
            cur["event_last_clock"] = str(meta.get("last_clock"))
        if meta.get("detection_status"):
            cur["detection_status"] = str(meta.get("detection_status"))
        if meta.get("related_count") is not None:
            try:
                cur["related_count"] = int(meta.get("related_count"))
            except (TypeError, ValueError):
                pass
        if _STORE is not None and cur != before:
            _append_line_unlocked({'kind': 'case_observation', 'link_key': link,
                                   **{key: cur.get(key) for key in ('cam_id', 'cam_code', 'scenario', 'subject', 'anchor_event_id', 'title', 'action', 'grade', 'level', 'detection_status', 'event_first_clock', 'event_last_clock', 'related_count', 'event_ids')}})
        _CURRENT[link] = cur
        return {"ok": True, "state": dict(cur)}


def reopen_case(meta: dict[str, Any]) -> dict[str, Any]:
    """중요도 상승 등 재확인: 이력을 지우지 않고 확인 전으로 되돌림. 배정 유지."""
    if shared_cases.enabled():
        return shared_cases.call('reopen_case', meta)
    with _LOCK:
        _load_unlocked()
        link = resolve_link_key_unlocked(meta or {})
        if not link:
            raise ValueError("link_key required")
        cur = _CURRENT.get(link)
        if not cur:
            # 없으면 생성
            return ensure_case(meta)
        if str(cur.get("status") or "new") == "new":
            _merge_meta(cur, meta or {})
            _CURRENT[link] = cur
            return {"ok": True, "reopened": False, "state": dict(cur)}
        req = str(meta.get("request_id") or f"reopen-{link}-{_now()}")
        if req in _SEEN_REQUESTS:
            return {"ok": True, "duplicate": True, "state": dict(_CURRENT[link])}
        row = {
            "kind": "reopen",
            "request_id": req,
            "link_key": link,
            "assigned_to": cur.get("assigned_to") or "",
            "prev_status": cur.get("status"),
            "next_status": "new",
            "prev_label": response_label(cur.get("status")),
            "next_label": response_label("new"),
            "operator": str(meta.get("operator") or "system"),
            "operator_at": _now(),
            "note": str(meta.get("note") or "중요도 상승 · 재확인"),
            "cam_id": cur.get("cam_id") or "",
            "scenario": cur.get("scenario") or "",
            "subject": cur.get("subject") or "",
            "anchor_event_id": cur.get("anchor_event_id") or "",
            "event_ids": list(cur.get("event_ids") or []),
            "detection_status": str(meta.get("detection_status") or cur.get("detection_status") or ""),
            "event_last_clock": str(meta.get("last_clock") or cur.get("event_last_clock") or ""),
            "related_count": int(meta.get("related_count") or cur.get("related_count") or 0),
            "grade": str(meta.get("grade") or cur.get("grade") or ""),
            "level": str(meta.get("level") or cur.get("level") or ""),
            "title": str(meta.get("title") or cur.get("title") or ""),
        }
        _append_line_unlocked(row)
        _SEEN_REQUESTS[req] = {"ok": True, "entry": row, "state": dict(_CURRENT[link])}
        return {"ok": True, "reopened": True, "state": dict(_CURRENT[link])}


def append_response_log(entry: dict[str, Any]) -> dict[str, Any]:
    result = apply_transition(entry)
    return result.get("entry") or result.get("state") or {}


def resolve_link_key_unlocked(data: dict[str, Any]) -> str | None:
    link = str(data.get("link_key") or "").strip()
    if link:
        return link
    eids = data.get("event_ids") or []
    if isinstance(eids, list):
        for eid in eids:
            key = _EVENT_INDEX.get(str(eid))
            if key:
                return key
    anchor = str(data.get("anchor_event_id") or "").strip()
    if anchor and anchor in _EVENT_INDEX:
        return _EVENT_INDEX[anchor]
    eid = str(data.get("event_id") or "").strip()
    if eid and eid in _EVENT_INDEX:
        return _EVENT_INDEX[eid]
    cam = str(data.get("cam_id") or "").strip()
    sid = str(data.get("scenario") or "").strip()
    sub = str(data.get("subject") or "").strip()
    if not anchor:
        if isinstance(eids, list) and eids:
            anchor = str(eids[0])
        else:
            anchor = eid
    if cam and sid and anchor:
        return make_link_key(cam, sid, sub, anchor)
    return None


def resolve_link_key(data: dict[str, Any]) -> str | None:
    load_logs_into_memory()
    with _LOCK:
        return resolve_link_key_unlocked(data)


def apply_transition(data: dict[str, Any]) -> dict[str, Any]:
    """서버 권위 전이. 배정 담당자는 처리 사용자로 덮지 않음."""
    if shared_cases.enabled():
        return shared_cases.call('apply_transition', data)
    if not isinstance(data, dict):
        raise ValueError("object required")

    request_id = str(data.get("request_id") or "").strip()
    if not request_id:
        raise ValueError("request_id required")

    operator = str(data.get("operator") or "").strip()
    if not operator or operator == "—":
        raise ValueError("로그인 사용자를 확인할 수 없어 처리할 수 없습니다")

    with _LOCK:
        _load_unlocked()
        if request_id in _SEEN_REQUESTS:
            prev = _SEEN_REQUESTS[request_id]
            return {
                "ok": True,
                "duplicate": True,
                "entry": prev.get("entry"),
                "state": prev.get("state"),
            }

        link = resolve_link_key_unlocked(data)
        if not link:
            raise ValueError("link_key or event_ids/anchor required")

        cur = _CURRENT.get(link)
        if not cur:
            # 전이 전 사건 없으면 배정과 함께 생성
            ensure_meta = dict(data)
            ensure_meta["request_id"] = f"auto-open-{request_id}"
            # ensure_case 는 락 재진입 불가 → 인라인
            who = _pick_assignee()
            open_row = {
                "kind": "case_open",
                "request_id": ensure_meta["request_id"],
                "link_key": link,
                "assigned_to": who,
                "cam_id": str(data.get("cam_id") or ""),
                "cam_code": str(data.get("cam_code") or ""),
                "scenario": str(data.get("scenario") or ""),
                "subject": str(data.get("subject") or ""),
                "anchor_event_id": str(data.get("anchor_event_id") or ""),
                "event_ids": list(data.get("event_ids") or []),
                "title": str(data.get("title") or ""),
                "detection_status": str(data.get("detection_status") or ""),
                "event_first_clock": str(data.get("event_first_clock") or ""),
                "event_last_clock": str(data.get("event_last_clock") or ""),
                "related_count": int(data.get("related_count") or 1),
                "grade": str(data.get("detection_grade") or data.get("grade") or ""),
                "level": str(data.get("level") or ""),
                "operator_at": _now(),
                "next_status": "new",
            }
            _append_line_unlocked(open_row)
            cur = _CURRENT[link]

        server_status = str((cur or {}).get("status") or "new")
        client_prev = str(data.get("prev_status") or "new")
        nxt = str(data.get("next_status") or "")

        if not can_transition(server_status, nxt):
            if server_status == nxt and cur:
                out = {
                    "ok": True,
                    "duplicate": True,
                    "entry": None,
                    "state": dict(cur),
                    "warning": "already_in_target_status",
                }
                _SEEN_REQUESTS[request_id] = {"ok": True, "entry": None, "state": dict(cur)}
                return out
            raise ValueError(
                f"invalid transition server={server_status} client_prev={client_prev} → {nxt}"
            )

        note = str(data.get("note") or "").strip()
        if note_required(nxt) and not note:
            raise ValueError("note required for acting/done")

        eids = data.get("event_ids") or []
        if not isinstance(eids, list):
            eids = []
        eids = [str(x) for x in eids if x]
        anchor = str(data.get("anchor_event_id") or (eids[0] if eids else "") or "")

        row = {
            "kind": "transition",
            "request_id": request_id,
            "link_key": link,
            "episode_id": str(data.get("episode_id") or ""),
            "cam_id": str(data.get("cam_id") or (cur or {}).get("cam_id") or ""),
            "cam_code": str(data.get("cam_code") or (cur or {}).get("cam_code") or ""),
            "scenario": str(data.get("scenario") or (cur or {}).get("scenario") or ""),
            "subject": str(data.get("subject") or (cur or {}).get("subject") or ""),
            "anchor_event_id": anchor or str((cur or {}).get("anchor_event_id") or ""),
            "event_ids": list(dict.fromkeys([*(((cur or {}).get("event_ids")) or []), *eids])),
            "assigned_to": str((cur or {}).get("assigned_to") or ""),
            "operator": operator,
            "prev_status": server_status,
            "next_status": nxt,
            "prev_label": response_label(server_status),
            "next_label": response_label(nxt),
            "note": note,
            "operator_at": _now(),  # 서버 시각 권위
            "event_first_clock": str(
                data.get("event_first_clock") or (cur or {}).get("event_first_clock") or ""
            ),
            "event_last_clock": str(
                data.get("event_last_clock") or (cur or {}).get("event_last_clock") or ""
            ),
            "detection_status": str(
                data.get("detection_status") or (cur or {}).get("detection_status") or ""
            ),
            "related_count": int(
                data.get("related_count") or (cur or {}).get("related_count") or 0
            ),
            "title": str(data.get("title") or (cur or {}).get("title") or ""),
            "grade": str(data.get("detection_grade") or data.get("grade") or (cur or {}).get("grade") or ""),
            "level": str(data.get("level") or (cur or {}).get("level") or ""),
            "disclaimer": "조치 완료는 현장 안전 보증이 아님",
        }

        _append_line_unlocked(row)
        state = dict(_CURRENT[link])
        _SEEN_REQUESTS[request_id] = {"ok": True, "entry": row, "state": state}
        if len(_SEEN_REQUESTS) > 2000:
            for key in list(_SEEN_REQUESTS.keys())[:500]:
                _SEEN_REQUESTS.pop(key, None)
        return {"ok": True, "duplicate": False, "entry": row, "state": state}


def validate_client_payload(data: dict[str, Any]) -> dict[str, Any]:
    result = apply_transition(data)
    if not result.get("ok"):
        raise ValueError(result.get("error") or "failed")
    return result.get("entry") or result.get("state") or {}


def get_states_for_event_ids(event_ids: list[str]) -> dict[str, Any]:
    load_logs_into_memory()
    with _LOCK:
        out = {}
        err = _LOG_READ_ERROR
        for eid in event_ids or []:
            link = _EVENT_INDEX.get(str(eid))
            if link and link in _CURRENT:
                out[str(eid)] = dict(_CURRENT[link])
        return {"ok": err is None, "error": err, "by_event_id": out}


def get_state_by_link(link_key: str) -> dict[str, Any]:
    load_logs_into_memory()
    with _LOCK:
        cur = _CURRENT.get(str(link_key or ""))
        return {
            "ok": _LOG_READ_ERROR is None,
            "error": _LOG_READ_ERROR,
            "state": dict(cur) if cur else None,
        }


def history_for_link(link_key: str = "", event_ids: list[str] | None = None) -> dict[str, Any]:
    if shared_cases.enabled() or _STORE is not None:
        load_logs_into_memory()
        link = str(link_key or '').strip()
        if not link and event_ids:
            with _LOCK:
                link = next((_EVENT_INDEX[e] for e in event_ids if e in _EVENT_INDEX), '')
        if not link:
            return {'ok': False, 'error': '이력을 연결할 link_key/event_id 가 없습니다(추정 연결 안 함)', 'history': []}
        try:
            rows = [row for row in iter_history() if str(row.get('link_key') or '') == link and row.get('kind') not in ('observation_day', 'case_observation')]
        except (OSError, ValueError) as exc:
            return {'ok': False, 'error': f'조치 이력 읽기 실패: {exc}', 'history': [], 'link_key': link}
        return {'ok': True, 'error': None, 'history': rows, 'link_key': link}
    load_logs_into_memory()
    link = str(link_key or "").strip()
    if not link and event_ids:
        with _LOCK:
            for eid in event_ids:
                link = _EVENT_INDEX.get(str(eid)) or link
                if link:
                    break
    path = log_path()
    rows: list[dict] = []
    if not link:
        return {
            "ok": False,
            "error": "이력을 연결할 link_key/event_id 가 없습니다(추정 연결 안 함)",
            "history": [],
        }
    if not os.path.isfile(path):
        return {"ok": True, "error": None, "history": [], "link_key": link}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                row = _parse_line(line)
                if row is None:
                    continue
                if str(row.get("link_key") or "") == link and row.get("kind") != "observation_day":
                    rows.append(row)
    except OSError as exc:
        return {"ok": False, "error": f"조치 이력 읽기 실패: {exc}", "history": [], "link_key": link}
    return {"ok": True, "error": None, "history": rows, "link_key": link}


def _merge_live_episode(cur: dict[str, Any], ep: dict[str, Any]) -> dict[str, Any]:
    out = dict(cur)
    if ep.get("last_clock"):
        out["event_last_clock"] = str(ep.get("last_clock"))
    if ep.get("first_clock") and not out.get("event_first_clock"):
        out["event_first_clock"] = str(ep.get("first_clock"))
    if ep.get("detection_status"):
        out["detection_status"] = str(ep.get("detection_status"))
        out["detection_fresh"] = True
    if ep.get("related_count") is not None:
        try:
            out["related_count"] = int(ep.get("related_count"))
        except (TypeError, ValueError):
            pass
    for key in ("title", "action", "cam_code", "grade", "level", "cam_id", "scenario", "subject"):
        if ep.get(key):
            out[key] = ep.get(key)
    if ep.get("event_ids"):
        out["event_ids"] = list(ep.get("event_ids") or out.get("event_ids") or [])
    return out


_SCENARIO_FALLBACK = {
    "collision": "근접 위험",
    "zone": "구역 진입",
    "dwell": "체류 초과",
    "ppe": "PPE 미착용",
    "fire": "불꽃 의심",
}


def _enrich_case_display(item: dict[str, Any]) -> dict[str, Any]:
    """목록/상세용 표시 보강(저장 필드를 추정으로 덮지 않음)."""
    out = dict(item)
    if not out.get("title"):
        scen = str(out.get("scenario") or "")
        reason = _SCENARIO_FALLBACK.get(scen, scen or "경보")
        place = str(out.get("cam_code") or out.get("cam_id") or "").strip()
        grade = str(out.get("grade") or "")
        if not grade:
            grade = "위험" if out.get("level") == "hot" else ("주의" if out.get("level") == "warn" else "")
        out["title"] = " · ".join(p for p in (grade, place, reason) if p)
    if not out.get("cam_code") and out.get("cam_id"):
        try:
            from .config import CAM_BY_ID

            cam = CAM_BY_ID.get(str(out.get("cam_id")), {}) or {}
            out["cam_code"] = str(cam.get("cam") or "").upper()
        except Exception:
            pass
    if not out.get("grade") and out.get("level") == "hot":
        out["grade"] = "위험"
    elif not out.get("grade") and out.get("level") == "warn":
        out["grade"] = "주의"
    return out


def list_cases(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    """사건 목록. 기본=미완료. 오늘 완료=처리(done_at) 날짜 기준."""
    from .alert_ops import snapshot_episodes

    load_logs_into_memory()
    migrate_missing_assignees()
    filters = filters or {}
    live = {str(ep.get("link_key") or ""): ep for ep in snapshot_episodes() if ep.get("link_key")}

    with _LOCK:
        cases = []
        for link, cur in _CURRENT.items():
            item = dict(cur)
            if link in live:
                item = _merge_live_episode(item, live[link])
            else:
                item["detection_fresh"] = False
            cases.append(_enrich_case_display(item))

    # 세션에만 있고 아직 case_open 안 된 에피소드 → ensure (드묾)
    for link, ep in live.items():
        if link and link not in {c["link_key"] for c in cases}:
            try:
                st = ensure_case(ep)
                if st.get("state"):
                    cases.append(dict(st["state"]))
            except ValueError:
                continue

    def _match(c: dict) -> bool:
        status = str(c.get("status") or "new")
        open_only = filters.get("open_only", True)
        if open_only and status == "done":
            return False
        want_status = str(filters.get("status") or "").strip()
        if want_status and want_status != "all" and status != want_status:
            return False
        cam = str(filters.get("cam_id") or "").strip()
        if cam and cam != "all" and str(c.get("cam_id") or "") != cam:
            return False
        scen = str(filters.get("scenario") or "").strip()
        if scen and scen != "all" and str(c.get("scenario") or "") != scen:
            return False
        sev = str(filters.get("severity") or "").strip()
        if sev and sev != "all":
            grade = str(c.get("grade") or "")
            level = str(c.get("level") or "")
            if sev == "위험" and grade != "위험" and level != "hot":
                return False
            if sev == "주의" and grade != "주의" and level != "warn":
                return False
        assignee = str(filters.get("assigned_to") or "").strip()
        if assignee and assignee != "all" and str(c.get("assigned_to") or "") != assignee:
            return False
        # 영상 발생 기간: first_clock 문자열 HH:MM:SS 또는 전체 일시 — 단순 포함 필터
        date_from = str(filters.get("date_from") or "").strip()
        date_to = str(filters.get("date_to") or "").strip()
        opened = str(c.get("opened_at") or c.get("operator_at") or "")
        first = str(c.get("event_first_clock") or "")
        # opened_at 우선(벽시계), 없으면 스킵
        day = opened[:10] if len(opened) >= 10 else ""
        if date_from and day and day < date_from:
            return False
        if date_to and day and day > date_to:
            return False
        _ = first  # 영상 시각은 목록 표시용; 기간 필터는 처리/개설 일자
        return True

    filtered = [c for c in cases if _match(c)]

    def sort_key(c: dict):
        status = str(c.get("status") or "new")
        st_rank = {"new": 0, "acked": 1, "acting": 2, "done": 3}.get(status, 9)
        hot = 0 if (c.get("grade") == "위험" or c.get("level") == "hot") else 1
        recent = str(c.get("event_last_clock") or c.get("operator_at") or "")
        # 최근 발생 우선을 위해 recent 는 역순 정렬되도록 음수 키가 없어 문자열 reverse
        return (st_rank, hot, recent)

    filtered.sort(key=sort_key)
    # 동일 우선순위 내 최근 시각 우선
    from itertools import groupby

    ordered: list[dict] = []
    filtered.sort(key=lambda c: (sort_key(c)[0], sort_key(c)[1]))
    for _, group in groupby(filtered, key=lambda c: (sort_key(c)[0], sort_key(c)[1])):
        chunk = list(group)
        chunk.sort(key=lambda c: str(c.get("event_last_clock") or c.get("operator_at") or ""), reverse=True)
        ordered.extend(chunk)
    filtered = ordered

    today = _now()[:10]
    # 요약: 전체 저장 사건 기준(필터와 무관) — 사용자 요청: 기준 명확히. 필터 결과면 표기.
    summary_source = "전체 저장 기준"
    with _LOCK:
        all_cases = list(_CURRENT.values())
    summary = {
        "new": sum(1 for c in all_cases if c.get("status") == "new"),
        "acked": sum(1 for c in all_cases if c.get("status") == "acked"),
        "acting": sum(1 for c in all_cases if c.get("status") == "acting"),
        "done_today": sum(
            1
            for c in all_cases
            if c.get("status") == "done" and str(c.get("done_at") or "").startswith(today)
        ),
        "source": summary_source,
    }

    return {
        "ok": _LOG_READ_ERROR is None,
        "error": _LOG_READ_ERROR,
        "cases": filtered,
        "summary": summary,
        "filter_count": len(filtered),
        "assignees": list(DEMO_ASSIGNEES),
    }


def case_detail(link_key: str) -> dict[str, Any]:
    load_logs_into_memory()
    migrate_missing_assignees()
    from .alert_ops import snapshot_episodes

    live = {str(ep.get("link_key") or ""): ep for ep in snapshot_episodes() if ep.get("link_key")}
    st = get_state_by_link(link_key)
    state = st.get("state")
    if not st.get("ok"):
        return {"ok": False, "error": st.get("error"), "state": None, "history": []}
    if not state:
        return {"ok": False, "error": "사건을 찾을 수 없습니다", "state": None, "history": []}
    if link_key in live:
        state = _merge_live_episode(state, live[link_key])
        state["detection_fresh"] = True
    else:
        state["detection_fresh"] = False
    state = _enrich_case_display(state)
    hist = history_for_link(link_key=link_key)
    return {
        "ok": True,
        "error": None,
        "state": state,
        "history": hist.get("history") or [],
    }


def iter_history():
    """Stream the audit log on explicit report load; never mutate source records."""
    if shared_cases.enabled():
        result = load_logs_into_memory()
        if not result.get('ok'):
            raise ValueError(result.get('error'))
        yield from list(_REMOTE_ROWS)
    elif _STORE is not None:
        yield from _STORE.rows()
    elif os.path.isfile(log_path()):
        with open(log_path(), encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = _parse_line(line)
                if row is None:
                    raise ValueError("손상된 조치 이력이 있어 통계를 계산하지 못했습니다")
                yield row
