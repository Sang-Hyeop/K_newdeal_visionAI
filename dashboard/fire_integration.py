"""Add video6 (옥외 주차장) when the source file exists."""


def register(namespace):
    video_dir = namespace["VIDEO_DIR"]
    if not (video_dir / "6_parking_lot_fire.mp4").exists():
        return
    if "P1" in namespace["CAM_BY_ID"] or "outdoor" in namespace["SITE_BY_ID"]:
        # 이미 config 에 있으면 시나리오·탭만 보강
        _ensure_fire_scenario(namespace)
        namespace["TABS"] = namespace["build_tabs"]()
        return

    video = "6_parking_lot_fire.mp4"
    site = {"id": "outdoor", "name": "옥외 구역", "color": "#dc2626"}
    camera = {
        "id": "P1",
        "site": "outdoor",
        "name": "옥외 구역",
        "zone": "옥외 주차장",
        "cam": "CAM06",
        "color": "#dc2626",
        "video_num": 6,
        "scenario": "fire",
        "src": video,
        "origin": "origin_P1.mp4",
        "detect": "detect_P1.mp4",
    }
    namespace["SITES"].append(site)
    namespace["SITE_BY_ID"][site["id"]] = site
    namespace["CAMERAS"].append(camera)
    namespace["CAM_BY_ID"][camera["id"]] = camera
    namespace["ZONES"] = namespace["CAMERAS"]
    _ensure_fire_scenario(namespace)
    namespace["NEEDED_VIDEOS"] = tuple(namespace["NEEDED_VIDEOS"]) + (6,)
    namespace["TABS"] = namespace["build_tabs"]()


def _ensure_fire_scenario(namespace):
    if "fire" in namespace.get("SC_BY_ID", {}):
        return
    scenario = {"id": "fire", "name": "화재 감지", "color": "#dc2626", "cam": "CAM06"}
    namespace["SCENARIOS"].append(scenario)
    namespace["SC_BY_ID"]["fire"] = scenario
    namespace["SID_TO_VIDEO"]["fire"] = 6
    namespace["SID_TO_EVENT_TYPE"]["fire"] = "fire"
    namespace["VIDEO_FILES"]["fire"] = "6_parking_lot_fire.mp4"
    namespace["TYPE_TO_SCENARIO"]["fire"] = "fire"
    if 6 not in namespace["NEEDED_VIDEOS"]:
        namespace["NEEDED_VIDEOS"] = tuple(namespace["NEEDED_VIDEOS"]) + (6,)
