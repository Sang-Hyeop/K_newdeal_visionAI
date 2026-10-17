# API 이벤트를 표 한 줄로. 사람·지게차 단위로 접음
import threading
from datetime import timedelta

import pandas as pd

from .api import load_events, presentation_row
from .config import (
    COLLISION_KINDS,
    DATA_ROOT,
    DWELL_KINDS,
    GRADE_EN,
    GRADE_RANK,
    PPE_SPLIT_SEC,
    ROW_COLS,
    SID_TO_VIDEO,
    TYPE_TO_SCENARIO,
    VIDEO_FILES,
    WAREHOUSE_VIDEO,
    ZONE_KINDS,
    ZONES,
    area_of_video,
    clock_start,
    ko,
    _clock_fields,
)
from .records import iter_jsonl, jsonl_snapshot, read_jsonl as _read_jsonl
from .sound import write_beep

_DF_LOCK = threading.Lock()
_DF_CACHE = None
_DF_READY = False


def get_df():
    """캐시 DataFrame 읽기 전용(복사 없음). 호출부에서 수정하지 말 것."""
    if not _DF_READY or _DF_CACHE is None:
        return None
    return _DF_CACHE


def peek_df():
    """로그인 버튼을 막지 않음. 아직이면 None. 안전 복사본."""
    df = get_df()
    return None if df is None else df.copy()


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


def _object_ids(ev):
    evid = ev.get("evidence") if isinstance(ev.get("evidence"), dict) else {}
    ids = [str(x) for x in (ev.get("track_ids") or [])]
    person = str(evid.get("person_track_id") or evid.get("track_id") or "")
    fork = str(evid.get("forklift_track_id") or "")
    if not fork:
        extra = evid.get("vehicle_track_ids") or ev.get("vehicle_track_ids") or evid.get("forklift_track_ids") or []
        if extra:
            fork = str(extra[0])
    if not person:
        person = next((x for x in ids if x[:1] not in "FH"), "")
    if not fork:
        fork = next((x for x in ids if x[:1] == "F"), "")
    return person, fork




def _object_x(ev):
    evid = ev.get("evidence") if isinstance(ev.get("evidence"), dict) else {}
    box = evid.get("person_bbox_xyxy") or evid.get("forklift_bbox_xyxy") or evid.get("head_bbox_xyxy") or [0]
    try:
        return float(box[0])
    except (TypeError, IndexError, ValueError):
        return 0.0






def _log_row(
    event_id, scenario, event_type, status, grade, ts,
    camera, zone, area, message, video, person_no,
    dwell_sec="", distance_px="", frame="", track_id=None,
    obj_x="", worker="",
):
    row = {
        "event_id": event_id,
        "scenario": scenario,
        "event_type": event_type,
        "status": status,
        "grade": grade,
        **_clock_fields(ts),
        "camera": camera,
        "zone": zone,
        "area": area,
        "dwell_sec": dwell_sec,
        "distance_px": distance_px,
        "message": message,
        "frame": frame,
        "video": video,
        "person_no": person_no,
        "worker": worker,
        "obj_x": obj_x,
        "track_id": track_id or "",
    }
    return row


def event_to_row(ev):
    kind = ev.get("event_type", "")
    if kind == "fire":
        row = _row_fields(ev)
        if row:
            evidence = ev.get("evidence") or {}
            reason = evidence.get("reason") or ev.get("status_reason")
            if ev.get("alert_eligible"):
                row["status"], row["message"] = "화재 의심", "반복 관측에 따른 화재 의심"
            elif reason == "pending_temporal_confirmation":
                row["status"], row["message"] = "확인 중", "불꽃 감지 · 반복 관측 확인 중"
            elif reason == "fire_not_observed":
                row["status"], row["message"] = "관측 소실", "현재 불꽃 관측 소실 · 진화 여부 확인 필요"
            else:
                row["status"], row["message"] = "판정 불가", "불꽃 판정 근거 부족"
            row["worker"] = "불꽃"
            row["track_id"] = ",".join(ev.get("track_ids") or [])
            # Keep subsecond transitions distinguishable in the history table.
            sec = float(ev.get("timestamp_seconds") or 0)
            row["timestamp"] = (clock_start() + timedelta(seconds=sec)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-5]
        return row
    if kind == "ppe" or kind in COLLISION_KINDS or kind in DWELL_KINDS or kind in ZONE_KINDS:
        return None
    return _row_fields(ev)


