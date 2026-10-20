# 역할: 로그인·영상 안내·위험 설명·KPI·이력 표의 화면 요소를 만듭니다.
# 로그인·표·KPI·통계 HTML
import re

import gradio as gr
import pandas as pd

from .display_text import (
    fire_evidence_lines,
    fire_reason_label,
    operator_message_for_row,
)
from .events import part_area, part_of
from .timeline import event_seconds, event_timestamps
from .config import (
    ADMINS,
    CAM_BY_ID,
    CAMERAS,
    TABS,
    INK_CARD,
    INK_CELL,
    INK_FG,
    INK_HEAD,
    INK_MUTED,
    INK_TITLE,
    SCENARIOS,
    STATUS_FG,
    ZONES,
    cam_side_label,
    cam_tag,
    clock_start,
    ko,
    sc_of,
)

# 관제 오버레이·상세 요약: 위치(zone) + 발생 이유. 모델/임계값과 무관한 표시 문구만.
_REASON_BY_SCENARIO = {
    "collision": "작업자–지게차 근접 위험",
    "zone": "위험구역 침범",
    "ppe": "안전모 미착용",
    "dwell": "위험구역 장시간 체류",
}
_EVIDENCE_BY_SCENARIO = {
    "collision": (
        "작업자와 지게차의 근접 위험이 관측됨",
        "영상에서 간격·접촉 위험 여부 확인",
    ),
    "zone": (
        "위험구역 진입이 관측됨",
        "영상에서 실제 침범 여부 확인",
    ),
    "ppe": (
        "안전모 미착용 상태가 관측됨",
        "영상에서 안전모 착용 여부 확인",
    ),
    "dwell": (
        "위험구역 장시간 체류가 관측됨",
        "영상에서 체류 지속 여부 확인",
    ),
}
_SEVERITY_RANK = {
    "위험": 4,
    "화재 의심": 4,
    "주의": 2,
    "확인 중": 1,
}
_FIRE_STATUS = ("화재 의심", "확인 중", "관측 소실", "판정 불가")


def place_label_for_cam(cam):
    """메인 문구용 위치. 창고명 없이 구역명만 (예: 옥외 주차장)."""
    if not cam:
        return ""
    zone = str(cam.get("zone") or "").strip()
    if zone:
        return zone
    site = str(cam.get("name") or "").strip()
    return site


def _cell(row, key, default=""):
    if row is None:
        return default
    try:
        value = row[key] if key in row.index else default
    except Exception:
        try:
            value = row.get(key, default)
        except Exception:
            return default
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return value


def reason_label_for_row(row):
    """이벤트 행 → 발생 이유 한 줄. 화재는 저장 status와 일치."""
    sid = str(_cell(row, "scenario") or "")
    status = str(_cell(row, "status") or "")
    if sid == "fire":
        return fire_reason_label(status)
    if sid == "ppe" and "미착용" in status:
        return "안전모 미착용"
    mapped = _REASON_BY_SCENARIO.get(sid)
    if mapped:
        return mapped
    try:
        return sc_of(sid)["name"]
    except Exception:
        return status or "위험"


def _severity_rank(row):
    grade = str(_cell(row, "grade") or "")
    status = str(_cell(row, "status") or "")
    return max(_SEVERITY_RANK.get(grade, 0), _SEVERITY_RANK.get(status, 0))


def pick_representative_alert(slice_df):
    """같은 카메라 다중 위험 → 심각도 높은 것, 동률이면 최신. (대표행, 추가건수)."""
    if slice_df is None or len(slice_df) == 0:
        return None, 0
    n = len(slice_df)
    if n == 1:
        return slice_df.iloc[0], 0
    ranks = [_severity_rank(r) for _, r in slice_df.iterrows()]
    if "timestamp" in slice_df.columns:
        ts = slice_df["timestamp"].tolist()
        # 심각도 desc, 시각 desc — 복사 열 없이 인덱스 선택
        order = sorted(
            range(n),
            key=lambda i: (ranks[i], ts[i]),
            reverse=True,
        )
    else:
        order = sorted(range(n), key=lambda i: ranks[i], reverse=True)
    return slice_df.iloc[order[0]], n - 1


