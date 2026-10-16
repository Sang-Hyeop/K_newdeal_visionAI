# 경로·구역·탭 이름. GitHub 한글 라벨도 여기서 연다.
import os
import sys
from datetime import datetime
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)
LOCAL = os.path.join(HERE, "team7_data")
ALARM_PATH = os.path.join(LOCAL, "alarm.wav")
WARN_PATH = os.path.join(LOCAL, "warn.wav")

DATA_CANDIDATES = [
    Path(os.environ["SISUN_DATA"]) if os.environ.get("SISUN_DATA") else None,
    Path(HERE),
    Path(HERE) / "K_newdeal_visionAI_main",
    Path(HERE).parent / "K_newdeal_visionAI_main",
    Path(r"c:\code\K_newdeal_visionAI_main"),
    Path(r"c:\code\K_newdeal_visionAI"),
    Path(HERE) / "K_newdeal_visionAI",
    Path(HERE).parent.parent / "K_newdeal_visionAI",
]
DATA_CANDIDATES = [p for p in DATA_CANDIDATES if p]
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
SID_TO_VIDEO = {"collision": 1, "zone": 2, "ppe": 3, "dwell": 4}
NEEDED_VIDEOS = (1, 2, 3, 4, 5)

VIDEO_DIR = DATA_ROOT / "data" / "videos"

TITLE = "시선 - 스마트 안전관제"
ADMINS = {"qwer1": "1234", "qwer2": "1234"}
CCTV_TAB = 1
OPERATOR = "안전 당직"
PAGE_BG = "#0f172a"


def clock_start():
    """로그 시각: 오늘 날짜 + 09:00:00 시작."""
    now = datetime.now()
    return datetime(now.year, now.month, now.day, 9, 0, 0)


def _clock_fields(ts):
    return {
        "year": ts.year,
        "month": ts.month,
        "day": ts.day,
        "hour": ts.hour,
        "minute": ts.minute,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
    }


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


def is_warehouse_video(name):
    """5번 물류창고 = A구역."""
    text = str(name or "")
    return text == WAREHOUSE_VIDEO or "Logistics Warehouse" in text


TABS = [
    {"id": "main", "name": "#1 메인 관제"},
    {"id": "A", "name": "#2 A구역"},
    {"id": "B", "name": "#3 B구역"},
    {"id": "C", "name": "#4 C구역"},
    {"id": "D", "name": "#5 D구역"},
    {"id": "E", "name": "#6 E구역"},
    {"id": "alerts", "name": "#7 통합 알람"},
    {"id": "history", "name": "#8 이벤트 이력"},
    {"id": "data", "name": "#9 통합데이터"},
]
SCENARIOS = [
    {"id": "collision", "name": "지게차 충돌", "color": "#ef4444", "cam": "CAM02"},
    {"id": "zone", "name": "위험구역 침범", "color": "#f59e0b", "cam": "CAM03"},
    {"id": "dwell", "name": "위험구역 체류", "color": "#8b5cf6", "cam": "CAM04"},
    {"id": "ppe", "name": "안전모 미착용", "color": "#3b82f6", "cam": "CAM05"},
]
ZONES = [
    {"id": "A", "name": "A구역", "color": "#ef4444", "cam": "CAM01"},
    {"id": "B", "name": "B구역", "color": "#f59e0b", "cam": "CAM02"},
    {"id": "C", "name": "C구역", "color": "#8b5cf6", "cam": "CAM03"},
    {"id": "D", "name": "D구역", "color": "#3b82f6", "cam": "CAM04"},
    {"id": "E", "name": "E구역", "color": "#22c55e", "cam": "CAM05"},
]


def area_of_video(name):
    text = str(name or "")
    if is_warehouse_video(text):
        return ZONES[0]
    by_file = {
        VIDEO_FILES["collision"]: ZONES[1],
        VIDEO_FILES["zone"]: ZONES[2],
        VIDEO_FILES["dwell"]: ZONES[3],
        VIDEO_FILES["ppe"]: ZONES[4],
        WAREHOUSE_VIDEO: ZONES[0],
    }
    return by_file.get(text)


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
ZONE_KINDS = {"zone_access"}
GRADE_RANK = {"위험": 3, "주의": 2, "안전": 1, "미확인": 0}
GRADE_EN = {"안전": "SAFE", "주의": "WARN", "위험": "CRIT", "미확인": "UNKNOWN"}
SID_TO_EVENT_TYPE = {
    "collision": "proximity",
    "zone": "zone_access",
    "dwell": "zone_dwell",
    "ppe": "ppe",
}
for _sc in SCENARIOS:
    _sc["name"] = ko.event_type_label(SID_TO_EVENT_TYPE[_sc["id"]])
STATUS_FG = {
    "안전": "#22c55e", "주의": "#eab308", "위험": "#ef4444",
    "없음": "#94a3b8", "대기": "#22c55e", "미확인": "#94a3b8",
    "착용": "#22c55e", "미착용": "#ef4444",
    "안전모 착용 감지": "#22c55e", "안전모 미착용 감지": "#ef4444",
}
PPE_SPLIT_SEC = 6.0
INK_TITLE = "color:var(--sisun-title,#f8fafc)!important"
INK_CARD = "background:var(--sisun-card-bg,#1e293b)!important;color:var(--sisun-card-fg,#f8fafc)!important"
INK_CELL = "color:var(--sisun-table-fg,#f8fafc)!important;background:var(--sisun-table-bg,#1e293b)!important"
INK_HEAD = "color:var(--sisun-table-fg,#f8fafc)!important;background:var(--sisun-th-bg,#334155)!important"
INK_MUTED = "color:var(--sisun-muted,#cbd5e1)!important"
INK_FG = "color:var(--sisun-card-fg,#f8fafc)!important"
ROW_COLS = [
    "event_id", "scenario", "event_type", "status", "grade",
    "year", "month", "day", "hour", "minute",
    "timestamp", "camera", "zone", "area", "dwell_sec",
    "distance_px", "message", "frame", "video", "person_no",
    "worker", "obj_x", "track_id",
]


def sc_of(sid):
    return next(s for s in SCENARIOS if s["id"] == sid)
