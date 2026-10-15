# team7.py
# 화면: team5.py 그대로
# 이벤트: python handoff.py backend → GET /events (http://127.0.0.1:8010)
# 표시: GitHub configs/dashboard-labels.ko.json (영문 API → 한글만)
# 영상: GitHub main 발표 1~5. 결과 mp4 없으면 handoff.py run --video N
# https://github.com/Sang-Hyeop/K_newdeal_visionAI
# python team7.py

import base64
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import gradio as gr

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.join(HERE, "team7_data")
ALARM_PATH = os.path.join(LOCAL, "alarm.wav")
WARN_PATH = os.path.join(LOCAL, "warn.wav")

DATA_CANDIDATES = [
    Path(HERE),
    Path(r"c:\code\K_newdeal_visionAI_main"),
    Path(r"c:\code\K_newdeal_visionAI"),
    Path(HERE) / "K_newdeal_visionAI",
    Path(HERE).parent.parent / "K_newdeal_visionAI",
]
CURRENT_MP4 = {
    "1_forklift_worker_collision_risk.mp4",
    "2_restricted_zone_intrusion.mp4",
    "3_PPE_Helmet.mp4",
    "4_hazard_zone_dwell.mp4",
    "5_Logistics Warehouse.mp4",
}
OLD_MP4 = {
    "1_forklift_forward.mp4",
    "2_forklift_back.mp4",
    "3_forklift_crush.mp4",
    "5_PPE_Helmet.mp4",
    "6_Helmet_forklift.mp4",
}


def pick_data_root():
    """옛 7개 영상 클론은 건너뛰고, GitHub main 발표 1~5만 쓴다."""
    for p in DATA_CANDIDATES:
        if not (p / "handoff.py").is_file() or not (p / "data" / "videos").is_dir():
            continue
        if not (p / "configs" / "dashboard-labels.ko.json").is_file():
            continue
        names = {x.name for x in (p / "data" / "videos").glob("*.mp4")}
        if names & OLD_MP4 and not (CURRENT_MP4 & names):
            continue
        if CURRENT_MP4 <= names:
            return p
    return None


DATA_ROOT = pick_data_root()
if DATA_ROOT is None:
    raise FileNotFoundError("GitHub main 발표 영상 1~5 저장소가 없습니다.")
sys.path.insert(0, str(DATA_ROOT / "backend_v1"))
import dashboard_labels as ko  # GitHub 한글 표시. API 원본은 안 바꿈.
API_PORT = int(os.environ.get("SISUN_API_PORT", "8010"))
API_BASE = os.environ.get("SISUN_API", f"http://127.0.0.1:{API_PORT}")
API_PROC = None
SID_TO_VIDEO = {"collision": 1, "zone": 2, "ppe": 3, "dwell": 4}
NEEDED_VIDEOS = (1, 2, 3, 4, 5)

VIDEO_DIR = DATA_ROOT / "data" / "videos"
EVENT_LOG_PATH = DATA_ROOT / "outputs" / "events"

TITLE = "시선 - 스마트 안전관제"
OPERATOR = "안전 당직"
PAGE_BG = "#0f172a"
SEEN_IDS = set()
SOUND_READY = False

def _src_video(n):
    return ko.presentation_video(n) or {
        1: "1_forklift_worker_collision_risk.mp4",
        2: "2_restricted_zone_intrusion.mp4",
        3: "3_PPE_Helmet.mp4",
        4: "4_hazard_zone_dwell.mp4",
        5: "5_Logistics Warehouse.mp4",
    }[n]


VIDEO_FILES = {sid: _src_video(n) for sid, n in SID_TO_VIDEO.items()}
WAREHOUSE_VIDEO = _src_video(5)
GRID_VIDEOS = [
    VIDEO_FILES["collision"],
    VIDEO_FILES["zone"],
    VIDEO_FILES["dwell"],
    VIDEO_FILES["ppe"],
]


def is_warehouse_video(name):
    """5번 물류창고는 #8 보여주기만. 로그·통계에는 안 넣음."""
    text = str(name or "")
    return text == WAREHOUSE_VIDEO or "Logistics Warehouse" in text


# 카메라 = 탭. 발표 파일 번호(3=안전모, 4=체류)와 다름.
VIDEO_CAM = {
    _src_video(1): "CAM_01",  # #2 충돌
    _src_video(2): "CAM_02",  # #3 구역
    _src_video(4): "CAM_03",  # #4 체류
    _src_video(3): "CAM_04",  # #5 안전모
    _src_video(5): "CAM_05",  # #8 물류창고 보여주기
}
VIDEO_TITLE = {_src_video(n): ko.video_label(_src_video(n)) for n in range(1, 6)}
FEATURE_TO_SID = {
    "person_forklift_proximity": "collision",
    "forklift_forklift_proximity": "collision",
    "conditional_person_forklift_proximity": "collision",
    "zone_access": "zone",
    "zone_dwell": "dwell",
    "ppe": "ppe",
}

TABS = [
    {"id": "main", "name": "#1 메인 관제"},
    {"id": "collision", "name": "#2 충돌 관제"},
    {"id": "zone", "name": "#3 구역 접근"},
    {"id": "dwell", "name": "#4 구역 체류"},
    {"id": "ppe", "name": "#5 안전모"},
    {"id": "alerts", "name": "#6 통합 알람"},
    {"id": "history", "name": "#7 이벤트 이력"},
    {"id": "cctv", "name": "#8 CCTV 관리"},
    {"id": "stats", "name": "#9 통계 분석"},
]
SCENARIOS = [
    {"id": "collision", "name": "지게차 충돌", "color": "#ef4444", "cam": "CAM_01"},
    {"id": "zone", "name": "위험구역 침범", "color": "#f59e0b", "cam": "CAM_02"},
    {"id": "dwell", "name": "위험구역 체류", "color": "#8b5cf6", "cam": "CAM_03"},
    {"id": "ppe", "name": "안전모 미착용", "color": "#3b82f6", "cam": "CAM_04"},
]
TYPE_TO_SCENARIO = {
    "proximity": "collision",
    "person_forklift_proximity": "collision",
    "forklift_forklift_proximity": "collision",
    "conditional_person_forklift_proximity": "collision",
    "zone_access": "zone",
    "zone_dwell": "dwell",
    "ppe": "ppe",
}
COLLISION_KINDS = {
    "proximity",
    "person_forklift_proximity",
    "forklift_forklift_proximity",
    "conditional_person_forklift_proximity",
}
DWELL_KINDS = {"zone_dwell"}
GRADE_RANK = {"위험": 3, "주의": 2, "안전": 1, "미확인": 0}
GRADE_EN = {"안전": "SAFE", "주의": "WARN", "위험": "CRIT", "미확인": "UNKNOWN"}
SID_TO_EVENT_TYPE = {
    "collision": "proximity",
    "zone": "zone_access",
    "dwell": "zone_dwell",
    "ppe": "ppe",
}
for _name in list(VIDEO_TITLE):
    VIDEO_TITLE[_name] = ko.video_label(_name)
for _sc in SCENARIOS:
    _sc["name"] = ko.event_type_label(SID_TO_EVENT_TYPE[_sc["id"]])