def evidence_lines_for_row(row):
    sid = str(_cell(row, "scenario") or "")
    status = str(_cell(row, "status") or "")
    if sid == "fire":
        return fire_evidence_lines(status)
    default = _EVIDENCE_BY_SCENARIO.get(
        sid, ("이벤트 조건 충족", "영상에서 실제 상황 확인")
    )
    msg = operator_message_for_row(row)
    if msg and len(msg) <= 64:
        return msg, default[1]
    return default


def pick_latest_fire_row(part, elapsed, window=12.0):
    """재생 위치 기준 구간 안 최신 불꽃 상태 행(알림 여부와 무관)."""
    if part is None or len(part) == 0 or "scenario" not in part.columns:
        return None
    try:
        t = float(elapsed)
    except (TypeError, ValueError):
        return None
    if t <= 0:
        return None
    sec = event_seconds(part)
    now = part[(sec <= t) & (sec >= t - float(window))]
    fire = now[now["scenario"] == "fire"]
    if len(fire) == 0:
        return None
    if "timestamp" in fire.columns:
        fire = fire.sort_values("timestamp", ascending=False)
    else:
        fire = fire.iloc[::-1]
    return fire.iloc[0]


def format_event_clock(row):
    """상세 요약용 시:분:초."""
    ts = str(_cell(row, "timestamp") or "")
    if " " in ts:
        time_part = ts.split(" ", 1)[1]
        return time_part[:8] if len(time_part) >= 8 else time_part
    return ts[:8] if ts else "—"


def alert_lines_for_row(row, cam=None):
    """메인·종 알림 공통: (위치 · 이유, CAM · 상세 보기)."""
    cid = str(_cell(row, "area") or "")
    cam_meta = cam if cam is not None else CAM_BY_ID.get(cid, {})
    place = place_label_for_cam(cam_meta)
    if not place:
        place = str(_cell(row, "zone") or "").strip()
    reason = reason_label_for_row(row)
    headline = " · ".join(part for part in (place, reason) if part) or "위험"
    cam_code = str((cam_meta or {}).get("cam") or _cell(row, "camera") or "").upper()
    sub = f"{cam_code} · 상세 보기" if cam_code else "상세 보기"
    return headline, sub


def cam_danger_overlay_html(
    active,
    place="",
    reason="",
    cam_code="",
    cam_id="",
    extra=0,
):
    """메인 영상 위 위험 박스: 위치·이유 / CAM · 상세 보기.
    클릭 시 해당 카메라 탭(#2~)으로 이동 (data-cam-id).
    """
    if not active:
        return "<div class='sisun-cam-alert-inner sisun-cam-alert-off' aria-hidden='true'></div>"
    headline = " · ".join(part for part in (place, reason) if part) or "위험"
    sub = f"{cam_code} · 상세 보기" if cam_code else "상세 보기"
    # 행 수−1 = 대표를 제외한 최근 구간 기록 수 (별도 사건 ID로 묶지 않음)
    extra_html = (
        f"<div class='sisun-cam-alert-extra'>추가 기록 {int(extra)}건</div>"
        if extra and int(extra) > 0
        else ""
    )
    cam_attr = f" data-cam-id='{_esc(cam_id)}'" if cam_id else ""
    return (
        f"<div class='sisun-cam-alert-inner sisun-cam-alert-on' role='button' "
        f"tabindex='0' title='해당 구역 화면으로 이동'{cam_attr}>"
        f"<div class='sisun-cam-alert-kicker'>{_esc(headline)}</div>"
        f"<div class='sisun-cam-alert-msg'>{_esc(sub)}</div>"
        f"{extra_html}</div>"
    )