def _row_fields(ev):
    kind = ev.get("event_type", "")
    sid = TYPE_TO_SCENARIO.get(kind)
    if sid is None:
        return None
    video = ev.get("video") or ""
    area = area_of_video(video)
    if area is None:
        return None
    view = ko.display_view(ev)
    evid = ev.get("evidence") if isinstance(ev.get("evidence"), dict) else {}
    sec = float(ev.get("timestamp_seconds") or 0)
    ts = clock_start() + timedelta(seconds=sec)
    stay = evid.get("observed_dwell_seconds") or evid.get("dwell_seconds") or evid.get("stay_seconds")
    gap = evid.get("image_gap_pixels")
    grade = event_status(ev)
    st = grade
    if kind == "ppe" and grade != "미확인" and view.get("ppe_state_label"):
        st = view["ppe_state_label"]
    return _log_row(
        str(ev.get("event_id", ""))[:12], sid, kind, st, grade, ts,
        area["cam"], area["name"], area["id"], event_message(ev), video, 0,
        dwell_sec="" if stay in (None, "") else float(stay),
        distance_px="" if gap in (None, "") else float(gap),
        track_id=_person_tid(ev),
        obj_x=_object_x(ev),
    )



def detections_path(sid):
    num = SID_TO_VIDEO.get(sid)
    row = presentation_row(num) if num else None
    rel = (row or {}).get("diagnostic_root")
    if rel:
        path = DATA_ROOT / rel / "detections.jsonl"
        if path.is_file():
            return path
    found = list((DATA_ROOT / "outputs" / "diagnostics").glob(f"presentation{num}*/**/detections.jsonl"))
    return found[0] if found else None


def warehouse_detections_path():
    row = presentation_row(5)
    rel = (row or {}).get("diagnostic_root")
    if rel:
        path = DATA_ROOT / rel / "detections.jsonl"
        if path.is_file():
            return path
    found = list((DATA_ROOT / "outputs" / "diagnostics").glob("presentation5*/**/detections.jsonl"))
    return found[0] if found else None


def ppe_detections_path():
    return detections_path("ppe")




def _ppe_track_x(tr):
    box = tr.get("detected_bbox_xyxy") or tr.get("bbox_xyxy") or [0, 0, 0, 0]
    return float(box[0])


def _ppe_track_wear(tr):
    st = str((tr.get("ppe") or {}).get("state") or "")
    if st == "no_helmet_candidate":
        return "미착용"
    if st == "helmet_detected":
        return "착용"
    return ""


def _ppe_track_id(tr):
    return str(tr.get("track_id") or "")


def _ppe_appear_rows(recs, t0, t1, video, area, start_idx):
    """장면 안에서 사람·미착용자가 처음 확정된 시각에 1줄."""
    active = []
    rows = []
    idx = start_idx
    match_px = 90.0
    timed = []
    for rec in recs:
        t = float(rec.get("timestamp_seconds") or 0)
        if t < t0 or t >= t1:
            continue
        timed.append((t, rec.get("ppe_tracks") or []))
    timed.sort()
    for t, tracks in timed:
        decided = []
        for tr in tracks:
            wear = _ppe_track_wear(tr)
            if not wear:
                continue
            decided.append((tr, wear, _ppe_track_x(tr), _ppe_track_id(tr)))
        used = set()
        for person in active:
            hit = None
            for i, (tr, wear, x, tid) in enumerate(decided):
                if i in used:
                    continue
                if tid and tid == person["tid"]:
                    hit = i
                    break
            if hit is None:
                best_d = match_px
                for i, (tr, wear, x, tid) in enumerate(decided):
                    if i in used:
                        continue
                    d = abs(x - person["x"])
                    if d < best_d:
                        best_d = d
                        hit = i
            if hit is not None:
                _tr, _wear, x, tid = decided[hit]
                person["x"] = x
                if tid:
                    person["tid"] = tid
                used.add(hit)
        for i, (tr, wear, x, tid) in enumerate(decided):
            if i in used:
                continue
            idx += 1
            n = len(active) + 1
            tag = "WORN" if wear == "착용" else "NOT WORN"
            ts = clock_start() + timedelta(seconds=t)
            rows.append(_log_row(
                f"P{idx:02d}", "ppe", "ppe", wear,
                "안전" if wear == "착용" else "주의",
                ts, area["cam"], area["name"], area["id"],
                f"{n} {tag}", video, n,
                track_id=tid, obj_x=x,
            ))
            active.append({"x": x, "tid": tid})
    return rows, idx


