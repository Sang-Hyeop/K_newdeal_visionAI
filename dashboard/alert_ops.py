# 운영 경보 계층: 원본 이벤트와 분리된 에피소드 묶음·알림음 결정
"""감지 판정은 바꾸지 않는다. notify()가 이 모듈의 process_alerts()를 사용한다.

적용 범위:
- 알림음·종 목록 갱신 억제: 시연 세션(epoch, 로그인/새로고침 시 리셋)
- 운영자 확인함: 브라우저 페이지 메모리(서버에 사용자별 영속 저장 없음)
- 조치 복원용 link_key: epoch 없는 cam|scenario|subject|e0:anchor_event_id
"""

from __future__ import annotations

import threading
from typing import Any

import pandas as pd

from .alert_policy import EPISODE_IDLE_GAP_SECONDS, MAX_OPERATOR_ALERTS
from .alert_response import record_observation_day, ensure_case, make_link_key, reopen_case, touch_case_observation
from .config import CAM_BY_ID
from .timeline import event_seconds

_LOCK = threading.Lock()
_STATE: dict[str, Any] = {
    "epoch": 0,
    "seen_event_ids": set(),
    "episodes": {},  # episode_id -> dict (과거·현재 모두 보관)
    "active_by_base": {},  # 논리 base_id -> 현재 활성 episode_id
}


def reset_alert_ops(epoch: int | None = None):
    """로그인·새로고침 시 세션 경보 상태 초기화."""
    with _LOCK:
        if epoch is None:
            _STATE["epoch"] = int(_STATE.get("epoch") or 0) + 1
        else:
            _STATE["epoch"] = int(epoch)
        _STATE["seen_event_ids"] = set()
        _STATE["episodes"] = {}
        _STATE["active_by_base"] = {}


def alert_epoch() -> int:
    with _LOCK:
        return int(_STATE.get("epoch") or 0)


def snapshot_episodes() -> list[dict]:
    """세션 내 에피소드 스냅샷(조치 관리 목록 병합용)."""
    with _LOCK:
        return [dict(v) for v in (_STATE.get("episodes") or {}).values()]


def _cell(row, key, default=""):
    try:
        value = row[key] if hasattr(row, "index") and key in row.index else row.get(key, default)
    except Exception:
        return default
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return value


def _clock(row) -> str:
    ts = str(_cell(row, "timestamp") or "")
    if " " in ts:
        part = ts.split(" ", 1)[1]
        return part[:8] if len(part) >= 8 else part
    return ts[:8] if ts else "—"


def _track_core(tid: str) -> str:
    s = str(tid or "").strip()
    if not s:
        return ""
    if ":" in s:
        return s.rsplit(":", 1)[-1]
    return s


def subject_key(row) -> str | None:
    """묶음용 대상 키. 근거 없으면 None → event_id 단독 경보.

    근접(collision): vehicle_track_id 가 있으면 작업자–차량 쌍으로 구분.
    차량 식별이 없으면 사람 키만 쓰고, 다른 차량과 임의로 합치지 않는다.
    """
    sid = str(_cell(row, "scenario") or "")
    person_no = _cell(row, "person_no")
    worker = str(_cell(row, "worker") or "").strip()
    tid = str(_cell(row, "track_id") or "").strip()
    vtid = str(_cell(row, "vehicle_track_id") or "").strip()

    if sid == "fire":
        if tid:
            return f"fire:{tid}"
        return None

    person_part = None
    if person_no not in ("", None, 0, "0"):
        try:
            person_part = f"person:{int(float(person_no))}"
        except (TypeError, ValueError):
            person_part = f"person:{person_no}"
    elif worker and worker not in ("불꽃",):
        person_part = f"worker:{worker}"
    elif tid:
        person_part = f"track:{tid}"

    if person_part is None:
        return None

    if sid == "collision" and vtid:
        return f"{person_part}+veh:{_track_core(vtid)}"
    return person_part


def episode_base_id_for_row(row, epoch: int | None = None) -> str:
    """유휴 분리 접미사 없는 논리 키."""
    ep = alert_epoch() if epoch is None else int(epoch)
    area = str(_cell(row, "area") or "")
    sid = str(_cell(row, "scenario") or "")
    sub = subject_key(row)
    if sub is None:
        eid = str(_cell(row, "event_id") or "")
        return f"{ep}|{area}|{sid}|alone:{eid}"
    return f"{ep}|{area}|{sid}|{sub}"