STATUS_COLOR = {
    "안전": "#10b981", "주의": "#f59e0b", "위험": "#ef4444",
    "없음": "#64748b", "미확인": "#64748b",
    "착용": "#10b981", "미착용": "#ef4444",
    "안전모 착용 감지": "#10b981", "안전모 미착용 감지": "#ef4444",
}
STATUS_FG = {
    "안전": "#22c55e", "주의": "#eab308", "위험": "#ef4444",
    "없음": "#94a3b8", "대기": "#22c55e", "미확인": "#94a3b8",
    "착용": "#22c55e", "미착용": "#ef4444",
    "안전모 착용 감지": "#22c55e", "안전모 미착용 감지": "#ef4444",
}
DWELL_LIMIT = 8
PPE_SPLIT_SEC = 6.0
INK_TITLE = "color:var(--sisun-title,#f8fafc)!important"
INK_CARD = "background:var(--sisun-card-bg,#1e293b)!important;color:var(--sisun-card-fg,#f8fafc)!important"
INK_CELL = "color:var(--sisun-table-fg,#f8fafc)!important;background:var(--sisun-table-bg,#1e293b)!important"
INK_HEAD = "color:var(--sisun-table-fg,#f8fafc)!important;background:var(--sisun-th-bg,#334155)!important"
INK_MUTED = "color:var(--sisun-muted,#cbd5e1)!important"
INK_FG = "color:var(--sisun-card-fg,#f8fafc)!important"

CSS = """
footer { display: none !important; }
.gradio-container { max-width: 100% !important; padding: 0 18px 28px 18px !important; }
#sisun-theme-btn {
  position: fixed !important; top: 14px; right: 18px; z-index: 9999;
  width: 80px !important; min-width: 80px !important;
}
#sisun-theme-btn, #sisun-theme-btn button,
.t2-refresh, .t2-refresh button {
  background: #fbbf24 !important; color: #111827 !important;
  border: 2px solid #111827 !important; font-weight: 800 !important;
}
.tab-nav button.selected, .tab-nav button[aria-selected="true"] {
  background: #2563eb !important; color: #fff !important;
}
.t2-page-title { font-size: 1.35rem; font-weight: 800; margin: 0 0 8px 0; line-height: 1.3; }
.t2-table { width: 100%; border-collapse: collapse; font-size: 14px; }

/* 소리 빈칸·제목 상자: Gradio 테두리/여백을 화면에서 없앰 */
.t2-sound, .t2-sound.block, .t2-sound .block, .t2-sound .html-container, .t2-sound .prose {
  display: none !important; height: 0 !important; min-height: 0 !important;
  padding: 0 !important; margin: 0 !important; border: none !important; overflow: hidden !important;
}
.t2-title-block, .t2-title-block.block, .t2-title-block .block,
.t2-title-block .html-container, .t2-title-block .prose {
  border: none !important; background: transparent !important; box-shadow: none !important;
  padding: 0 !important; margin: 0 0 8px 0 !important; min-height: 0 !important;
}
.gradio-container .block:has(.html-container) {
  border: none !important; background: transparent !important; box-shadow: none !important;
  padding: 0 !important; min-height: 0 !important;
}
.html-container, .prose { border: none !important; min-height: 0 !important; padding: 0 !important; background: transparent !important; }

/* ===== 밤 ===== */
html, body, .gradio-container { background: #0f172a !important; color: #f8fafc !important; }
.tab-nav { background: #1e293b !important; border: 1px solid #64748b !important; border-radius: 10px !important; padding: 6px !important; }
.tab-nav button { color: #f8fafc !important; font-weight: 700 !important; opacity: 1 !important; }
.sisun-header { background: #020617 !important; border-bottom: 1px solid #475569 !important; }
.sisun-title, .sisun-sub, .sisun-meta { color: #f8fafc !important; }
.t2-page-title { color: #f8fafc !important; }
.t2-card, .t2-kpi { background: #1e293b !important; border: 1px solid #94a3b8 !important; color: #f8fafc !important; border-radius: 12px; padding: 14px 16px; }
.t2-muted { color: #cbd5e1 !important; }
.t2-table th, .t2-table td {
  border: 1px solid #94a3b8 !important; padding: 8px 10px !important;
  color: #f8fafc !important; background: #1e293b !important;
}
.t2-table th { background: #334155 !important; }
.t2-pick-label { font-size: 16px; font-weight: 800; margin: 0 0 10px 0; color: #f8fafc !important; }
.t2-pick-btn, .t2-pick-btn button {
  background: #334155 !important; color: #ffffff !important;
  border: 1px solid #94a3b8 !important; font-weight: 700 !important;
}
.t2-stats-wrap { min-height: 72vh; }
.t2-stat-track {
  flex: 1; height: 32px; background: #334155; border-radius: 8px; overflow: hidden;
}
.t2-time-col { min-width: 44px; flex: 1; height: 100%;
  display: flex; flex-direction: column; align-items: center; justify-content: flex-end;
}

/* ===== 낮 ===== */
html.sisun-day, html.sisun-day body, html.sisun-day .gradio-container {
  background: #f1f5f9 !important; color: #0f172a !important;
}
html.sisun-day .tab-nav { background: #ffffff !important; border: 1px solid #64748b !important; }
html.sisun-day .tab-nav button { color: #0f172a !important; font-weight: 700 !important; opacity: 1 !important; }
html.sisun-day .sisun-header { background: #ffffff !important; border-bottom: 1px solid #64748b !important; }
html.sisun-day .sisun-title, html.sisun-day .sisun-sub, html.sisun-day .sisun-meta { color: #0f172a !important; }
html.sisun-day .t2-page-title { color: #0f172a !important; }
html.sisun-day .t2-card, html.sisun-day .t2-kpi {
  background: #ffffff !important; border: 1px solid #475569 !important; color: #0f172a !important;
}
html.sisun-day .t2-muted { color: #334155 !important; }
html.sisun-day .t2-table th, html.sisun-day .t2-table td {
  border: 1px solid #475569 !important; color: #0f172a !important; background: #ffffff !important;
}
html.sisun-day .t2-table th { background: #e2e8f0 !important; color: #0f172a !important; }
html.sisun-day .t2-pick-label { color: #0f172a !important; }
html.sisun-day .t2-pick-btn, html.sisun-day .t2-pick-btn button {
  background: #e2e8f0 !important; color: #0f172a !important; border: 1px solid #475569 !important;
}

/* ===== 낮 추가 (밤 규칙은 수정하지 않음) ===== */
html.sisun-day {
  --body-background-fill: #f1f5f9 !important;
  --background-fill-primary: #ffffff !important;
  --background-fill-secondary: #e2e8f0 !important;
  --block-background-fill: #ffffff !important;
  --block-border-color: #475569 !important;
  --body-text-color: #0f172a !important;
  --block-title-text-color: #0f172a !important;
  --block-label-text-color: #334155 !important;
}
html.sisun-day .block,
html.sisun-day .column,
html.sisun-day .form,
html.sisun-day .tabitem,
html.sisun-day .panel {
  color: #0f172a !important;
}
html.sisun-day .label-wrap,
html.sisun-day .block-label,
html.sisun-day .block-title,
html.sisun-day .block-info {
  color: #0f172a !important;
}
html.sisun-day .tab-nav button:not(.selected):not([aria-selected="true"]) {
  color: #0f172a !important;
  background: #ffffff !important;
}
html.sisun-day .tab-nav button.selected,
html.sisun-day .tab-nav button[aria-selected="true"] {
  background: #2563eb !important;
  color: #ffffff !important;
}
html.sisun-day .block:has(video),
html.sisun-day .video-container {
  background: #ffffff !important;
  border: 1px solid #475569 !important;
}

/* 낮 추가: 흰 바탕은 검정 글자, 어두운 표·칸은 흰 글자 */
html.sisun-day .t2-page-title,
html.sisun-day .t2-pick-label {
  color: #111827 !important;
}
html.sisun-day .t2-card,
html.sisun-day .t2-kpi {
  background: #1e293b !important;
  color: #f8fafc !important;
}
html.sisun-day .t2-muted { color: #e2e8f0 !important; }
html.sisun-day .t2-table th,
html.sisun-day .t2-table td {
  background: #1e293b !important;
  color: #f8fafc !important;
}
html.sisun-day .t2-table th {
  background: #334155 !important;
  color: #f8fafc !important;
}
html.sisun-day .sisun-header .sisun-title,
html.sisun-day .sisun-header .sisun-sub,
html.sisun-day .sisun-header .sisun-meta,
html.sisun-day .sisun-header #sisun-clock,
html.sisun-day .sisun-header .sisun-meta > span:first-of-type {
  color: #f8fafc !important;
}

"""