def ppe_scene_rows():
    """사람이 나오는 즉시 착용, 미착용자가 나오는 즉시 미착용. 사람 1명 = 1줄."""
    path = ppe_detections_path()
    if path is None:
        return []
    recs = _read_jsonl(path)
    video = VIDEO_FILES["ppe"]
    area = area_of_video(video) or ZONES[2]  # 창고 A CAM03 (PPE)
    rows = []
    idx = 0
    for t0, t1 in ((0.0, PPE_SPLIT_SEC), (PPE_SPLIT_SEC, 99.0)):
        part, idx = _ppe_appear_rows(recs, t0, t1, video, area, idx)
        rows.extend(part)
    return rows


def _match_person(now, used, x, tid, match_px=90.0):
    """now 항목: (x, h, tid, sev, stay)."""
    if tid:
        for i, item in enumerate(now):
            if i in used:
                continue
            if item[2] and item[2] == tid:
                return i
    hit = None
    best_d = match_px
    for i, item in enumerate(now):
        if i in used:
            continue
        d = abs(item[0] - x)
        if d < best_d:
            best_d = d
            hit = i
    return hit


def d_zone_ppe_rows():
    """시작 2명 바로 미착용, 뒤에 나오는 2명도 나오는 즉시 미착용."""
    path = detections_path("dwell")
    if path is None:
        return []
    recs = _read_jsonl(path)
    area = ZONES[3]  # 창고 A CAM04 (체류)
    video = VIDEO_FILES["dwell"]
    active = []
    rows = []
    min_h = 120.0
    for rec in recs:
        t = float(rec.get("timestamp_seconds") or 0)
        now = []
        for obj in rec.get("object_detections") or []:
            if obj.get("class") != "person":
                continue
            box = obj.get("bbox_xyxy") or [0, 0, 0, 0]
            x1, y1, x2, y2 = [float(v) for v in box[:4]]
            if (y2 - y1) < min_h:
                continue
            now.append(x1)
        used = set()
        for person in active:
            hit = None
            best_d = 90.0
            for i, x in enumerate(now):
                if i in used:
                    continue
                d = abs(x - person["x"])
                if d < best_d:
                    best_d = d
                    hit = i
            if hit is not None:
                person["x"] = now[hit]
                used.add(hit)
        for i, x in enumerate(now):
            if i in used:
                continue
            n = len(active) + 1
            if n > 4:
                continue
            ts = clock_start() + timedelta(seconds=t)
            rows.append(_log_row(
                f"DH{n:02d}", "ppe", "ppe", "미착용", "주의",
                ts, area["cam"], area["name"], area["id"],
                f"{n} NOT WORN", video, n,
                obj_x=x,
            ))
            active.append({"x": x})
    return rows


