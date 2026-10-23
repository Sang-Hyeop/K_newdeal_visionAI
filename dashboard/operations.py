# 역할: 저장된 사건과 처리 이력을 운영 통계로 집계합니다.
"""저장된 사건과 처리 이력을 운영 통계로 집계합니다."""

from collections import Counter
from datetime import datetime
from html import escape
from statistics import mean

from . import alert_response
from .config import CAM_BY_ID

_FEATURES = {
    "collision": "작업자–지게차 근접",
    "zone": "위험구역 침범",
    "ppe": "안전모",
    "dwell": "통로 체류",
    "fire": "불꽃 의심",
}


def operational_metrics(cases, period="전체", histories=None, now=None):
    """One unique stored link per case. Elapsed times use operator clocks only."""
    today = (now or datetime.now()).strftime("%Y-%m-%d")
    unique = {c["link_key"]: c for c in cases if c.get("link_key")}
    selected = [
        c
        for c in unique.values()
        if period != "오늘 등록" or today in (c.get("observed_dates") or [])
    ]
    ack, done = [], []
    for c in selected:
        rows = (histories or {}).get(c["link_key"], [])
        try:
            opened = datetime.fromisoformat(c["opened_at"])
        except (ValueError, KeyError, TypeError):
            continue
        for state, values in (("acked", ack), ("done", done)):
            stamps = []
            for row in rows:
                if (
                    row.get("kind", "transition") != "transition"
                    or row.get("next_status") != state
                ):
                    continue
                try:
                    delta = (
                        datetime.fromisoformat(row["operator_at"]) - opened
                    ).total_seconds()
                    if delta >= 0:
                        stamps.append(delta)
                except (ValueError, KeyError, TypeError):
                    pass
            if stamps:
                values.append(min(stamps))
    return {
        "total": len(selected),
        "unfinished": sum(c.get("status") != "done" for c in selected),
        "states": Counter(c.get("status", "new") for c in selected),
        "cameras": Counter(c.get("cam_id") or "미상" for c in selected),
        "features": Counter(c.get("scenario") or "미상" for c in selected),
        "mean_ack_seconds": mean(ack) if ack else None,
        "ack_samples": len(ack),
        "mean_done_seconds": mean(done) if done else None,
        "done_samples": len(done),
    }


def operations_html(period="전체"):
    from .ui import card

    result = alert_response.list_cases({"open_only": False})
    if not result.get("ok"):
        return card(
            "운영 통계 조회 실패: "
            + escape(str(result.get("error") or "저장 기록 확인 필요"))
        )
    cases = result.get("cases") or []
    # Read the audit log once on explicit refresh, never once per case or on a timer.
    histories = {}
    try:
        path = alert_response.log_path()
        from pathlib import Path

        if alert_response.shared_cases.enabled() or Path(path).is_file():
            for row in alert_response.iter_history():
                histories.setdefault(row.get("link_key"), []).append(row)
    except (OSError, ValueError) as exc:
        return card("조치 이력 조회 실패: " + escape(str(exc)))
    m = operational_metrics(cases, period, histories)

    tiles = [
        ("등록 사건", f"{m['total']}건"),
        ("미완료", f"{m['unfinished']}건"),
    ]
    out = (
        "<p>집계 갱신: "
        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        + " · 최신 값은 새로고침으로 조회</p>"
    )
    out += (
        '<div class="sisun-cases-summary">'
        + "".join(
            '<div class="sisun-cases-sum"><div class="lab">'
            + escape(k)
            + '</div><div class="num">'
            + escape(v)
            + "</div></div>"
            for k, v in tiles
        )
        + "</div>"
    )

    def bars(title, counts, labels):
        high = max(counts.values(), default=1)
        rows = "".join(
            '<div style="margin:12px 0"><b>'
            + escape(labels(k))
            + f' · {v}건</b><div style="height:8px;background:var(--sisun-line);border-radius:4px"><div style="height:8px;background:#2563eb;width:{100 * v / high:.1f}%;border-radius:4px"></div></div></div>'
            for k, v in counts.most_common()
        )
        return card("<h3>" + title + "</h3>" + (rows or "기록 없음"))

    out += bars(
        "대응 상태", m["states"], lambda k: alert_response.RESPONSE_LABELS.get(k, k)
    )
    out += bars(
        "구역별 발생 사건",
        m["cameras"],
        lambda k: " · ".join(
            [
                CAM_BY_ID.get(k, {}).get("cam", k).upper(),
                CAM_BY_ID.get(k, {}).get("zone", ""),
            ]
        ),
    )
    out += bars("유형별 발생 사건", m["features"], lambda k: _FEATURES.get(k, k))
    return out