def danger_overlay_updates(view, cams, positions, window=12.0):
    """재생 위치 기준 최근 window초 위험 → 카메라당 대표 문구 1개."""
    idle = [cam_danger_overlay_html(False) for _ in cams]
    if view is None or len(view) == 0 or not cams:
        return idle
    if not isinstance(positions, dict):
        return idle
    col = "grade" if "grade" in view.columns else "status"
    hot = view[view[col] == "위험"]
    if len(hot) == 0:
        return idle
    sec = event_seconds(hot)
    areas = hot["area"].astype(str)
    out = []
    for cam in cams:
        cid = str(cam.get("id") or "")
        try:
            t = float(positions.get(cid, 0.0))
        except (TypeError, ValueError):
            t = 0.0
        if not (t > 0 and cid):
            out.append(cam_danger_overlay_html(False))
            continue
        mask = (areas == cid) & (sec <= t) & (sec >= t - float(window))
        hit = hot.loc[mask]
        if len(hit) == 0:
            out.append(cam_danger_overlay_html(False))
            continue
        best, extra = pick_representative_alert(hit)
        out.append(
            cam_danger_overlay_html(
                True,
                place=place_label_for_cam(cam),
                reason=reason_label_for_row(best),
                cam_code=str(cam.get("cam") or "").upper(),
                cam_id=cid,
                extra=extra,
            )
        )
    return out


def pick_live_alert_row(part, elapsed, window=12.0):
    """재생 위치 기준 최근 구간 대표 위험/주의 행. 없으면 (None, 0)."""
    if part is None or len(part) == 0:
        return None, 0
    try:
        t = float(elapsed)
    except (TypeError, ValueError):
        return None, 0
    if t <= 0:
        return None, 0
    col = "grade" if "grade" in part.columns else "status"
    sec = event_seconds(part)
    now = part[(sec <= t) & (sec >= t - float(window))]
    if now is None or len(now) == 0:
        return None, 0
    hot = now[now[col] == "위험"]
    if len(hot) == 0:
        hot = now[now[col] == "주의"]
    if len(hot) == 0:
        # 화재 확인 중·관측 소실 등 grade가 위험이 아닌 상태도 상세에서 설명(신규 알림 아님)
        if "status" in now.columns:
            fireish = now[now["status"].isin(list(_FIRE_STATUS))]
            if len(fireish):
                return pick_representative_alert(fireish)
        return None, 0
    return pick_representative_alert(hot)


def _latest_fire_note_html(best, part, elapsed, window):
    """대표 위험 기록과 최신 관측 상태가 다르면 시각을 구분해 안내."""
    if str(_cell(best, "scenario") or "") != "fire":
        return ""
    latest = pick_latest_fire_row(part, elapsed, window=window)
    if latest is None:
        return ""
    best_status = str(_cell(best, "status") or "")
    latest_status = str(_cell(latest, "status") or "")
    best_ts = str(_cell(best, "timestamp") or "")
    latest_ts = str(_cell(latest, "timestamp") or "")
    if latest_status == best_status:
        return ""
    if latest_ts and best_ts and latest_ts < best_ts:
        return ""
    when = format_event_clock(latest)
    label = fire_reason_label(latest_status)
    return (
        f"<div class='sisun-detail-line'><span>최신 관측 상태</span> "
        f"{_esc(label)} · 발생 시각 {_esc(when)} "
        f"(위 최근 위험 기록과 별개 · 현재 불꽃 확정이 아님)</div>"
    )