def d_zone_dwell_rows():
    """주의 1명은 주의가 시작된 시각, 안전 3명은 화면에서 사라질 때."""
    path = detections_path("dwell")
    if path is None:
        return []
    recs = _read_jsonl(path)
    area = ZONES[3]
    video = VIDEO_FILES["dwell"]
    active = []
    for rec in recs:
        t = float(rec.get("timestamp_seconds") or 0)
        evs = ((rec.get("zone") or {}).get("events") or [])
        now = []
        for ev in evs:
            if ev.get("inside") is None and ev.get("severity") is None:
                continue
            box = ev.get("person_bbox_xyxy") or [0, 0, 0, 0]
            x = float(box[0] or 0)
            h = float(box[3] - box[1]) if len(box) > 3 else 0
            tid = str(ev.get("track_id") or "")
            sev = ev.get("severity")
            stay = ev.get("observed_dwell_seconds")
            now.append((x, h, tid, sev, stay))
        used = set()
        for person in active:
            hit = _match_person(now, used, person["x"], person.get("tid"))
            if hit is not None:
                x, h, tid, sev, stay = now[hit]
                person["x"] = x
                person["last_t"] = t
                if tid:
                    person["tid"] = tid
                if stay not in (None, ""):
                    try:
                        person["stay"] = float(stay)
                    except (TypeError, ValueError):
                        pass
                if str(sev or "").upper() == "WARNING" and person.get("warn_t") is None:
                    person["warn_t"] = t
                    person["warn_stay"] = person.get("stay")
                used.add(hit)
        for i, (x, h, tid, sev, stay) in enumerate(now):
            if i in used:
                continue
            if h < 100 and not any(p.get("tid") == tid for p in active if tid):
                continue
            person = {
                "x": x, "tid": tid, "first_t": t, "last_t": t, "first_x": x,
                "warn_t": t if str(sev or "").upper() == "WARNING" else None,
                "stay": float(stay) if stay not in (None, "") else 0.0,
                "warn_stay": None,
            }
            if person["warn_t"] is not None:
                person["warn_stay"] = person["stay"]
            active.append(person)
    # 오래 보인 사람 4명
    active.sort(key=lambda p: (p["last_t"] - p["first_t"]), reverse=True)
    chosen = active[:4]
    chosen.sort(key=lambda p: p["first_t"])
    rows = []
    for i, person in enumerate(chosen, 1):
        if person.get("warn_t") is not None:
            ts = clock_start() + timedelta(seconds=person["warn_t"])
            grade = "주의"
            stay = person.get("warn_stay") or person.get("stay") or ""
        else:
            ts = clock_start() + timedelta(seconds=person["last_t"])
            grade = "안전"
            stay = person.get("stay") or ""
        tag = GRADE_EN.get(grade, "UNKNOWN")
        bits = [f"{i} 사람 {tag}"]
        row = _log_row(
            f"DD{i:02d}", "dwell", "zone_dwell", grade, grade,
            ts, area["cam"], area["name"], area["id"],
            " · ".join(bits), video, i,
            dwell_sec=stay if stay not in ("", None) and float(stay or 0) > 0 else "",
            track_id=person.get("tid"), obj_x=person.get("first_x", person.get("x")),
        )
        rows.append(row)
    return rows


def c_zone_access_rows():
    """처음엔 안전, 위험구역에 들어가는 즉시 위험."""
    path = detections_path("zone")
    if path is None:
        return []
    recs = _read_jsonl(path)
    area = ZONES[1]  # 창고 A CAM02 (위험구역)
    video = VIDEO_FILES["zone"]
    active = []
    for rec in recs:
        t = float(rec.get("timestamp_seconds") or 0)
        evs = ((rec.get("feature_events") or {}).get("zone_access") or [])
        now = []
        for ev in evs:
            box = ev.get("person_bbox_xyxy") or ev.get("bbox_xyxy") or [0, 0, 0, 0]
            x = float(box[0] or 0)
            h = float(box[3] - box[1]) if len(box) > 3 else 0
            tid = str(ev.get("track_id") or "")
            sev = str(ev.get("severity") or "").upper()
            inside = ev.get("inside") is True or str(ev.get("region") or "") == "inside"
            hot = inside or sev in ("CRITICAL", "HIGH", "DANGER")
            now.append((x, h, tid, hot))
        used = set()
        for person in active:
            hit = _match_person(now, used, person["x"], person.get("tid"))
            if hit is not None:
                x, h, tid, hot = now[hit]
                person["x"] = x
                person["last_t"] = t
                if tid:
                    person["tid"] = tid
                if hot and person.get("enter_t") is None:
                    person["enter_t"] = t
                used.add(hit)
        for i, (x, h, tid, hot) in enumerate(now):
            if i in used:
                continue
            if h < 80 and not any(p.get("tid") == tid for p in active if tid):
                continue
            active.append({
                "x": x, "tid": tid, "first_t": t, "last_t": t,
                "enter_t": t if hot else None,
            })
    active.sort(key=lambda p: p["first_t"])
    rows = []
    for i, person in enumerate(active, 1):
        first = person["first_t"]
        enter = person.get("enter_t")
        if enter is None or enter > first + 0.05:
            ts = clock_start() + timedelta(seconds=first)
            tag = GRADE_EN["안전"]
            rows.append(_log_row(
                f"CZ{i:02d}S", "zone", "zone_access", "안전", "안전",
                ts, area["cam"], area["name"], area["id"],
                f"{i} 사람 {tag}", video, i,
                track_id=person.get("tid"), obj_x=person.get("x"),
            ))
        if enter is not None:
            ts = clock_start() + timedelta(seconds=enter)
            tag = GRADE_EN["위험"]
            rows.append(_log_row(
                f"CZ{i:02d}D", "zone", "zone_access", "위험", "위험",
                ts, area["cam"], area["name"], area["id"],
                f"{i} 사람 {tag}", video, i,
                track_id=person.get("tid"), obj_x=person.get("x"),
            ))
    return rows