BOOT_JS = """
() => {
  var collect = function(root, sel, out) {
    if (!root) return;
    if (root.querySelectorAll) {
      root.querySelectorAll(sel).forEach(function(el) { out.push(el); });
    }
    var all = root.querySelectorAll ? root.querySelectorAll("*") : [];
    all.forEach(function(el) { if (el.shadowRoot) collect(el.shadowRoot, sel, out); });
  };
  var allOf = function(sel) {
    var out = [];
    collect(document, sel, out);
    return out;
  };
  var ink = function(el, prop, val) {
    if (el && el.style) el.style.setProperty(prop, val, "important");
  };
  window.__sisunPaint = function(day) {
    document.documentElement.classList.toggle("sisun-day", !!day);
    if (document.body) document.body.classList.toggle("sisun-day", !!day);
    document.querySelectorAll(".gradio-container").forEach(function(box) {
      box.classList.toggle("sisun-day", !!day);
    });
    var title = day ? "#111827" : "#f8fafc";
    var onDark = "#f8fafc";
    var darkBg = "#1e293b";
    var headBg = "#334155";
    allOf(".t2-page-title").forEach(function(el) { ink(el, "color", title); });
    allOf(".t2-pick-label").forEach(function(el) { ink(el, "color", title); });
    allOf(".sisun-title,.sisun-sub,.sisun-meta,#sisun-clock").forEach(function(el) { ink(el, "color", "#f8fafc"); });
    allOf(".t2-card,.t2-kpi").forEach(function(el) {
      ink(el, "background", darkBg);
      ink(el, "color", onDark);
    });
    allOf(".t2-muted").forEach(function(el) { ink(el, "color", "#e2e8f0"); });
    allOf(".t2-table th").forEach(function(el) {
      ink(el, "color", onDark);
      ink(el, "background", headBg);
    });
    allOf(".t2-table td").forEach(function(el) {
      ink(el, "color", onDark);
      ink(el, "background", darkBg);
    });
    allOf(".tab-nav button").forEach(function(el) {
      var on = el.classList.contains("selected") || el.getAttribute("aria-selected") === "true";
      ink(el, "color", on ? "#ffffff" : title);
    });
    var old = document.getElementById("sisun-day-force");
    if (old) old.remove();
  };
  var day = (localStorage.getItem("sisun-theme2") === "day");
  window.__sisunPaint(day);
  setTimeout(function() { window.__sisunPaint(day); }, 400);
  var label = function() {
    var btn = document.querySelector("#sisun-theme-btn button") || document.querySelector("#sisun-theme-btn");
    if (btn) btn.textContent = day ? "낮" : "밤";
  };
  label();
  setTimeout(label, 300);
  window.__sisunSound = true;
  var muteCctv = function() {
    allOf("video").forEach(function(v) {
      v.muted = true;
      v.defaultMuted = true;
      v.volume = 0;
    });
  };
  muteCctv();
  var tick = function() {
    var el = document.getElementById("sisun-clock");
    if (el) el.textContent = new Date().toLocaleString("ko-KR", {hour12: false});
  };
  tick();
  setInterval(tick, 1000);
  document.addEventListener("pointerdown", function() {
    try {
      var ctx = window.__sisunCtx || new (window.AudioContext || window.webkitAudioContext)();
      window.__sisunCtx = ctx;
      if (ctx.state === "suspended") ctx.resume();
    } catch (e) {}
    muteCctv();
  });
  var timer = null;
  var watch = new MutationObserver(function() {
    muteCctv();
    if (timer) clearTimeout(timer);
    timer = setTimeout(function() {
      window.__sisunPaint(document.documentElement.classList.contains("sisun-day"));
      muteCctv();
    }, 80);
  });
  watch.observe(document.documentElement, { childList: true, subtree: true });
}
"""

TOGGLE_JS = """
() => {
  var day = !document.documentElement.classList.contains("sisun-day");
  if (window.__sisunPaint) window.__sisunPaint(day);
  try { localStorage.setItem("sisun-theme2", day ? "day" : "night"); } catch (e) {}
  return [day ? "낮" : "밤"];
}
"""


def sc_of(sid):
    return next(s for s in SCENARIOS if s["id"] == sid)


def cam_label(cam):
    text = str(cam or "cam_01")
    return text.replace("cam_", "CAM_").upper() if text[:3].lower() == "cam" else text


def dwell_status(sec):
    sec = int(sec)
    if sec <= 3:
        return "안전"
    if sec <= 7:
        return "주의"
    return "위험"


def event_status(ev):
    """GitHub severity_label. null/unconfirmed → 미확인. SAFE로 바꾸지 않음."""
    sev = ev.get("severity")
    if sev in ("", "null") or ev.get("observation_status") == "unconfirmed":
        sev = None
    return ko.severity_label(sev, ev.get("observation_status"))


def event_message(ev):
    """GitHub display_view 한글. 영문 reason·SAFE 원문은 넣지 않음."""
    view = ko.display_view(ev)
    evid = ev.get("evidence") if isinstance(ev.get("evidence"), dict) else {}
    bits = []
    if view.get("event_type_label"):
        bits.append(view["event_type_label"])
    if ev.get("event_type") == "ppe" and view.get("ppe_state_label"):
        bits.append(view["ppe_state_label"])
    if view.get("region_label"):
        bits.append(view["region_label"])
    if view.get("observation_status_label"):
        bits.append(view["observation_status_label"])
    stay = evid.get("observed_dwell_seconds") or evid.get("dwell_seconds") or evid.get("stay_seconds")
    if stay not in (None, ""):
        bits.append(ko.format_dwell_seconds(stay))
    gap = evid.get("image_gap_pixels")
    if gap not in (None, ""):
        bits.append(f"화면상 간격 {float(gap):.0f}px")
    bits.append(ko.format_distance_meters(evid.get("distance_meters", ev.get("distance_meters"))))
    return " · ".join(bits)


def _person_tid(ev):
    evid = ev.get("evidence") if isinstance(ev.get("evidence"), dict) else {}
    ids = ev.get("track_ids") or []
    tid = str(evid.get("person_track_id") or evid.get("track_id") or (ids[0] if ids else ""))
    if not tid or tid[:1] in "FH":
        return ""
    return tid


def _person_x(ev):
    evid = ev.get("evidence") if isinstance(ev.get("evidence"), dict) else {}
    box = evid.get("person_bbox_xyxy") or evid.get("head_bbox_xyxy") or [0]
    try:
        return float(box[0])
    except (TypeError, IndexError, ValueError):
        return 0.0


def _event_dwell(ev):
    evid = ev.get("evidence") if isinstance(ev.get("evidence"), dict) else {}
    stay = evid.get("observed_dwell_seconds") or evid.get("dwell_seconds") or evid.get("stay_seconds")
    try:
        return float(stay)
    except (TypeError, ValueError):
        return 0.0


def event_to_row(ev):
    kind = ev.get("event_type", "")
    if kind == "ppe" or kind in COLLISION_KINDS or kind in DWELL_KINDS:
        return None
    return _row_fields(ev)