def episode_id_for_row(row, epoch: int | None = None) -> str:
    """하위 호환: 논리 base id (활성 접미사 없음)."""
    return episode_base_id_for_row(row, epoch=epoch)


def _severity_rank(grade: str) -> int:
    if grade == "위험":
        return 2
    if grade == "주의":
        return 1
    return 0


def _action_for_row(row) -> str:
    from .display_text import fire_evidence_lines
    from .ui import evidence_lines_for_row

    sid = str(_cell(row, "scenario") or "")
    status = str(_cell(row, "status") or "")
    if sid == "fire":
        return fire_evidence_lines(status)[1]
    _evidence, check = evidence_lines_for_row(row)
    return check


def _title_for_row(row, grade: str) -> str:
    from .ui import place_label_for_cam, reason_label_for_row

    cam_id = str(_cell(row, "area") or "")
    cam = CAM_BY_ID.get(cam_id, {})
    place = place_label_for_cam(cam) or str(_cell(row, "zone") or "")
    reason = reason_label_for_row(row)
    sev = grade if grade in ("위험", "주의") else "알림"
    return " · ".join(p for p in (sev, place, reason) if p)


def _subject_for_link(row) -> str:
    sub = subject_key(row)
    if sub:
        return sub
    return f"alone:{_cell(row, 'event_id') or ''}"