def _box_overlap_frac(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    area = max(1.0, (ax2 - ax1) * (ay2 - ay1))
    return (iw * ih) / area


def _on_forklift(pbox, fbox):
    """운전석·차체에 올라탄 사람. 뒤에 앉은 작업자·멀리 있는 사람은 아님."""
    if fbox is None:
        return False
    cx = (pbox[0] + pbox[2]) / 2.0
    if not (fbox[0] <= cx <= fbox[2]):
        return False
    return _box_overlap_frac(pbox, fbox) >= 0.35


def _prox_grade(sev):
    s = str(sev or "").upper()
    if s in ("CRITICAL", "HIGH", "DANGER"):
        return "위험"
    if s == "WARNING":
        return "주의"
    if s == "SAFE":
        return "안전"
    return ""


def _b_record_grade(person, grade, gap, t):
    logs = person.setdefault("logs", [])
    last = logs[-1]["grade"] if logs else None
    if grade == last:
        return
    if grade == "미확인":
        if person.get("seen_unknown"):
            return
        person["seen_unknown"] = True
    elif grade == "위험":
        if person["seen_crit"] and last != "미확인":
            return
        person["seen_crit"] = True
        person["seen_warn"] = True
    elif grade == "주의":
        person["seen_warn"] = True
    elif grade == "안전":
        if not person["seen_warn"] and person.get("rear"):
            return
    logs.append({"t": t, "grade": grade, "gap": gap, "x": person.get("x")})


def b_zone_collision_rows():
    """지게차 운전자는 제외. 뒤 작업자 주의→안전, 먼 사람 안전→주의→위험, 가려지면 미확인, 지나친 뒤 위험→멀면 안전."""
    path = detections_path("collision")
    if path is None:
        return []
    recs = _read_jsonl(path)
    area = ZONES[0]  # 창고 A CAM01 (충돌)
    video = VIDEO_FILES["collision"]
    active = []
    min_h = 100.0
    for rec in recs:
        t = float(rec.get("timestamp_seconds") or 0)
        objs = rec.get("object_detections") or []
        forks = [
            [float(v) for v in (o.get("bbox_xyxy") or [0, 0, 0, 0])[:4]]
            for o in objs
            if "fork" in str(o.get("class") or "").lower()
        ]
        fbox = forks[0] if forks else None
        people = []
        for obj in objs:
            if obj.get("class") != "person":
                continue
            box = [float(v) for v in (obj.get("bbox_xyxy") or [0, 0, 0, 0])[:4]]
            h = box[3] - box[1]
            if h < min_h:
                continue
            people.append({"x": box[0], "box": box, "on_fork": _on_forklift(box, fbox)})
        confirmed = []
        for ev in ((rec.get("feature_events") or {}).get("proximity") or []):
            if ev.get("observation_status") == "unconfirmed":
                continue
            grade = _prox_grade(ev.get("severity"))
            if not grade:
                continue
            box = ev.get("person_bbox_xyxy") or [0]
            confirmed.append((
                float(box[0] or 0),
                str(ev.get("person_track_id") or ""),
                grade,
                ev.get("image_gap_pixels"),
            ))
        used = set()
        for person in active:
            hit = None
            best = 140.0
            for i, p in enumerate(people):
                if i in used:
                    continue
                d = abs(p["x"] - person["x"])
                if d < best:
                    best = d
                    hit = i
            if hit is None:
                continue
            p = people[hit]
            used.add(hit)
            person["x"] = p["x"]
            person["last_t"] = t
            now = None
            for x, tid, grade, gap in confirmed:
                if tid and tid == person.get("tid"):
                    now = (grade, gap, tid)
                    break
            if now is None:
                for x, tid, grade, gap in confirmed:
                    if abs(x - person["x"]) < 90:
                        now = (grade, gap, tid)
                        break
            if now and now[2]:
                person["tid"] = now[2]
            if p["on_fork"] and not person.get("rear"):
                gap = now[1] if now else None
                _b_record_grade(person, "미확인", gap, t)
                continue
            if now is None:
                continue
            grade, gap, tid = now
            _b_record_grade(person, grade, gap, t)
        if fbox is None:
            for person in active:
                if person.get("rear"):
                    continue
                last = (person.get("logs") or [{}])[-1].get("grade") if person.get("logs") else None
                if last in ("위험", "미확인"):
                    _b_record_grade(person, "안전", None, t)
        elif fbox is not None:
            for person in active:
                if person.get("rear") or person.get("seen_unknown"):
                    continue
                if person.get("last_t") == t:
                    continue
                if person.get("seen_warn") or person.get("seen_crit"):
                    _b_record_grade(person, "미확인", None, t)
        for i, p in enumerate(people):
            if i in used:
                continue
            if p["on_fork"]:
                continue
            person = {
                "x": p["x"],
                "first_t": t,
                "last_t": t,
                "tid": "",
                "rear": p["x"] > 1200,
                "seen_warn": False,
                "seen_crit": False,
                "seen_unknown": False,
                "logs": [],
            }
            for x, tid, grade, gap in confirmed:
                if abs(x - p["x"]) < 90:
                    person["tid"] = tid
                    _b_record_grade(person, grade, gap, t)
                    break
            active.append(person)
    active.sort(key=lambda p: p["first_t"])
    rows = []
    suffix = {"안전": "S", "주의": "W", "위험": "D", "미확인": "U"}
    for i, person in enumerate(active, 1):
        seen = {}
        for item in person.get("logs") or []:
            ts = clock_start() + timedelta(seconds=item["t"])
            grade = item["grade"]
            tag = GRADE_EN.get(grade, "UNKNOWN")
            gap = item.get("gap")
            bits = [f"{i} 사람 {tag}"]
            if gap not in (None, ""):
                bits.append(f"{float(gap):.0f}px")
            key = suffix.get(grade, "X")
            seen[key] = seen.get(key, 0) + 1
            extra = "" if seen[key] == 1 else str(seen[key])
            rows.append(_log_row(
                f"BC{i:02d}{key}{extra}",
                "collision", "proximity", grade, grade,
                ts, area["cam"], area["name"], area["id"],
                " · ".join(bits), video, i,
                distance_px="" if gap in (None, "") else float(gap),
                track_id=person.get("tid"),
                obj_x=item.get("x", person.get("x")),
            ))
    return rows


def _tid_core(tid):
    s = str(tid or "")
    if ":" in s:
        return s.rsplit(":", 1)[-1]
    return s


def _a_record(person, grade, t, extra=None):
    """같은 상태가 매 프레임 반복되면 한 줄만."""
    logs = person.setdefault("logs", [])
    if logs and logs[-1]["grade"] == grade:
        return
    item = {"t": t, "grade": grade, "x": person.get("x")}
    if extra:
        item.update(extra)
    logs.append(item)


def _a_update_tracks(active, now, t, match_px=55.0):
    used = set()
    for person in active:
        hit = _match_person(now, used, person["x"], person.get("tid"), match_px=match_px)
        if hit is None:
            continue
        x, h, tid, grade, gap, stay = now[hit]
        used.add(hit)
        person["x"] = x
        person["last_t"] = t
        if tid:
            person["tid"] = tid
        extra = {}
        if gap not in (None, ""):
            extra["gap"] = gap
        if stay not in (None, ""):
            extra["stay"] = stay
        _a_record(person, grade, t, extra)
    for i, item in enumerate(now):
        if i in used:
            continue
        x, h, tid, grade, gap, stay = item
        extra = {}
        if gap not in (None, ""):
            extra["gap"] = gap
        if stay not in (None, ""):
            extra["stay"] = stay
        person = {
            "x": x, "tid": tid or "", "first_t": t, "last_t": t, "logs": [],
        }
        _a_record(person, grade, t, extra)
        active.append(person)


def _a_emit_rows(active, prefix, scenario, kind, area, video, ppe=False):
    active.sort(key=lambda p: p["first_t"])
    rows = []
    suffix = {
        "안전": "S", "주의": "W", "위험": "D", "미확인": "U",
        "착용": "H", "미착용": "N",
    }
    for i, person in enumerate(active, 1):
        seen = {}
        for item in person.get("logs") or []:
            grade = item["grade"]
            ts = clock_start() + timedelta(seconds=item["t"])
            gap = item.get("gap")
            stay = item.get("stay")
            if ppe:
                status = grade
                g = "안전" if grade == "착용" else "주의"
                tag = "WORN" if grade == "착용" else "NOT WORN"
                bits = [f"{i} {tag}"]
            else:
                status = grade
                g = grade
                tag = GRADE_EN.get(grade, "UNKNOWN")
                bits = [f"{i} 사람 {tag}"]
                if gap not in (None, ""):
                    bits.append(f"{float(gap):.0f}px")
            key = suffix.get(grade, "X")
            seen[key] = seen.get(key, 0) + 1
            extra = "" if seen[key] == 1 else str(seen[key])
            rows.append(_log_row(
                f"{prefix}{i:02d}{key}{extra}",
                scenario, kind, status, g, ts,
                area["cam"], area["name"], area["id"],
                " · ".join(bits), video, i,
                dwell_sec="" if stay in (None, "") or float(stay or 0) <= 0 else float(stay),
                distance_px="" if gap in (None, "") else float(gap),
                track_id=person.get("tid"),
                obj_x=item.get("x", person.get("x")),
            ))
    return rows


def a_zone_rows():
    """창고 B(영상 5): 충돌·안전모·체류. 사람 단위로 묶고 상태가 바뀔 때만 1줄."""
    path = warehouse_detections_path()
    if path is None:
        return []
    recs = iter_jsonl(path)
    area = ZONES[4]  # 창고 B CAM05
    video = WAREHOUSE_VIDEO
    coll, ppe, dwell = [], [], []
    for rec in recs:
        t = float(rec.get("timestamp_seconds") or 0)
        objs = rec.get("object_detections") or []
        forks = [
            [float(v) for v in (o.get("bbox_xyxy") or [0, 0, 0, 0])[:4]]
            for o in objs
            if "fork" in str(o.get("class") or "").lower()
        ]
        fbox = forks[0] if forks else None
        riders = {
            _tid_core(x)
            for x in ((rec.get("zone") or {}).get("excluded_riders") or [])
            if _tid_core(x)
        }
        fe = rec.get("feature_events") or {}
        now_c = []
        for ev in fe.get("proximity") or []:
            if ev.get("observation_status") == "unconfirmed":
                continue
            grade = _prox_grade(ev.get("severity"))
            if not grade:
                continue
            box = [float(v) for v in (ev.get("person_bbox_xyxy") or [0, 0, 0, 0])[:4]]
            tid = _tid_core(ev.get("person_track_id") or ev.get("track_id") or "")
            if tid and tid in riders:
                continue
            if _on_forklift(box, fbox):
                continue
            h = box[3] - box[1]
            if h < 40:
                continue
            now_c.append((box[0], h, tid, grade, ev.get("image_gap_pixels"), None))
        _a_update_tracks(coll, now_c, t)
        now_p = []
        for tr in rec.get("ppe_tracks") or []:
            wear = _ppe_track_wear(tr)
            if not wear:
                continue
            box = [float(v) for v in (tr.get("detected_bbox_xyxy") or tr.get("bbox_xyxy") or [0, 0, 0, 0])[:4]]
            tid = _tid_core(tr.get("track_id") or "")
            h = box[3] - box[1]
            if h < 40:
                continue
            now_p.append((box[0], h, tid, wear, None, None))
        _a_update_tracks(ppe, now_p, t)
        now_d = []
        for ev in fe.get("zone_dwell") or []:
            if ev.get("observation_status") == "unconfirmed":
                continue
            grade = _prox_grade(ev.get("severity"))
            if not grade:
                continue
            box = [float(v) for v in (ev.get("person_bbox_xyxy") or [0, 0, 0, 0])[:4]]
            tid = _tid_core(ev.get("track_id") or ev.get("person_track_id") or "")
            if tid and tid in riders:
                continue
            h = box[3] - box[1]
            if h < 40:
                continue
            stay = ev.get("observed_dwell_seconds") or ev.get("dwell_seconds")
            now_d.append((box[0], h, tid, grade, None, stay))
        _a_update_tracks(dwell, now_d, t)
    rows = []
    rows.extend(_a_emit_rows(coll, "AC", "collision", "proximity", area, video))
    rows.extend(_a_emit_rows(ppe, "AP", "ppe", "ppe", area, video, ppe=True))
    rows.extend(_a_emit_rows(dwell, "AD", "dwell", "zone_dwell", area, video))
    return rows


def _worker_letter(i):
    name = ""
    n = i + 1
    while n:
        n, r = divmod(n - 1, 26)
        name = chr(65 + r) + name
    return name


def assign_workers(rows):
    """같은 구역에서 같은 사람(위치·번호)은 작업자 A, B… 로 묶음."""
    groups = {}
    for row in rows:
        if row.get("scenario") == "fire":
            continue
        groups.setdefault(row.get("area") or "", []).append(row)
    match_of = {"A": 60.0, "B": 150.0, "C": 90.0, "D": 200.0, "E": 90.0}
    for area, items in groups.items():
        match_px = match_of.get(area, 80.0)
        clusters = []
        items.sort(key=lambda r: (str(r.get("timestamp") or ""), float(r.get("obj_x") or 0)))
        for row in items:
            tid = _tid_core(row.get("track_id") or "")
            try:
                x = float(row["obj_x"]) if row.get("obj_x") not in ("", None) else None
            except (TypeError, ValueError):
                x = None
            hit = None
            if tid:
                for cluster in clusters:
                    if cluster.get("tid") and cluster["tid"] == tid:
                        hit = cluster
                        break
            if hit is None and x is not None:
                best = match_px
                for cluster in clusters:
                    if cluster.get("x") is None:
                        continue
                    d = abs(cluster["x"] - x)
                    if d < best:
                        best = d
                        hit = cluster
            if hit is None:
                hit = {"tid": tid, "x": x, "t0": row.get("timestamp") or ""}
                clusters.append(hit)
            else:
                if tid and not hit.get("tid"):
                    hit["tid"] = tid
                if x is not None:
                    hit["x"] = x if hit.get("x") is None else (0.7 * hit["x"] + 0.3 * x)
            row["_cluster"] = hit
        clusters.sort(key=lambda c: c.get("t0") or "")
        names = {id(c): f"작업자 {_worker_letter(i)}" for i, c in enumerate(clusters)}
        for row in items:
            cluster = row.pop("_cluster", None)
            row["worker"] = names.get(id(cluster), "") if cluster is not None else ""


def load_df(force=False):
    """한 번 가져온 로그는 재사용. 탭 바꿀 때 API를 다시 치지 않음."""
    global _DF_CACHE, _DF_READY
    with _DF_LOCK:
        if not force and _DF_CACHE is not None:
            _DF_READY = True
            return _DF_CACHE.copy()
        write_beep()
        events = list(load_events())
        with jsonl_snapshot([detections_path("dwell")]):
            rows = [event_to_row(ev) for ev in events]
            rows = [r for r in rows if r]
            rows.extend(a_zone_rows())
            rows.extend(b_zone_collision_rows())
            rows.extend(d_zone_dwell_rows())
            rows.extend(c_zone_access_rows())
            rows.extend(ppe_scene_rows())
            rows.extend(d_zone_ppe_rows())
        assign_workers(rows)
        if not rows:
            _DF_CACHE = pd.DataFrame(columns=ROW_COLS)
        else:
            _DF_CACHE = pd.DataFrame(rows).sort_values(["timestamp", "worker", "event_id"])
        _DF_READY = True
        return _DF_CACHE.copy()


def part_of(d, sid):
    return d[d["scenario"] == sid].sort_values(["timestamp", "event_id"], ascending=False)


def part_area(d, area_id, sids=None):
    if d is None or len(d) == 0:
        return d
    view = d[d["area"] == area_id] if "area" in d.columns else d.iloc[0:0]
    if sids:
        view = view[view["scenario"].isin(sids)]
    return view.sort_values(["timestamp", "event_id"], ascending=False)


def part_site(d, site_id, sids=None):
    """창고(사이트) 단위 이벤트."""
    if d is None or len(d) == 0:
        return d
    from .config import cameras_of
    ids = {c["id"] for c in cameras_of(site_id)}
    view = d[d["area"].isin(ids)] if "area" in d.columns else d.iloc[0:0]
    if sids:
        view = view[view["scenario"].isin(sids)]
    return view.sort_values(["timestamp", "event_id"], ascending=False)


def live_part(d, area_id, sids, elapsed, site_id=None):
    """탭을 연 뒤 elapsed초까지 나온 로그만. 영상 시작=09:00:00."""
    if site_id:
        part = part_site(d, site_id, sids)
    else:
        part = part_area(d, area_id, sids)
    if part is None or len(part) == 0:
        return part
    start = pd.Timestamp(clock_start())
    ts = pd.to_datetime(part["timestamp"], errors="coerce")
    sec = (ts - start).dt.total_seconds().fillna(0)
    return part[sec <= float(elapsed)]