def _row_fields(ev):
    kind = ev.get("event_type", "")
    sid = TYPE_TO_SCENARIO.get(kind)
    if sid is None:
        return None
    video = ev.get("video") or ""
    own = VIDEO_FILES.get(sid)
    if not own or video != own:
        return None
    view = ko.display_view(ev)
    evid = ev.get("evidence") if isinstance(ev.get("evidence"), dict) else {}
    sec = float(ev.get("timestamp_seconds") or 0)
    ts = datetime(2026, 10, 7, 9, 0, 0) + timedelta(seconds=sec)
    cam = sc_of(sid)["cam"]
    stay = evid.get("observed_dwell_seconds") or evid.get("dwell_seconds") or evid.get("stay_seconds")
    gap = evid.get("image_gap_pixels")
    zone = view.get("zone_label") or view.get("camera_label") or ""
    grade = event_status(ev)
    st = grade
    if kind == "ppe" and grade != "미확인" and view.get("ppe_state_label"):
        st = view["ppe_state_label"]
    return {
        "event_id": str(ev.get("event_id", ""))[:12],
        "scenario": sid,
        "event_type": kind,
        "status": st,
        "grade": grade,
        "year": ts.year,
        "month": ts.month,
        "day": ts.day,
        "hour": ts.hour,
        "minute": ts.minute,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "camera": cam,
        "zone": zone,
        "dwell_sec": "" if stay in (None, "") else float(stay),
        "distance_px": "" if gap in (None, "") else float(gap),
        "message": event_message(ev),
        "frame": "",
        "video": video,
        "person_no": 0,
        "track_id": _person_tid(ev),
    }


def _unique_people_rows(events, kinds, sid, prefix):
    """같은 사람 프레임 반복을 접고, 사람 1명 = 1줄."""
    own = VIDEO_FILES.get(sid)
    groups = {}
    for ev in events:
        if ev.get("event_type") not in kinds:
            continue
        if own and (ev.get("video") or "") != own:
            continue
        tid = _person_tid(ev)
        if not tid:
            continue
        groups.setdefault(tid, []).append(ev)
    items = []
    for tid, evs in groups.items():
        best = max(
            evs,
            key=lambda e: (
                GRADE_RANK.get(event_status(e), 0),
                float(e.get("timestamp_seconds") or 0),
            ),
        )
        items.append((_person_x(best), tid, best, evs))
    items.sort()
    rows = []
    for i, (_x, _tid, best, evs) in enumerate(items, 1):
        row = _row_fields(best)
        if row is None:
            continue
        row["event_id"] = f"{prefix}{i:02d}"
        row["person_no"] = i
        tag = GRADE_EN.get(row["grade"], "UNKNOWN")
        bits = [f"{i} {tag}"]
        if sid == "collision" and row["distance_px"] not in ("", None):
            bits.append(f"{float(row['distance_px']):.0f}px")
        if sid == "dwell":
            stay = max((_event_dwell(e) for e in evs), default=0)
            row["dwell_sec"] = stay if stay > 0 else ""
        row["message"] = " · ".join(bits)
        rows.append(row)
    return rows


def write_tone(path, pattern, vol=14000):
    os.makedirs(LOCAL, exist_ok=True)
    rate = 22050
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for freq, sec in pattern:
            n = int(rate * sec)
            for i in range(n):
                v = 0 if freq < 1 else int(vol * math.sin(2 * math.pi * freq * i / rate))
                w.writeframes(struct.pack("<h", v))


def write_beep():
    write_tone(ALARM_PATH, [(980, 0.06), (0.001, 0.03)] * 10, vol=15000)
    write_tone(WARN_PATH, [(480, 0.22), (0.001, 0.28), (480, 0.22)], vol=4000)


def api_get(path, params=None):
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_up():
    try:
        api_get("/events", {"limit": 1})
        return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return False


def runtime_index():
    path = DATA_ROOT / "configs" / "team-runtime-index.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"videos": []}


def presentation_row(num):
    for row in runtime_index().get("videos") or []:
        if int(row.get("presentation_video_number") or 0) == int(num):
            return row
    return None


def sample_root():
    """발표 1~5 이벤트만. backend_v1/samples 더미 40건은 쓰지 않음."""
    events = DATA_ROOT / "outputs" / "events"
    if events.is_dir() and list(events.rglob("events_v1.jsonl")):
        return events
    raise FileNotFoundError("GitHub 발표 이벤트 outputs/events 가 없습니다.")


def _jsonl_event_count():
    n = 0
    for path in sample_root().rglob("events_v1.jsonl"):
        with path.open(encoding="utf-8") as f:
            n += sum(1 for line in f if line.strip())
    return n