def live_detail_summary_html(part, elapsed, cam=None, window=12.0):
    """카메라 상세 상단: 위치·이유 + 시각/CAM + 근거·확인 사항."""
    best, extra = pick_live_alert_row(part, elapsed, window=window)
    if best is None:
        return ""
    cam_meta = cam or CAM_BY_ID.get(str(_cell(best, "area") or ""), {})
    place = place_label_for_cam(cam_meta) or str(_cell(best, "zone") or "")
    reason = reason_label_for_row(best)
    headline = " · ".join(part for part in (place, reason) if part)
    cam_code = str((cam_meta or {}).get("cam") or _cell(best, "camera") or "").upper()
    when = format_event_clock(best)
    evidence, check = evidence_lines_for_row(best)
    status = str(_cell(best, "status") or "")
    level = str(_cell(best, "grade") or status or "")
    css = (
        "sisun-detail-hot"
        if level == "위험" or status == "화재 의심"
        else "sisun-detail-warn"
    )
    extra_bit = (
        f"<div class='sisun-detail-extra'>같은 카메라 추가 기록 {int(extra)}건</div>"
        if extra
        else ""
    )
    fire_note = _latest_fire_note_html(best, part, elapsed, window)
    return (
        f"<div class='sisun-detail-summary {css}'>"
        f"<div class='sisun-detail-headline'>{_esc(headline)}</div>"
        f"<div class='sisun-detail-meta'>발생 시각: {_esc(when)} / {_esc(cam_code)}"
        f" · 최근 기록</div>"
        f"<div class='sisun-detail-line'><span>감지 근거</span> {_esc(evidence)}</div>"
        f"<div class='sisun-detail-line'><span>확인 사항</span> {_esc(check)}</div>"
        f"{fire_note}"
        f"{extra_bit}</div>"
    )


def live_judgment_html(part, elapsed, cam=None, window=12.0):
    """요약과 동일한 대표 행의 판정 기준·관측 근거. 알림 없으면 빈 문자열."""
    from .judgment import judgment_panel_html

    best, _extra = pick_live_alert_row(part, elapsed, window=window)
    if best is None:
        return ""
    return judgment_panel_html(best, cam=cam)


def live_flash_html(part, elapsed, window=2.5, cam=None):
    """카메라 상세 상단 요약(위치·이유·근거). 구 flash 자리 재사용."""
    return live_detail_summary_html(
        part, elapsed, cam=cam, window=max(float(window), 12.0)
    )


def login_html():
    return """
<div class="sisun-login-bg" aria-hidden="true">
  <svg viewBox="0 0 1200 900" preserveAspectRatio="xMidYMid slice">
    <circle cx="1020" cy="-40" r="560" fill="none" stroke="#1d4ed8" stroke-width="22"/>
    <circle cx="1020" cy="-40" r="620" fill="none" stroke="#2563eb" stroke-width="3" opacity=".45"/>
    <circle cx="80" cy="980" r="480" fill="none" stroke="#1e3a8a" stroke-width="14" opacity=".7"/>
  </svg>
</div>
<div class="sisun-login-brand">
  <div class="sisun-login-kicker">시선</div>
  <div class="sisun-login-name">로그인</div>
</div>"""


def login_foot():
    return """
<div class="sisun-login-meta">
  <label class="sisun-login-keep"><input type="checkbox"/> 로그인 유지</label>
  <span class="sisun-login-forgot">비밀번호 문의</span>
</div>
"""


def login_error(msg):
    return f"<div class='sisun-login-err' role='alert'>{msg}</div>"


def tab_caption(name):
    caption = re.sub(r"^#\d+\s*", "", str(name or "")).strip()
    return re.sub(r"\s+", " ", caption)


def _esc(text):
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def do_login(uid, pw):
    uid = str(uid or "").strip()
    pw = str(pw or "")
    if uid not in ADMINS or ADMINS.get(uid) != pw:
        # 실패 시 게이트/대시보드는 건드리지 않음 — 불필요 DOM 재렌더·큐 정체 방지
        return (
            gr.update(),
            gr.update(),
            login_error(
                "아이디 또는 비밀번호가 올바르지 않습니다. 입력한 정보를 다시 확인해 주세요."
            ),
            gr.update(),
            "",
        )
    # login-on 을 완전히 제거하고 off+hide 로 바꿔 게이트 CSS 가 덮지 않게 함
    return (
        gr.update(visible=False, elem_classes=["sisun-login-off", "hide"]),
        gr.update(visible=True),
        "",
        header_html(uid, TABS[0]["name"]),
        uid,
    )


def do_logout():
    return (
        gr.update(visible=True, elem_classes=["sisun-login-on"]),
        gr.update(visible=False),
        "",
        header_html(),
        "",
        gr.update(value=""),
        gr.update(value=""),
    )


