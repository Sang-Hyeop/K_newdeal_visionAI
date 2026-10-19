# 경로·구역·탭 이름. GitHub 한글 라벨도 여기서 연다.
import os
import sys
from datetime import datetime
from pathlib import Path

# dashboard/ = 이 패키지, 저장소 루트 = REPO (영상·handoff 탐색)
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DASHBOARD_DIR)
HERE = REPO_ROOT
if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)
    DASHBOARD_DIR = HERE
LOCAL = os.path.join(DASHBOARD_DIR, "data")
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
ADMINS = {
    "김상협": "1234",
    "이수민": "1234",
    "박회승": "1234",
    "최인승": "1234",
}
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

# 현장: 창고 A(4) / 창고 B(1) / 옥외 구역(1·영상6은 fire_integration 에서 추가)
# 메인 = 원본 6칸 + 소제목, 사이드 = 카메라별 감지 상세
SITES = [
    {"id": "wh_a", "name": "창고 A", "color": "#2563eb"},
    {"id": "wh_b", "name": "창고 B", "color": "#0d9488"},
]
CAMERAS = [
    {
        "id": "A1", "site": "wh_a", "name": "창고 A", "zone": "하역장 진입로", "cam": "CAM01",
        "color": "#ef4444", "video_num": 1, "scenario": "collision",
        "src": _src_video(1), "origin": "origin_A1.mp4", "detect": "detect_A1.mp4",
    },
    {
        "id": "A2", "site": "wh_a", "name": "창고 A", "zone": "자동화 설비구역", "cam": "CAM02",
        "color": "#f59e0b", "video_num": 2, "scenario": "zone",
        "src": _src_video(2), "origin": "origin_A2.mp4", "detect": "detect_A2.mp4",
    },
    {
        "id": "A3", "site": "wh_a", "name": "창고 A", "zone": "포장 작업구역", "cam": "CAM03",
        "color": "#3b82f6", "video_num": 3, "scenario": "ppe",
        "src": _src_video(3), "origin": "origin_A3.mp4", "detect": "detect_A3.mp4",
    },
    {
        "id": "A4", "site": "wh_a", "name": "창고 A", "zone": "작업자 교차통로", "cam": "CAM04",
        "color": "#8b5cf6", "video_num": 4, "scenario": "dwell",
        "src": _src_video(4), "origin": "origin_A4.mp4", "detect": "detect_A4.mp4",
    },
    {
        "id": "B1", "site": "wh_b", "name": "창고 B", "zone": "물류 적재구역", "cam": "CAM05",
        "color": "#22c55e", "video_num": 5, "scenario": None,
        "src": _src_video(5), "origin": "origin_B1.mp4", "detect": "detect_B1.mp4",
    },
]
# events.py 등 기존 ZONES 참조 호환 (카메라 = 관제 위치)
ZONES = CAMERAS
CAM_BY_ID = {c["id"]: c for c in CAMERAS}
SITE_BY_ID = {s["id"]: s for s in SITES}


def cameras_of(site_id):
    return [c for c in CAMERAS if c["site"] == site_id]


def is_warehouse_video(name):
    """5번 물류창고 = 창고 B CAM05."""
    text = str(name or "")
    return text == WAREHOUSE_VIDEO or "Logistics Warehouse" in text


SCENARIOS = [
    {"id": "collision", "name": "지게차 충돌", "color": "#ef4444", "cam": "CAM01"},
    {"id": "zone", "name": "위험구역 침범", "color": "#f59e0b", "cam": "CAM02"},
    {"id": "ppe", "name": "안전모 미착용", "color": "#3b82f6", "cam": "CAM03"},
    {"id": "dwell", "name": "위험구역 체류", "color": "#8b5cf6", "cam": "CAM04"},
]


def area_of_video(name):
    text = str(name or "")
    if is_warehouse_video(text):
        return CAM_BY_ID["B1"]
    by_file = {c["src"]: c for c in CAMERAS}
    return by_file.get(text)


def cam_location_label(cam):
    """Keep existing site/zone names; outdoor uses its existing zone name."""
    zone = str(cam.get("zone") or "").strip()
    site = str(cam.get("name") or "").strip()
    if cam.get("site") in ("outdoor", "parking") or site == "옥외 구역":
        return zone or "옥외 주차장"
    return " ".join(part for part in (site, zone) if part)


def cam_main_label(cam):
    """One camera label shared by grid, detail header and tags."""
    camera = str(cam.get("cam") or "").upper()
    location = cam_location_label(cam)
    return " · ".join(part for part in (camera, location) if part)


def cam_side_label(cam):
    return cam_main_label(cam)


def cam_tag(cam):
    return cam_main_label(cam)


def cam_sidebar_label(cam):
    """Two lines in the narrow sidebar, without introducing a second numbering."""
    camera = str(cam.get("cam") or "").upper()
    location = cam_location_label(cam)
    if cam.get("site") in ("outdoor", "parking") or cam.get("name") == "옥외 구역":
        return f"{camera} · {location}"
    site = str(cam.get("name") or "").strip()
    zone = str(cam.get("zone") or "").strip()
    return " · ".join(part for part in (camera, site) if part) + (f"\n{zone}" if zone else "")


def build_tabs():
    """Camera numbers identify cameras; ordinary menus have names only."""
    tabs = [{"id": "main", "name": "메인 관제", "kind": "main"}]
    tabs.extend({
        "id": cam["id"], "name": cam_sidebar_label(cam),
        "kind": "camera", "camera_id": cam["id"],
    } for cam in CAMERAS)
    # CAM06 바로 아래: 경보·조치 관리 (카메라 id 와 겹치지 않는 안정 id)
    tabs.append({"id": "cases", "name": "경보·조치 관리", "kind": "cases"})
    tabs.extend({"id": key, "name": name, "kind": key} for key, name in (
        ("history", "이벤트 이력"), ("data", "운영 통계"),
    ))
    return tabs


TABS = build_tabs()


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
SC_BY_ID = {s["id"]: s for s in SCENARIOS}
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
    return SC_BY_ID[sid]


# Optional sixth camera; warehouse settings above stay intact.
from .fire_integration import register as _register_fire
_register_fire(globals())