def process_alerts(frame) -> tuple[str | None, list[dict]]:
    """라이브 구간의 주의/위험 행 → (sound kind, toast ops).

    - 같은 event_id 재조회: 무시
    - 같은 에피소드·같은/낮은 중요도: 갱신만(소리 없음)
    - 주의 new: 목록만(sound=None) · 주의→위험: upgrade + hot
    - 한 배치에 위험이 여러 개여도 sound kind는 hot 한 번
    - 대상 없음: event_id별 독립
    - 유휴 분리 후: active_by_base 로 최신 묶음에만 연결 (과거 에피소드와 구분)
    """
    if frame is None or len(frame) == 0:
        return None, []

    col = "grade" if "grade" in frame.columns else "status"
    mask = frame[col].isin(["주의", "위험"])
    if not mask.any():
        return None, []
    want = (
        "event_id", col, "status", "grade", "timestamp", "scenario",
        "area", "camera", "zone", "person_no", "worker", "track_id",
        "vehicle_track_id", "distance_px", "dwell_sec", "message",
    )
    cols = list(dict.fromkeys(c for c in want if c in frame.columns))
    danger = frame.loc[mask, cols]
    if "timestamp" in danger.columns:
        sort_cols = ["timestamp"] + (["event_id"] if "event_id" in danger.columns else [])
        danger = danger.sort_values(sort_cols, kind="mergesort")

    secs = event_seconds(danger)
    records = danger.to_dict("records")
    sec_vals = secs.to_numpy(dtype=float, copy=False)
    ops: list[dict] = []
    sound: str | None = None
    case_hooks: list[tuple[str, dict]] = []

    with _LOCK:
        epoch = int(_STATE.get("epoch") or 0)
        seen: set = _STATE["seen_event_ids"]
        episodes: dict = _STATE["episodes"]
        active_by_base: dict = _STATE["active_by_base"]

        for idx, row in enumerate(records):
            eid = str(_cell(row, "event_id") or "")
            if not eid or eid in seen:
                continue
            seen.add(eid)

            grade = str(_cell(row, col) or "")
            rank = _severity_rank(grade)
            if rank <= 0:
                continue

            try:
                t_sec = float(sec_vals[idx])
            except Exception:
                t_sec = 0.0

            base_id = episode_base_id_for_row(row, epoch=epoch)
            active_id = active_by_base.get(base_id)
            ep = episodes.get(active_id) if active_id else None

            # 유휴 간격이 길면 새 에피소드. 과거 키는 episodes에 남기고 active만 교체.
            # (묶음 분리 ≠ 현장 위험 종료 기록)
            if ep is not None:
                idle = t_sec - float(ep.get("last_sec") or t_sec)
                if idle > float(EPISODE_IDLE_GAP_SECONDS) and rank > 0:
                    active_id = f"{base_id}|t{int(t_sec * 10)}"
                    ep = None

            cam_id = str(_cell(row, "area") or "").strip()
            cam = CAM_BY_ID.get(cam_id, {})
            cam_code = str(cam.get("cam") or _cell(row, "camera") or "").upper()
            clock = _clock(row)
            title = _title_for_row(row, grade)
            action = _action_for_row(row)
            det_status = str(_cell(row, "status") or grade)
            subject = _subject_for_link(row)
            scenario = str(_cell(row, "scenario") or "")

            if ep is None:
                ep_id = active_id or base_id
                link = make_link_key(cam_id, scenario, subject, eid)
                ep = {
                    "episode_id": ep_id,
                    "base_id": base_id,
                    "link_key": link,
                    "anchor_event_id": eid,
                    "subject": subject,
                    "scenario": scenario,
                    "max_rank": rank,
                    "first_clock": clock,
                    "last_clock": clock,
                    "first_sec": t_sec,
                    "last_sec": t_sec,
                    "event_ids": [eid],
                    "related_count": 1,
                    "level": "hot" if rank >= 2 else "warn",
                    "grade": grade,
                    "detection_status": det_status,
                    "cam_id": cam_id,
                    "cam_code": cam_code,
                    "title": title,
                    "action": action,
                    "assigned_to": "",
                }
                episodes[ep_id] = ep
                active_by_base[base_id] = ep_id
                op = "new"
                if rank >= 2:
                    sound = "hot"
            else:
                prev_rank = int(ep.get("max_rank") or 0)
                ep["last_clock"] = clock
                ep["last_sec"] = t_sec
                ep["event_ids"].append(eid)
                ep["related_count"] = len(ep["event_ids"])
                ep["cam_id"] = cam_id or ep.get("cam_id")
                ep["cam_code"] = cam_code or ep.get("cam_code")
                ep["title"] = title
                ep["action"] = action
                ep["detection_status"] = det_status
                ep["grade"] = grade if rank >= prev_rank else ep.get("grade")
                if rank > prev_rank:
                    ep["max_rank"] = rank
                    ep["level"] = "hot" if rank >= 2 else "warn"
                    op = "upgrade"
                    if rank >= 2:
                        sound = "hot"
                else:
                    op = "update"

            # 락 밖에서 저장 계층 호출(교착 방지)
            case_hooks.append((op, dict(ep)))

            text = (
                f"{ep['cam_code']} / 최초 {ep['first_clock']} / 최근 {ep['last_clock']}"
            )
            if int(ep["related_count"]) > 1:
                text = f"{text} · 관련 기록 {int(ep['related_count'])}건"

            ops.append(
                {
                    "op": op,
                    "episode_id": ep["episode_id"],
                    "link_key": ep.get("link_key") or "",
                    "anchor_event_id": ep.get("anchor_event_id") or "",
                    "event_ids": list(ep.get("event_ids") or []),
                    "subject": ep.get("subject") or "",
                    "scenario": ep.get("scenario") or scenario,
                    "level": ep["level"],
                    "severity_label": "위험" if ep["level"] == "hot" else "주의",
                    "title": ep["title"],
                    "text": text,
                    "cam_id": ep.get("cam_id") or "",
                    "cam_code": ep.get("cam_code") or "",
                    "first_clock": ep["first_clock"],
                    "last_clock": ep["last_clock"],
                    "related_count": int(ep["related_count"]),
                    "action": ep.get("action") or "",
                    "ack_reset": op == "upgrade",
                    "event_id": eid,
                    "detection_status": ep.get("detection_status") or det_status,
                    "detection_grade": ep.get("grade") or grade,
                    "assigned_to": ep.get("assigned_to") or "",
                }
            )

        if len(episodes) > MAX_OPERATOR_ALERTS * 2:
            ordered = sorted(episodes.items(), key=lambda kv: kv[1].get("last_sec") or 0)
            drop_n = max(0, len(ordered) - MAX_OPERATOR_ALERTS)
            for key, _ in ordered[:drop_n]:
                ep_old = episodes.pop(key, None)
                if not ep_old:
                    continue
                b = ep_old.get("base_id")
                if b and active_by_base.get(b) == key:
                    active_by_base.pop(b, None)

    # 사건 배정·관측 갱신·중요도 상승 재오픈 (원본 이벤트는 변경하지 않음)
    for hop, ep_snap in case_hooks:
        try:
            if hop == "new":
                st = ensure_case(ep_snap)
                assigned = str((st.get("state") or {}).get("assigned_to") or "")
                if assigned:
                    for item in ops:
                        if item.get("link_key") == ep_snap.get("link_key"):
                            item["assigned_to"] = assigned
            elif hop == "upgrade":
                reopen_case(ep_snap)
                touch_case_observation(ep_snap)
            else:
                touch_case_observation(ep_snap)
            record_observation_day(str(ep_snap.get("link_key") or ""))
        except Exception:
            continue

    return sound, ops