def header_html(uid="", tab_name=""):
    who = _esc(uid)
    sub = _esc(tab_caption(tab_name or TABS[0]["name"]))
    hello = f"안녕하세요, {who}님" if who else ""
    return f"""
<div class="sisun-header">
  <div class="sisun-h-left">
    <button type="button" id="sisun-side-toggle" class="sisun-side-toggle" aria-label="사이드바 닫기" title="사이드바 닫기"></button>
    <div class="sisun-brand"><span class="sisun-brand-mark"></span>시선</div>
    <div class="sisun-weather">
      <div class="sisun-weather-place">경상북도 포항시 남구</div>
      <div id="sisun-weather-data" class="sisun-weather-data">--</div>
    </div>
  </div>
  <div class="sisun-h-center">
    <div class="sisun-h-title">스마트 안전관제</div>
    <div class="sisun-h-sub">{sub}</div>
  </div>
  <div class="sisun-h-right">
    <div class="sisun-hello" data-operator="{who}">{hello}</div>
    <div id="sisun-clock" class="sisun-clock">--</div>
    <div class="sisun-notice">[공지] 작업 중 안전에 유의하세요</div>
  </div>
</div>
"""


def theme_foot_html():
    return """
<div class="sisun-theme" id="sisun-theme-row" role="button" tabindex="0">
  <span class="sisun-theme-ico" aria-hidden="true">☀</span>
  <span class="sisun-theme-label">Light Mode</span>
  <span class="sisun-theme-sw" aria-hidden="true"><span class="sisun-theme-knob"></span></span>
</div>
"""


def side_brand_html():
    return """<div class="sisun-side-brand"><span class="sisun-brand-mark"></span>시선</div>"""


def card(html):
    return f"<div class='t2-card' style='{INK_CARD}'>{html}</div>"


def title_html(text):
    return f"<div class='t2-page-title' style='{INK_TITLE}'>{text}</div>"


def status_html(st):
    st = str(st or "")
    fg = STATUS_FG.get(st, "var(--sisun-table-fg)")
    return f"<span style='color:{fg} !important;font-weight:800'>{st}</span>"


def _event_link_meta_html(d):
    """이벤트 조회 신호(파일 재생과 별개). KPI에 숨겨 넣고 클라이언트 배지가 읽는다."""
    from datetime import datetime

    if d is None:
        state, rows, err = "loading", 0, ""
    else:
        try:
            rows = int(len(d))
        except Exception:
            rows = 0
        state, err = ("empty" if rows == 0 else "ok"), ""
    at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"<div class='sisun-event-bus-meta' hidden "
        f"data-state='{state}' data-at='{at}' data-rows='{rows}' "
        f"data-error='{err}'></div>"
    )


def kpi_html(d):
    total, hot, warn, safe, unknown = _stat_bucket(d)
    cams = len(CAMERAS)
    # 테마 따라가는 값만 t2-kpi-ink (라이트에서 흰글씨 방지). 위험/주의 등은 고정색.
    # '구성 카메라' = 배치된 카메라 수. 재생·이벤트 연결 정상 수를 뜻하지 않음.
    cells = [
        ("전체 사건", str(total), "var(--sisun-card-fg)", "t2-kpi-ink"),
        ("위험", str(hot), "#ef4444", ""),
        ("주의", str(warn), "#d97706", ""),
        ("안전", str(safe), "#16a34a", ""),
        ("미확인", str(unknown), "var(--sisun-muted)", "t2-kpi-ink"),
        ("구성 카메라", str(cams), "#0284c7", "t2-kpi-cam"),
    ]
    boxes = []
    for title, val, color, cls in cells:
        boxes.append(
            f"<div class='t2-kpi' style='{INK_CARD}'>"
            f"<div class='t2-muted' style='font-size:13px;{INK_MUTED}'>{title}</div>"
            f"<div class='{cls}' style='font-size:32px;font-weight:800;color:{color};margin-top:6px'>{val}</div></div>"
        )
    return (
        "<div class='sisun-kpi-grid'>"
        + "".join(boxes)
        + "</div>"
        + _event_link_meta_html(d)
    )


