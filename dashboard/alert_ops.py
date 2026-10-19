# 운영 경보 계층: 원본 이벤트와 분리된 에피소드 묶음·알림음 결정
"""감지 판정은 바꾸지 않는다. notify()가 이 모듈의 process_alerts()를 사용한다.

적용 범위:
- 알림음·종 목록 갱신 억제: 시연 세션(epoch, 로그인/새로고침 시 리셋)
- 운영자 확인함: 브라우저 페이지 메모리(서버에 사용자별 영속 저장 없음)
"""

from __future__ import annotations

import threading
from typing import Any

import pandas as pd

from .alert_policy import EPISODE_IDLE_GAP_SECONDS, MAX_OPERATOR_ALERTS
from .config import CAM_BY_ID
from .timeline import event_seconds

_LOCK = threading.Lock()
_STATE: dict[str, Any] = {
    "epoch": 0,
    "seen_event_ids": set(),
    "episodes": {},  # episode_id -> dict
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


def alert_epoch() -> int:
    with _LOCK:
        return int(_STATE.get("epoch") or 0)


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
    """묶음용 대상 키. 근거 없으면 None → event_id 단독 경보."""
    sid = str(_cell(row, "scenario") or "")
    person_no = _cell(row, "person_no")
    worker = str(_cell(row, "worker") or "").strip()
    tid = str(_cell(row, "track_id") or "").strip()

    if sid == "fire":
        if tid:
            return f"fire:{tid}"
        return None

    if person_no not in ("", None, 0, "0"):
        try:
            return f"person:{int(float(person_no))}"
        except (TypeError, ValueError):
            return f"person:{person_no}"

    if worker and worker not in ("불꽃",):
        return f"worker:{worker}"

    if tid:
        return f"track:{tid}"

    return None


def episode_id_for_row(row, epoch: int | None = None) -> str:
    ep = alert_epoch() if epoch is None else int(epoch)
    area = str(_cell(row, "area") or "")
    sid = str(_cell(row, "scenario") or "")
    sub = subject_key(row)
    if sub is None:
        eid = str(_cell(row, "event_id") or "")
        return f"{ep}|{area}|{sid}|alone:{eid}"
    return f"{ep}|{area}|{sid}|{sub}"


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


def process_alerts(frame) -> tuple[str | None, list[dict]]:
    """라이브 구간의 주의/위험 행 → (sound kind, toast ops).

    - 같은 event_id 재조회: 무시
    - 같은 에피소드·같은/낮은 중요도: 갱신만(소리 없음)
    - 주의→위험: upgrade + 소리
    - 대상 없음: event_id별 독립
    """
    if frame is None or len(frame) == 0:
        return None, []

    col = "grade" if "grade" in frame.columns else "status"
    danger = frame[frame[col].isin(["주의", "위험"])]
    if len(danger) == 0:
        return None, []

    if "timestamp" in danger.columns:
        danger = danger.sort_values(["timestamp", "event_id"], kind="mergesort")

    secs = event_seconds(danger)
    ops: list[dict] = []
    sound: str | None = None

    with _LOCK:
        epoch = int(_STATE.get("epoch") or 0)
        seen: set = _STATE["seen_event_ids"]
        episodes: dict = _STATE["episodes"]

        for idx, (_, row) in enumerate(danger.iterrows()):
            eid = str(_cell(row, "event_id") or "")
            if not eid or eid in seen:
                continue
            seen.add(eid)

            grade = str(_cell(row, col) or "")
            rank = _severity_rank(grade)
            if rank <= 0:
                continue

            try:
                t_sec = float(secs.iloc[idx])
            except Exception:
                t_sec = 0.0

            base_id = episode_id_for_row(row, epoch=epoch)
            ep = episodes.get(base_id)

            # 유휴 간격이 길면 새 에피소드(같은 대상이라도 종료 후 재발생)
            if ep is not None:
                idle = t_sec - float(ep.get("last_sec") or t_sec)
                if idle > float(EPISODE_IDLE_GAP_SECONDS) and rank > 0:
                    # 이전 에피소드와 분리: 키에 시작 시각 접미사
                    base_id = f"{base_id}|t{int(t_sec * 10)}"
                    ep = None

            cam_id = str(_cell(row, "area") or "").strip()
            cam = CAM_BY_ID.get(cam_id, {})
            cam_code = str(cam.get("cam") or _cell(row, "camera") or "").upper()
            clock = _clock(row)
            title = _title_for_row(row, grade)
            action = _action_for_row(row)

            if ep is None:
                ep = {
                    "episode_id": base_id,
                    "max_rank": rank,
                    "first_clock": clock,
                    "last_clock": clock,
                    "first_sec": t_sec,
                    "last_sec": t_sec,
                    "event_ids": [eid],
                    "related_count": 1,
                    "level": "hot" if rank >= 2 else "warn",
                    "grade": grade,
                    "cam_id": cam_id,
                    "cam_code": cam_code,
                    "title": title,
                    "action": action,
                }
                episodes[base_id] = ep
                op = "new"
                sound = "hot" if rank >= 2 else (sound or "warn")
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
                ep["grade"] = grade if rank >= prev_rank else ep.get("grade")
                if rank > prev_rank:
                    ep["max_rank"] = rank
                    ep["level"] = "hot" if rank >= 2 else "warn"
                    op = "upgrade"
                    sound = "hot" if rank >= 2 else (sound or "warn")
                else:
                    op = "update"
                    # 같은 단계 반복: 소리 없음

            text = (
                f"{ep['cam_code']} / 최초 {ep['first_clock']} / 최근 {ep['last_clock']}"
            )
            if int(ep["related_count"]) > 1:
                text = f"{text} · 관련 기록 {int(ep['related_count'])}건"

            ops.append(
                {
                    "op": op,
                    "episode_id": ep["episode_id"],
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
                }
            )

        # 목록 상한: 서버 에피소드 맵만 정리(클라이언트도 MAX 사용)
        if len(episodes) > MAX_OPERATOR_ALERTS * 2:
            # 오래된 last_sec 기준 정리
            ordered = sorted(episodes.items(), key=lambda kv: kv[1].get("last_sec") or 0)
            for key, _ in ordered[: max(0, len(ordered) - MAX_OPERATOR_ALERTS)]:
                episodes.pop(key, None)

    return sound, ops
