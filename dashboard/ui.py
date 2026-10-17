# 로그인·표·KPI·통계 HTML
import re

import gradio as gr
import pandas as pd

from .events import part_area, part_of
from .config import (
    ADMINS,
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
    cam_tag,
    clock_start,
    ko,
    sc_of,
)

def live_flash_html(part, elapsed, window=2.5):
    """지금 시각 근처의 주의·위험만 큰 경고로 띄움."""
    if part is None or len(part) == 0:
        return ""
    col = "grade" if "grade" in part.columns else "status"
    start = pd.Timestamp(clock_start())
    ts = pd.to_datetime(part["timestamp"], errors="coerce")
    sec = (ts - start).dt.total_seconds().fillna(0)
    now = part[(sec <= float(elapsed)) & (sec >= float(elapsed) - window)]
    if now is None or len(now) == 0:
        return ""
    if (now[col] == "위험").any():
        css, level, en = "sisun-flash-hot", "위험", "DANGER"
        hit = now[now[col] == "위험"]
    elif (now[col] == "주의").any():
        css, level, en = "sisun-flash-warn", "주의", "WARNING"
        hit = now[now[col] == "주의"]
    else:
        return ""
    names = []
    for _, r in hit.iterrows():
        try:
            names.append(sc_of(r["scenario"])["name"])
        except Exception:
            pass
    sub = " · ".join(dict.fromkeys(names))
    extra = f"<div style='font-size:18px;font-weight:800;margin-top:8px;letter-spacing:0'>{sub}</div>" if sub else ""
    return (
        f"<div class='sisun-flash {css}'>{level}"
        f"<div style='font-size:20px;letter-spacing:.28em;margin-top:6px'>{en}</div>{extra}</div>"
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
    return re.sub(r"^#\d+\s*", "", str(name or "")).strip() or str(name or "")


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
            login_error("아이디 또는 비밀번호가 올바르지 않습니다. 입력한 정보를 다시 확인해 주세요."),
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
    <div class="sisun-hello">{hello}</div>
    <div id="sisun-clock" class="sisun-clock">--</div>
    <div class="sisun-notice">[공지] 작업 중 안전에 유의하세요</div>
  </div>
</div>
"""


def theme_foot_html():
    return """
<div class="sisun-theme" id="sisun-theme-row" role="button" tabindex="0">
  <span class="sisun-theme-ico" aria-hidden="true">☽</span>
  <span class="sisun-theme-label">Dark Mode</span>
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
    fg = STATUS_FG.get(st, "#f8fafc")
    return f"<span style='color:{fg} !important;font-weight:800'>{st}</span>"


def kpi_html(d):
    total, hot, warn, safe, unknown = _stat_bucket(d)
    cams = len(CAMERAS)
    # 테마 따라가는 값만 t2-kpi-ink (라이트에서 흰글씨 방지). 위험/주의 등은 고정색.
    cells = [
        ("전체 사건", str(total), "var(--sisun-card-fg)", "t2-kpi-ink"),
        ("위험", str(hot), "#ef4444", ""),
        ("주의", str(warn), "#d97706", ""),
        ("안전", str(safe), "#16a34a", ""),
        ("미확인", str(unknown), "var(--sisun-muted)", "t2-kpi-ink"),
        ("카메라", f"{cams}(작동중)", "#0284c7", "t2-kpi-cam"),
    ]
    boxes = []
    for title, val, color, cls in cells:
        boxes.append(
            f"<div class='t2-kpi' style='{INK_CARD}'>"
            f"<div class='t2-muted' style='font-size:13px;{INK_MUTED}'>{title}</div>"
            f"<div class='{cls}' style='font-size:32px;font-weight:800;color:{color};margin-top:6px'>{val}</div></div>"
        )
    return "<div style='display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px'>" + "".join(boxes) + "</div>"


def recent_alert_html(d, limit=8):
    col = "grade" if "grade" in d.columns else "status"
    view = d[d[col].isin(["주의", "위험"])].sort_values("timestamp", ascending=False).head(limit)
    if len(view) == 0:
        return card("최근 알람이 없습니다.")
    rows = []
    for _, r in view.iterrows():
        color = sc_of(r["scenario"])["color"]
        rows.append(
            f"<tr><td style='padding:8px;{INK_CELL}'><span style='display:inline-block;width:8px;height:8px;"
            f"border-radius:50%;background:{color}'></span></td>"
            f"<td style='padding:8px;{INK_CELL}'>{r['timestamp']}</td>"
            f"<td style='padding:8px;{INK_CELL}'>{r.get('zone') or ''}</td>"
            f"<td style='padding:8px;{INK_CELL}'>{r['camera']}</td>"
            f"<td style='padding:8px;{INK_CELL}'>{r.get('worker') or ''}</td>"
            f"<td style='padding:8px;{INK_CELL}'>{sc_of(r['scenario'])['name']}</td>"
            f"<td style='padding:8px;{INK_CELL}'>{status_html(r['status'])}</td>"
            f"<td style='padding:8px;{INK_CELL}'>{r['message']}</td></tr>"
        )
    return card(
        f"<b style='{INK_FG}'>실시간 알람</b>"
        "<table class='t2-table'>"
        f"<thead><tr style='text-align:left'><th style='{INK_HEAD}'></th><th style='{INK_HEAD}'>시각</th>"
        f"<th style='{INK_HEAD}'>창고</th><th style='{INK_HEAD}'>카메라</th>"
        f"<th style='{INK_HEAD}'>작업자</th>"
        f"<th style='{INK_HEAD}'>유형</th>"
        f"<th style='{INK_HEAD}'>단계</th><th style='{INK_HEAD}'>내용</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def table_html(d, sid=None, newest_first=False, allow_empty=False, include_fire_status=False):
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
                f"<td style='{INK_CELL}'>{r['message']}</td>"
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


def _stat_bar(label, n, max_n, color):
    pct = 0 if max_n <= 0 or n <= 0 else max(4.0, 100.0 * n / max_n)
    return (
        f"<div style='display:flex;align-items:center;gap:12px;margin:12px 0'>"
        f"<div style='width:84px;flex:0 0 84px;font-weight:700;{INK_FG}'>{label}</div>"
        f"<div class='t2-stat-track'>"
        f"<div style='height:100%;width:{pct:.1f}%;background:{color};border-radius:8px'></div>"
        f"</div>"
        f"<b style='width:88px;flex:0 0 88px;text-align:right;font-size:20px;{INK_FG}'>{n}</b></div>"
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
    mapped = part["grade"].map(_stat_grade) if "grade" in part.columns else part["status"].map(_stat_grade)
    return (
        int(len(part)),
        int((mapped == "위험").sum()),
        int((mapped == "주의").sum()),
        int((mapped == "안전").sum()),
        int((mapped == "미확인").sum()),
    )


def _ppe_wear(st, grade):
    g = str(grade or "")
    s = str(st or "")
    if g == "미확인" or s == "미확인":
        return "착용"
    if "미착용" in s or g in ("주의", "위험"):
        return "미착용"
    return "착용"


def _time_bin_labels(d):
    ts = pd.to_datetime(d["timestamp"])
    hours = ts.dt.floor("h").nunique()
    if hours >= 3:
        return ts.dt.strftime("%H:00")
    base = pd.Timestamp(clock_start())
    slot = ((ts - base).dt.total_seconds() // 10 * 10).astype(int)
    return slot.map(lambda s: (base + pd.Timedelta(seconds=int(s))).strftime("%H:%M:%S"))


def _grouped_time_html(d):
    if d is None or len(d) == 0:
        return f"<div class='t2-muted' style='margin-top:8px;{INK_MUTED}'>시간 데이터 없음</div>"
    view = d.copy()
    view["_bin"] = _time_bin_labels(view)
    bins = sorted(view["_bin"].unique())
    series = {sc["id"]: [] for sc in SCENARIOS}
    max_n = 1
    for b in bins:
        chunk = view[view["_bin"] == b]
        for sc in SCENARIOS:
            n = int((chunk["scenario"] == sc["id"]).sum())
            series[sc["id"]].append(n)
            max_n = max(max_n, n)
    cols = []
    for i, b in enumerate(bins):
        bars = []
        for sc in SCENARIOS:
            n = series[sc["id"]][i]
            h = 6 if n <= 0 else max(8, int(240 * n / max_n))
            bars.append(
                f"<div title='{sc['name']} {n}' "
                f"style='width:16px;height:{h}px;background:{sc['color']};border-radius:4px 4px 0 0'></div>"
            )
        cols.append(
            f"<div class='t2-time-col'>"
            f"<div style='display:flex;align-items:flex-end;gap:2px;height:240px'>{''.join(bars)}</div>"
            f"<div style='margin-top:8px;font-size:12px;font-weight:700;{INK_MUTED}'>{b}</div></div>"
        )
    legend = "".join(
        f"<span style='display:inline-flex;align-items:center;gap:6px;margin-right:16px'>"
        f"<span style='width:12px;height:12px;background:{sc['color']};border-radius:2px'></span>"
        f"<span style='{INK_FG}'>{'안전모' if sc['id'] == 'ppe' else sc['name']}</span></span>"
        for sc in SCENARIOS
    )
    return (
        f"<div style='margin:8px 0 14px 0'>{legend}</div>"
        f"<div style='display:flex;align-items:flex-end;gap:8px;overflow-x:auto;"
        f"min-height:300px;padding-bottom:8px'>{''.join(cols)}</div>"
    )


def stats_html(d):
    type_cards = []
    for z in ZONES:
        total, danger, warn, safe, unknown = _stat_bucket(part_area(d, z["id"]))
        max_n = max(total, danger, warn, safe, unknown, 1)
        type_cards.append(
            card(
                f"<b style='font-size:18px;{INK_FG}'>{cam_tag(z)}</b>"
                f"<div class='t2-muted' style='margin:6px 0 4px 0;{INK_MUTED}'>"
                "총 · 위험 · 주의 · 안전 · 미확인</div>"
                + _stat_bar("총 건수", total, max_n, z["color"])
                + _stat_bar("위험", danger, max_n, "#ef4444")
                + _stat_bar("주의", warn, max_n, "#f59e0b")
                + _stat_bar("안전", safe, max_n, "#10b981")
                + _stat_bar("미확인", unknown, max_n, "#64748b")
            )
        )
    ppe = part_of(d, "ppe")
    if len(ppe):
        wear = [_ppe_wear(st, g) for st, g in zip(ppe["status"], ppe["grade"])]
        worn = wear.count("착용")
        missing = wear.count("미착용")
    else:
        worn = missing = 0
    ppe_max = max(worn, missing, 1)
    ppe_card = card(
        f"<b style='font-size:18px;{INK_FG}'>안전모 착용</b>"
        f"<div class='t2-muted' style='margin:6px 0 4px 0;{INK_MUTED}'>"
        "두 장면 · 사람 1명 = 1줄 (미확인=착용)</div>"
        + _stat_bar("착용", worn, ppe_max, "#10b981")
        + _stat_bar("미착용", missing, ppe_max, "#ef4444")
    )
    return (
        "<div class='t2-stats-wrap'>"
        "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:12px'>"
        + "".join(type_cards)
        + "</div>"
        + f"<div style='margin-bottom:12px'>{ppe_card}</div>"
        + card(f"<b style='font-size:18px;{INK_FG}'>시간대별 유형</b>" + _grouped_time_html(d))
        + "</div>"
    )