def _stop_api(port):
    global API_PROC
    if API_PROC is not None:
        try:
            API_PROC.terminate()
        except OSError:
            pass
        API_PROC = None
    if os.name == "nt":
        cmd = (
            f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
            "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)


def find_demo(num):
    """확정 리뷰(선·상자)를 먼저 쓰고, 없을 때만 handoff 임시 결과를 쓴다."""
    row = presentation_row(num)
    if row and row.get("review_video"):
        review = DATA_ROOT / row["review_video"]
        if review.is_file() and review.stat().st_size > 0:
            return review
    found = []
    runs = DATA_ROOT / "outputs" / "handoff_runs"
    if runs.is_dir():
        found += [p for p in runs.glob(f"presentation{num}_*/**/demo.mp4") if p.is_file() and p.stat().st_size > 0]
        found += [p for p in runs.glob(f"presentation{num}_*/*.mp4") if p.is_file() and p.stat().st_size > 0]
    if not found:
        return None
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found[0]


def ensure_repo_demos():
    """발표 1~4 결과 영상이 없으면 handoff.py run 으로 만든다."""
    handoff = DATA_ROOT / "handoff.py"
    if not handoff.is_file():
        print("handoff.py 가 없습니다.", DATA_ROOT)
        return
    for n in NEEDED_VIDEOS:
        if find_demo(n) is not None:
            continue
        cmd = [sys.executable, str(handoff), "run", "--video", str(n)]
        print("handoff 생성", " ".join(cmd))
        subprocess.run(cmd, cwd=str(DATA_ROOT), check=False)


def ensure_api():
    global API_PROC
    expected = _jsonl_event_count()
    if api_up():
        total = int((api_get("/events", {"limit": 1}) or {}).get("total") or 0)
        if expected and abs(total - expected) <= 5:
            print("API", API_BASE, "events", total)
            return
        print("API 로그가 예전입니다. 다시 시작합니다.", total, "->", expected)
        _stop_api(API_PORT)
    os.makedirs(LOCAL, exist_ok=True)
    backend = DATA_ROOT / "backend_v1" / "backend.py"
    if not backend.is_file():
        raise FileNotFoundError(f"백엔드가 없습니다: {backend}")
    log_path = os.path.join(LOCAL, "api.log")
    cmd = [
        sys.executable, str(backend),
        "--host", "127.0.0.1", "--port", str(API_PORT),
        "--samples", str(sample_root()),
        "--db", str(DATA_ROOT / "outputs" / "backend" / "full_review.sqlite3"),
    ]
    cwd = str(backend.parent)
    print("API 시작", " ".join(cmd))
    log = open(log_path, "w", encoding="utf-8")
    API_PROC = subprocess.Popen(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(80):
        time.sleep(0.5)
        if api_up():
            print("API", API_BASE)
            return
    raise RuntimeError(f"API 시작 실패 {API_BASE} · 로그 {log_path}")


def load_events():
    ensure_api()
    found = []
    offset = 0
    limit = 500
    while True:
        data = api_get("/events", {"limit": limit, "offset": offset})
        batch = data.get("events") or []
        found.extend(batch)
        total = int(data.get("total") or 0)
        offset += len(batch)
        if not batch or offset >= total:
            break
    return found


def ppe_detections_path():
    row = presentation_row(SID_TO_VIDEO["ppe"])
    rel = (row or {}).get("diagnostic_root")
    if rel:
        path = DATA_ROOT / rel / "detections.jsonl"
        if path.is_file():
            return path
    found = list((DATA_ROOT / "outputs" / "diagnostics").glob("presentation3*/**/detections.jsonl"))
    return found[0] if found else None


def _ppe_track_x(tr):
    box = tr.get("detected_bbox_xyxy") or tr.get("bbox_xyxy") or [0, 0, 0, 0]
    return float(box[0])


def _ppe_track_wear(tr):
    st = str((tr.get("ppe") or {}).get("state") or "")
    return "미착용" if st == "no_helmet_candidate" else "착용"


def _ppe_scene_pick(recs, t0, t1):
    best = None
    for rec in recs:
        t = float(rec.get("timestamp_seconds") or 0)
        if t < t0 or t >= t1:
            continue
        tracks = rec.get("ppe_tracks") or []
        if not tracks:
            continue
        decided = 0
        for tr in tracks:
            st = str((tr.get("ppe") or {}).get("state") or "")
            if st in ("helmet_detected", "no_helmet_candidate"):
                decided += 1
        key = (len(tracks), decided, t)
        if best is None or key > best[0]:
            best = (key, rec)
    return None if best is None else best[1]


def ppe_scene_rows():
    """0~5초 5명, 6초 이후 7명. 사람 1명 = 1줄, 합 12케이스."""
    path = ppe_detections_path()
    if path is None:
        return []
    recs = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                recs.append(json.loads(line))
    rows = []
    idx = 0
    video = VIDEO_FILES["ppe"]
    cam = sc_of("ppe")["cam"]
    for t0, t1 in ((0.0, PPE_SPLIT_SEC), (PPE_SPLIT_SEC, 99.0)):
        rec = _ppe_scene_pick(recs, t0, t1)
        if rec is None:
            continue
        sec = float(rec.get("timestamp_seconds") or t0)
        ts = datetime(2026, 10, 7, 9, 0, 0) + timedelta(seconds=sec)
        tracks = sorted(rec.get("ppe_tracks") or [], key=_ppe_track_x)
        for i, tr in enumerate(tracks, 1):
            idx += 1
            wear = _ppe_track_wear(tr)
            tag = "WORN" if wear == "착용" else "NOT WORN"
            rows.append({
                "event_id": f"P{idx:02d}",
                "scenario": "ppe",
                "event_type": "ppe",
                "status": wear,
                "grade": "안전" if wear == "착용" else "주의",
                "year": ts.year,
                "month": ts.month,
                "day": ts.day,
                "hour": ts.hour,
                "minute": ts.minute,
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "camera": cam,
                "zone": "",
                "dwell_sec": "",
                "distance_px": "",
                "message": f"{i} {tag}",
                "frame": "",
                "video": video,
                "person_no": i,
            })
    return rows


def load_df():
    write_beep()
    events = [ev for ev in load_events() if not is_warehouse_video(ev.get("video"))]
    rows = [event_to_row(ev) for ev in events]
    rows = [r for r in rows if r]
    rows.extend(_unique_people_rows(events, COLLISION_KINDS, "collision", "C"))
    rows.extend(_unique_people_rows(events, DWELL_KINDS, "dwell", "D"))
    rows.extend(ppe_scene_rows())
    cols = [
        "event_id", "scenario", "event_type", "status", "grade",
        "year", "month", "day", "hour", "minute",
        "timestamp", "camera", "zone", "dwell_sec",
        "distance_px", "message", "frame", "video", "person_no",
    ]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows).sort_values(["timestamp", "person_no", "event_id"])


def latest_row(d, sid):
    part = d[d["scenario"] == sid]
    if len(part) == 0:
        return None
    return part.sort_values(["timestamp", "event_id"]).iloc[-1]


def part_of(d, sid):
    return d[d["scenario"] == sid].sort_values(["timestamp", "event_id"], ascending=False)


def video_path(name):
    path = VIDEO_DIR / name
    return str(path) if path.is_file() else None


def pack_video_names():
    if VIDEO_DIR.is_dir():
        names = sorted(p.name for p in VIDEO_DIR.glob("*.mp4"))
        if names:
            return names
    return list(VIDEO_CAM.keys())


def main_clips():
    return [video_path(name) for name in GRID_VIDEOS]


def pack_clips():
    return [video_path(name) for name in pack_video_names()]


def pack_scenarios():
    feat_map = {
        1: ["person_forklift_proximity"],
        2: ["zone_access"],
        3: ["ppe"],
        4: ["zone_dwell"],
        5: ["zone_access", "conditional_person_forklift_proximity"],
    }
    rows = []
    for item in runtime_index().get("videos") or []:
        src = Path(item.get("source_video") or "").name
        num = item.get("presentation_video_number")
        if src:
            rows.append({
                "video_number": num,
                "source_name": src,
                "primary_features": feat_map.get(int(num or 0), []),
            })
    if rows:
        return rows
    path = DATA_ROOT / "configs" / "demo-scenarios.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("scenarios") or []
    return []


def cam_meta_list():
    rows = []
    items = pack_scenarios()
    if not items:
        items = [{"video_number": i + 1, "source_name": n, "primary_features": []} for i, n in enumerate(pack_video_names())]
    for item in items:
        name = item.get("source_name")
        if not name or not video_path(name):
            continue
        sid = None
        for feat in item.get("primary_features") or []:
            sid = FEATURE_TO_SID.get(feat)
            if sid:
                break
        rows.append({
            "video": name,
            "cam": VIDEO_CAM.get(name) or (sc_of(sid)["cam"] if sid else f"CAM_{len(rows)+1:02d}"),
            "name": VIDEO_TITLE.get(name, name),
            "sid": sid,
        })
    return rows


def _poly_px(norm, w, h):
    return np.array([[int(x * w), int(y * h)] for x, y in norm], np.int32)


def _roi_cfg(sid):
    num = SID_TO_VIDEO.get(sid)
    row = presentation_row(num) if num else None
    rel = (row or {}).get("camera_config")
    if not rel:
        return None
    path = DATA_ROOT / rel
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


BANNER = {
    "collision": "PROXIMITY DETECT",
    "zone": "ZONE ACCESS + LANE ROI",
    "dwell": "ZONE DWELL + LANE ROI",
    "ppe": "PPE HELMET DETECT",
}


def _marks_for_sid(sid):
    """GitHub API 이벤트만. 옛 samples/forward·ppe5 JSONL 은 쓰지 않음."""
    name = VIDEO_FILES.get(sid)
    return [
        ev for ev in load_events()
        if TYPE_TO_SCENARIO.get(ev.get("event_type")) == sid
        and (not name or ev.get("video") == name)
    ]


def _color(ev):
    st = event_status(ev)
    return {"위험": (0, 0, 255), "주의": (0, 165, 255), "안전": (0, 200, 0)}.get(st, (180, 180, 180))


def _worst_color(events):
    rank = {"위험": 3, "주의": 2, "안전": 1, "미확인": 0}
    best = max(events, key=lambda e: rank.get(event_status(e), 0), default=None)
    return _color(best) if best else (0, 220, 255)


def _draw_roi(frame, cfg, color=(0, 220, 255)):
    h, w = frame.shape[:2]
    poly = _poly_px(cfg.get("polygon_normalized") or [], w, h)
    if len(poly) < 3:
        return
    overlay = frame.copy()
    cv2.fillPoly(overlay, [poly], color)
    cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
    cv2.polylines(frame, [poly], True, color, 3)
    cv2.putText(frame, "LANE ROI", (int(poly[0][0]), max(48, int(poly[0][1]) + 24)), 0, 0.7, color, 2)


def _scale_xy(pt, sx, sy):
    return int(pt[0] * sx), int(pt[1] * sy)


def _draw_event(frame, ev, sx=1.0, sy=1.0):
    evid = ev.get("evidence") or {}
    color = _color(ev)
    boxes = []
    if evid.get("person_bbox_xyxy"):
        boxes.append(evid["person_bbox_xyxy"])
    if evid.get("forklift_bbox_xyxy"):
        boxes.append(evid["forklift_bbox_xyxy"])
    boxes += evid.get("forklift_bboxes_xyxy") or []
    for h in evid.get("head_candidates") or []:
        if h.get("bbox_xyxy"):
            boxes.append(h["bbox_xyxy"])
    for box in boxes:
        x1, y1, x2, y2 = box
        p1, p2 = _scale_xy((x1, y1), sx, sy), _scale_xy((x2, y2), sx, sy)
        cv2.rectangle(frame, p1, p2, color, 2)
    p = evid.get("person_anchor_xy")
    q = evid.get("nearest_vehicle_point_xy")
    if p and q:
        a, b = _scale_xy(p, sx, sy), _scale_xy(q, sx, sy)
        cv2.line(frame, a, b, color, 2)
        cv2.circle(frame, a, 5, (0, 200, 0), -1)
        cv2.circle(frame, b, 5, (0, 0, 255), -1)
    label = {"안전": "SAFE", "주의": "WARN", "위험": "CRIT", "미확인": "UNKNOWN"}.get(event_status(ev), "UNKNOWN")
    dwell = evid.get("observed_dwell_seconds")
    if dwell not in (None, ""):
        label = f"{label} {float(dwell):.1f}s"
    if boxes:
        x1, y1 = _scale_xy((boxes[0][0], boxes[0][1]), sx, sy)
        cv2.putText(frame, label, (x1, max(20, y1 - 6)), 0, 0.55, color, 2)


def _box_scale(marks, w, h):
    xs, ys = [0], [0]
    for ev in marks:
        evid = ev.get("evidence") or {}
        for key in ("person_bbox_xyxy", "forklift_bbox_xyxy"):
            box = evid.get(key)
            if box:
                xs.append(box[2])
                ys.append(box[3])
        for box in evid.get("forklift_bboxes_xyxy") or []:
            xs.append(box[2])
            ys.append(box[3])
    mx, my = max(xs), max(ys)
    sx = w / mx if mx > w + 8 else 1.0
    sy = h / my if my > h + 8 else 1.0
    return sx, sy


def _draw_banner(frame, sid, events):
    color = _worst_color(events)
    text = BANNER.get(sid, "DETECT")
    cv2.rectangle(frame, (8, 8), (min(frame.shape[1] - 8, 640), 40), (20, 20, 20), -1)
    cv2.putText(frame, text, (16, 32), 0, 0.7, color, 2)


def ensure_overlay(sid):
    """원본에 팀원 ROI·관측 상자·거리선을 입힌 시연 영상을 만든다."""
    src = video_path(VIDEO_FILES.get(sid, GRID_VIDEOS[0]))
    if not src:
        return None
    os.makedirs(LOCAL, exist_ok=True)
    dest = os.path.join(LOCAL, f"overlay_{sid}.mp4")
    stamp = os.path.join(LOCAL, f"overlay_{sid}.stamp")
    if os.path.isfile(dest) and os.path.isfile(stamp) and os.path.getmtime(dest) >= os.path.getmtime(src):
        return dest
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        return src
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    raw = os.path.join(LOCAL, f"overlay_{sid}_raw.mp4")
    writer = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    if not writer.isOpened():
        cap.release()
        writer.release()
        return src
    cfg = _roi_cfg(sid)
    marks = _marks_for_sid(sid)
    sx, sy = _box_scale(marks, w, h)
    buckets = {}
    for ev in marks:
        t = round(float(ev.get("timestamp_seconds") or 0), 3)
        buckets.setdefault(t, []).append(ev)
    times = sorted(buckets)
    current, ti = [], 0
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        now = idx / fps
        while ti < len(times) and times[ti] <= now + 0.04:
            current = buckets[times[ti]]
            ti += 1
        if cfg:
            _draw_roi(frame, cfg, _worst_color(current) if current else (0, 220, 255))
        for ev in current:
            _draw_event(frame, ev, sx, sy)
        _draw_banner(frame, sid, current)
        writer.write(frame)
        idx += 1
    cap.release()
    writer.release()
    if not os.path.isfile(raw) or os.path.getsize(raw) == 0:
        return src
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg = None
    converted = dest
    if ffmpeg:
        cmd = [
            ffmpeg, "-y", "-i", raw, "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", dest,
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                os.remove(raw)
            except OSError:
                pass
        except Exception:
            converted = raw
    else:
        try:
            os.replace(raw, dest)
            converted = dest
        except OSError:
            converted = raw
    Path(stamp).write_text("ok", encoding="utf-8")
    print("overlay", sid, converted)
    return converted if os.path.isfile(converted) else src


def pack_demo(sid):
    """발표 결과 영상. 없으면 handoff.py run 으로 만든다."""
    num = SID_TO_VIDEO.get(sid)
    if num is None:
        return None
    return pack_demo_num(num)


def pack_demo_num(num):
    found = find_demo(num)
    if found is None:
        ensure_repo_demos()
        found = find_demo(num)
    return str(found) if found else None


def overlay_clip(num):
    """선·상자가 그려진 발표 결과. 없으면 원본."""
    found = pack_demo_num(num)
    if found:
        return to_browser_mp4(found, f"demo_{num}.mp4")
    return video_path(_src_video(num))


def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def to_browser_mp4(src, dest_name):
    """브라우저가 못 읽는 mp4v 를 H.264 로 바꾼다. 결과는 team7_data 에 둔다."""
    if not src or not os.path.isfile(src):
        return src
    os.makedirs(LOCAL, exist_ok=True)
    dest = os.path.join(LOCAL, dest_name)
    stamp = dest + ".stamp"
    if os.path.isfile(dest) and os.path.isfile(stamp) and os.path.getmtime(dest) >= os.path.getmtime(src):
        return dest
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return src
    cmd = [
        ffmpeg, "-y", "-i", src, "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", dest,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return src
    if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
        return src
    Path(stamp).write_text("ok", encoding="utf-8")
    print("browser mp4", dest)
    return dest


def detect_video(sid=None):
    if sid in VIDEO_FILES:
        found = pack_demo(sid)
        if found:
            return to_browser_mp4(found, f"demo_{sid}.mp4")
    return video_path(VIDEO_FILES.get(sid, GRID_VIDEOS[0]))


def header_html():
    return f"""
<div class="sisun-header" style="padding:16px 22px 16px 22px;
  margin:0 -18px 16px -18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;padding-right:110px">
  <div>
    <div class="sisun-kicker" style="font-size:13px;letter-spacing:.08em;color:#60a5fa;font-weight:700">스마트 안전 관제</div>
    <div class="sisun-title" style="font-size:1.7rem;font-weight:800">{TITLE}</div>
  </div>
  <div class="sisun-meta" style="display:flex;gap:16px;align-items:center;font-size:14px">
    <b id="sisun-clock">--:--:--</b>
    <span>{OPERATOR}</span>
    <span style="background:#14532d;color:#86efac;padding:6px 10px;border-radius:999px;font-weight:700">시스템 정상</span>
    <span style="background:#1e3a5f;color:#93c5fd;padding:6px 10px;border-radius:999px;font-weight:700">소리 켜짐</span>
  </div>
</div>
"""


def card(html):
    return f"<div class='t2-card' style='{INK_CARD}'>{html}</div>"


def title_html(text):
    return f"<div class='t2-page-title' style='{INK_TITLE}'>{text}</div>"


def status_html(st):
    st = str(st or "")
    fg = STATUS_FG.get(st, "#f8fafc")
    return f"<span style='color:{fg} !important;font-weight:800'>{st}</span>"


def kpi_html(d):
    total = len(d)
    grade = d["grade"] if "grade" in d.columns else d["status"]
    hot = int((grade == "위험").sum()) if total else 0
    warn = int((grade == "주의").sum()) if total else 0
    cams = len(cam_meta_list())
    cells = [
        ("전체 사건", str(total), "#38bdf8"),
        ("위험", str(hot), "#ef4444"),
        ("주의", str(warn), "#f59e0b"),
        ("카메라", str(cams), "#22c55e"),
    ]
    boxes = []
    for title, val, color in cells:
        boxes.append(
            f"<div class='t2-kpi' style='{INK_CARD}'>"
            f"<div class='t2-muted' style='font-size:13px;{INK_MUTED}'>{title}</div>"
            f"<div style='font-size:32px;font-weight:800;color:{color};margin-top:6px'>{val}</div></div>"
        )
    return "<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:12px'>" + "".join(boxes) + "</div>"


def zone_chip(d, sid):
    sc = sc_of(sid)
    now = latest_row(d, sid)
    st = "없음" if now is None else str(now["status"])
    bg = STATUS_COLOR.get(st, "#64748b")
    extra = "기록 없음" if now is None else now["message"]
    return (
        f"<div style='background:{sc['color']};color:#fff;padding:8px 10px;border-radius:8px 8px 0 0;"
        f"font-weight:700'>{sc['name']} · {sc['cam']}</div>"
        f"<div class='t2-card' style='{INK_CARD};border-radius:0 0 8px 8px;border-top:0;padding:8px 10px;"
        f"font-size:13px'><span style='background:{bg};color:#fff;padding:2px 8px;border-radius:999px'>{st}</span>"
        f" {extra}</div>"
    )


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
            f"<td style='padding:8px;{INK_CELL}'>{sc_of(r['scenario'])['name']}</td>"
            f"<td style='padding:8px;{INK_CELL}'>{r['camera']}</td>"
            f"<td style='padding:8px;{INK_CELL}'>{status_html(r['status'])}</td>"
            f"<td style='padding:8px;{INK_CELL}'>{r['message']}</td></tr>"
        )
    return card(
        f"<b style='{INK_FG}'>실시간 알람</b>"
        "<table class='t2-table'>"
        f"<thead><tr style='text-align:left'><th style='{INK_HEAD}'></th><th style='{INK_HEAD}'>시각</th>"
        f"<th style='{INK_HEAD}'>유형</th><th style='{INK_HEAD}'>카메라</th>"
        f"<th style='{INK_HEAD}'>단계</th><th style='{INK_HEAD}'>내용</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def detail_html(sid, d):
    sc = sc_of(sid)
    now = latest_row(d, sid)
    n = len(part_of(d, sid))
    if now is None:
        body = ko.empty_events_message()
    else:
        extra = []
        if sid == "collision" and now["distance_px"] not in ("", None) and not (
            isinstance(now["distance_px"], float) and pd.isna(now["distance_px"])
        ):
            extra.append(f"화면상 간격 {float(now['distance_px']):.0f}px")
        if sid == "dwell" and now["dwell_sec"] not in ("", None):
            extra.append(f"체류 {float(now['dwell_sec']):.0f}초 / 기준 {DWELL_LIMIT}초")
        extra.append(now["message"])
        body = (
            f"<div style='font-size:28px;font-weight:800'>{status_html(now['status'])}</div>"
            f"<div style='margin-top:8px;{INK_FG}'>{now['timestamp']} · {now['camera']} · {now['zone']}</div>"
            f"<div class='t2-muted' style='margin-top:8px;{INK_MUTED}'>{' · '.join(extra)}</div>"
            f"<div class='t2-muted' style='margin-top:10px;{INK_MUTED}'>이 유형 {n}건</div>"
        )
    return card(f"<b style='{INK_FG}'>{sc['name']}</b><br>{body}")


def dwell_bar_html(d):
    now = latest_row(d, "dwell")
    sec = 0 if now is None or now["dwell_sec"] in ("", None) else float(now["dwell_sec"])
    pct = min(100, int(100 * sec / DWELL_LIMIT))
    color = "#8b5cf6" if sec < DWELL_LIMIT else "#ef4444"
    return card(
        f"<b style='{INK_FG}'>체류 {DWELL_LIMIT}초 기준</b>"
        f"<div style='font-size:42px;font-weight:800;margin:10px 0;color:{color}'>{sec:.0f}초</div>"
        f"<div style='background:#334155;border-radius:999px;height:14px;overflow:hidden'>"
        f"<div style='width:{pct}%;height:100%;background:{color}'></div></div>"
        f"<div class='t2-muted' style='margin-top:8px;{INK_MUTED}'>기준 {DWELL_LIMIT}초 · 현재 {pct}%</div>"
    )


def table_html(d, sid=None, newest_first=False):
    """#2~5는 시간순(위=처음), #7은 최신 위. 번호는 1부터."""
    if sid:
        view = d[d["scenario"] == sid] if d is not None and len(d) else d
    else:
        view = d
    if view is None or len(view) == 0:
        return card(ko.empty_events_message())
    cols = [c for c in ("timestamp", "person_no", "event_id") if c in view.columns]
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
        f"<th style='{INK_HEAD}'>유형</th><th style='{INK_HEAD}'>단계</th>"
        f"<th style='{INK_HEAD}'>카메라</th><th style='{INK_HEAD}'>구역</th>"
        f"<th style='{INK_HEAD}'>내용</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def cam_panel_html(d, meta):
    part = d[d["video"] == meta["video"]] if len(d) and "video" in d.columns else d.iloc[0:0]
    now = part.sort_values(["timestamp", "event_id"]).iloc[-1] if len(part) else None
    st = "대기" if now is None else now["status"]
    msg = "연결됨 · 대기" if now is None else now["message"]
    return card(
        f"<div style='font-weight:800;{INK_FG}'>{meta['cam']}</div>"
        f"<div style='margin:6px 0;{INK_FG}'>{meta['name']} · {status_html(st)}</div>"
        f"<div class='t2-muted' style='font-size:13px;{INK_MUTED}'>{msg}</div>"
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
    """#9 집계. 가림·미확인은 안전으로 넣지 않음."""
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
    base = pd.Timestamp("2026-10-07 09:00:00")
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
    for sc in SCENARIOS:
        if sc["id"] == "ppe":
            continue
        total, danger, warn, safe, unknown = _stat_bucket(part_of(d, sc["id"]))
        max_n = max(total, danger, warn, safe, unknown, 1)
        type_cards.append(
            card(
                f"<b style='font-size:18px;{INK_FG}'>{sc['name']}</b>"
                f"<div class='t2-muted' style='margin:6px 0 4px 0;{INK_MUTED}'>"
                "총 · 위험 · 주의 · 안전 · 미확인</div>"
                + _stat_bar("총 건수", total, max_n, "#38bdf8")
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
        "<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px'>"
        + "".join(type_cards)
        + "</div>"
        + f"<div style='margin-bottom:12px'>{ppe_card}</div>"
        + card(f"<b style='font-size:18px;{INK_FG}'>시간대별 유형</b>" + _grouped_time_html(d))
        + "</div>"
    )


def beep_html(kind):
    path = ALARM_PATH if kind == "hot" else WARN_PATH if kind == "warn" else ""
    if not path or not os.path.isfile(path):
        return ""
    raw = open(path, "rb").read()
    b64 = base64.b64encode(raw).decode("ascii")
    return (
        f"<audio autoplay style='display:none'><source src='data:audio/wav;base64,{b64}' type='audio/wav'></audio>"
        f"<script>(function(){{var a=new Audio('data:audio/wav;base64,{b64}');a.play().catch(function(){{}});}})();</script>"
    )


def notify(d):
    """이미 있는 기록은 안 울림. 주의=약한 소리, 위험=빠른 소리. 미확인은 안 울림."""
    global SOUND_READY
    if d is None or len(d) == 0:
        SOUND_READY = True
        return None
    col = "grade" if "grade" in d.columns else "status"
    danger = d[d[col].isin(["주의", "위험"])]
    ids = set(danger["event_id"].astype(str).tolist())
    if not SOUND_READY:
        SEEN_IDS.update(ids)
        SOUND_READY = True
        return None
    new_ids = ids - SEEN_IDS
    SEEN_IDS.update(ids)
    if not new_ids:
        return None
    fresh = danger[danger["event_id"].astype(str).isin(new_ids)]
    gcol = "grade" if "grade" in fresh.columns else "status"
    if int((fresh[gcol] == "위험").sum()):
        gr.Warning("위험 상황이 발생했습니다.")
        return "hot"
    gr.Warning("주의 상황이 발생했습니다.")
    return "warn"


def make_theme():
    return gr.themes.Soft(primary_hue="blue").set(
        body_background_fill=PAGE_BG,
        background_fill_primary=PAGE_BG,
        background_fill_secondary="#1e293b",
        block_background_fill="#1e293b",
        block_border_color="#334155",
        body_text_color="#e2e8f0",
        block_title_text_color="#e2e8f0",
        block_label_text_color="#cbd5e1",
    )


def video_box(path, height=240):
    return gr.Video(
        value=path if path and os.path.isfile(path) else None,
        autoplay=True,
        loop=True,
        include_audio=False,
        show_label=False,
        height=height,
    )


def make_main(d, clips):
    with gr.Blocks() as demo:
        kpis = gr.HTML()
        labs = []
        vids = []
        with gr.Row():
            for i in range(2):
                with gr.Column():
                    labs.append(gr.HTML())
                    vids.append(video_box(clips[i], 230))
        with gr.Row():
            for i in range(2, 4):
                with gr.Column():
                    labs.append(gr.HTML())
                    vids.append(video_box(clips[i], 230))
        alerts = gr.HTML()
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        sound = gr.HTML(elem_classes="t2-sound")

        def _load():
            view = load_df()
            return (
                beep_html(notify(view)),
                kpi_html(view),
                *[zone_chip(view, sc["id"]) for sc in SCENARIOS],
                recent_alert_html(view),
            )

        outs = [sound, kpis, *labs, alerts]
        demo.load(_load, outputs=outs)
        btn.click(_load, outputs=outs)
    return demo


def make_detail(sid, title, extra=None):
    with gr.Blocks() as demo:
        gr.HTML(title_html(title), elem_classes="t2-title-block")
        vid = video_box(detect_video(sid), 640)
        log = gr.HTML()
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        sound = gr.HTML(elem_classes="t2-sound")

        def _load():
            view = load_df()
            return (
                beep_html(notify(part_of(view, sid))),
                table_html(view, sid),
            )

        outs = [sound, log]
        demo.load(_load, outputs=outs)
        btn.click(_load, outputs=outs)
        _ = vid
        _ = extra
    return demo


def make_alerts():
    with gr.Blocks() as demo:
        gr.HTML(title_html("통합 알람 · 시각 · 위치 · 카메라"), elem_classes="t2-title-block")
        box = gr.HTML()
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        sound = gr.HTML(elem_classes="t2-sound")

        def _load():
            view = load_df()
            col = "grade" if "grade" in view.columns else "status"
            danger = view[view[col].isin(["주의", "위험"])]
            return beep_html(notify(danger)), recent_alert_html(danger, limit=30)

        demo.load(_load, outputs=[sound, box])
        btn.click(_load, outputs=[sound, box])
    return demo


def make_history():
    picks = ["전체"] + [s["name"] for s in SCENARIOS]
    with gr.Blocks() as demo:
        gr.HTML(title_html("이벤트 이력 · 유형으로 찾기"), elem_classes="t2-title-block")
        gr.HTML(f"<div class='t2-pick-label' style='{INK_TITLE}'>유형 고르기</div>", elem_classes="t2-title-block")
        btns = []
        with gr.Row():
            for name in picks:
                btns.append(gr.Button(name, elem_classes="t2-pick-btn"))
        box = gr.HTML()

        def _load(name="전체"):
            name = str(name or "전체").strip()
            view = load_df()
            if name != "전체":
                sid = next((s["id"] for s in SCENARIOS if s["name"] == name), None)
                if sid is None:
                    return card("그 유형을 찾지 못했습니다.")
                view = view[view["scenario"] == sid]
            return table_html(view, newest_first=True)

        demo.load(lambda: _load("전체"), outputs=box)
        for name, btn in zip(picks, btns):
            btn.click(lambda n=name: _load(n), outputs=box)
    return demo


def _is_warehouse(meta):
    name = str(meta.get("video") or "")
    title = str(meta.get("name") or "")
    return is_warehouse_video(name) or "물류창고" in title


def make_cctv(d, clips):
    metas = cam_meta_list()
    main = next((m for m in metas if _is_warehouse(m)), None)
    rest = [m for m in metas if m is not main]
    rest = sorted(rest, key=lambda m: str(m.get("cam") or ""))
    if main is None:
        main, rest = (metas[0], metas[1:]) if metas else (None, [])
    ordered = ([main] if main else []) + rest
    with gr.Blocks() as demo:
        gr.HTML(title_html("카메라 관리 · 물류창고 종합 메인"), elem_classes="t2-title-block")
        panels = []
        with gr.Row():
            with gr.Column(scale=1):
                gr.HTML("")
            with gr.Column(scale=6):
                if main:
                    panels.append(gr.HTML())
                    video_box(overlay_clip(5), 520)
            with gr.Column(scale=1):
                gr.HTML("")
        with gr.Row():
            for m in rest:
                with gr.Column():
                    panels.append(gr.HTML())
                    video_box(video_path(m["video"]), 160)

        def _load():
            view = load_df()
            return [cam_panel_html(view, m) for m in ordered]

        demo.load(_load, outputs=panels)
    return demo


def make_stats():
    with gr.Blocks() as demo:
        gr.HTML(title_html("통계 · 유형별 · 안전모 · 시간대별"), elem_classes="t2-title-block")
        box = gr.HTML()
        demo.load(lambda: stats_html(load_df()), outputs=box)
    return demo


def launch():
    grid = main_clips()
    cams = pack_clips()
    seed = load_df()
    demos = [
        (TABS[0]["name"], make_main(seed, grid)),
        (TABS[1]["name"], make_detail("collision", "지게차 충돌 관제")),
        (TABS[2]["name"], make_detail("zone", "위험구역 접근 관제")),
        (TABS[3]["name"], make_detail("dwell", "위험구역 체류 관제", extra="dwell")),
        (TABS[4]["name"], make_detail("ppe", "안전모 관제")),
        (TABS[5]["name"], make_alerts()),
        (TABS[6]["name"], make_history()),
        (TABS[7]["name"], make_cctv(seed, cams)),
        (TABS[8]["name"], make_stats()),
    ]
    allowed = [str(DATA_ROOT), str(VIDEO_DIR), LOCAL, str(DATA_ROOT / "outputs")]
    os.makedirs(LOCAL, exist_ok=True)
    for path in grid + cams + [detect_video(sid) for sid in VIDEO_FILES] + [overlay_clip(5)]:
        if path and os.path.isfile(path):
            allowed.append(os.path.dirname(path))
    with gr.Blocks(title=TITLE, theme=make_theme(), css=CSS, js=BOOT_JS) as app:
        theme_btn = gr.Button("밤", elem_id="sisun-theme-btn", size="sm")
        gr.HTML(header_html())
        with gr.Tabs():
            for name, block in demos:
                with gr.Tab(name):
                    block.render()
        theme_btn.click(fn=None, js=TOGGLE_JS, outputs=theme_btn)
    app.launch(
        inbrowser=True,
        allowed_paths=allowed,
        theme=make_theme(),
        css=CSS,
        js=BOOT_JS,
    )


if __name__ == "__main__":
    ensure_repo_demos()
    ensure_api()
    df = load_df()
    print("repo", DATA_ROOT)
    print("API", API_BASE, "rows", len(df))
    print("videos", VIDEO_DIR, [n for n in pack_video_names() if video_path(n)])
    print("open http://127.0.0.1:7860")
    launch()