def table_html(
    d, sid=None, newest_first=False, allow_empty=False, include_fire_status=False
):
    """CCTV 탭은 시간순(위=처음), #8은 최신 위. 번호는 1부터."""
    if sid:
        view = d[d["scenario"] == sid] if d is not None and len(d) else d
    else:
        view = d
    if view is not None and len(view) and not include_fire_status:
        # Status evidence stays in the history; camera tables show fire alerts only.
        view = view[(view["scenario"] != "fire") | (view["status"] == "화재 의심")]
    if view is None or len(view) == 0:
        if not allow_empty:
            return card(ko.empty_events_message())
        rows = []
    else:
        cols = [c for c in ("timestamp", "worker", "event_id") if c in view.columns]
        if cols:
            view = view.sort_values(cols, ascending=not newest_first)
        rows = []
        for i, (_, r) in enumerate(view.iterrows(), 1):
            color = sc_of(r["scenario"])["color"]
            when = r["timestamp"]
            stay = r.get("dwell_sec")
            if (
                r.get("scenario") == "dwell"
                and str(r.get("status") or r.get("grade")) == "주의"
                and stay not in ("", None)
                and float(stay) > 0
            ):
                when = f"{when} ({float(stay):.0f}s)"
            rows.append(
                "<tr>"
                f"<td style='{INK_CELL}'>{i}</td>"
                f"<td style='{INK_CELL}'>{when}</td>"
                f"<td style='{INK_CELL}'>{r.get('worker') or ''}</td>"
                f"<td style='{INK_CELL}'><span style='color:{color};font-weight:700'>{sc_of(r['scenario'])['name']}</span></td>"
                f"<td style='{INK_CELL}'>{status_html(r['status'])}</td>"
                f"<td style='{INK_CELL}'>{r['camera']}</td>"
                f"<td style='{INK_CELL}'>{r['zone']}</td>"
                f"<td style='{INK_CELL}'>{_esc(operator_message_for_row(r))}</td>"
                "</tr>"
            )
    return card(
        "<div style='overflow:auto'><table class='t2-table'>"
        "<thead><tr style='text-align:left'>"
        f"<th style='{INK_HEAD}'>번호</th><th style='{INK_HEAD}'>시각</th>"
        f"<th style='{INK_HEAD}'>작업자</th>"
        f"<th style='{INK_HEAD}'>유형</th><th style='{INK_HEAD}'>단계</th>"
        f"<th style='{INK_HEAD}'>카메라</th><th style='{INK_HEAD}'>구역</th>"
        f"<th style='{INK_HEAD}'>내용</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _stat_grade(g):
    """메인 KPI 집계. 가림·미확인은 안전으로 넣지 않음."""
    if g in ("위험", "주의", "안전", "미확인"):
        return g
    if g in ("착용",):
        return "안전"
    if g in ("미착용",):
        return "주의"
    return "미확인"


def _stat_bucket(part):
    if part is None or len(part) == 0:
        return 0, 0, 0, 0, 0
    mapped = (
        part["grade"].map(_stat_grade)
        if "grade" in part.columns
        else part["status"].map(_stat_grade)
    )
    return (
        int(len(part)),
        int((mapped == "위험").sum()),
        int((mapped == "주의").sum()),
        int((mapped == "안전").sum()),
        int((mapped == "미확인").sum()),
    )


def _time_bin_labels(d):
    ts = event_timestamps(d)
    hours = ts.dt.floor("h").nunique()
    if hours >= 3:
        return ts.dt.strftime("%H:00").fillna("시각 미상")
    base = pd.Timestamp(clock_start())
    slot = (ts - base).dt.total_seconds() // 10 * 10
    return slot.map(
        lambda s: (
            (base + pd.Timedelta(seconds=int(s))).strftime("%H:%M:%S")
            if pd.notna(s)
            else "시각 미상"
        )
    )
