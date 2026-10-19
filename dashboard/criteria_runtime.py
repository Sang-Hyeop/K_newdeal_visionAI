# 판정 기준 표시용: demo-scenarios·승인 정책·화재 temporal을 시작 시 1회 읽어 캐시한다.
# UI에서 임계값을 재정의하지 않으며, 파일 값만 확인한 경우 출처를 ‘현재 설정 파일 기준’으로 표기한다.
"""설정 파일 → 관제용 기준 문구. 모델·판정 로직은 변경하지 않는다."""

from __future__ import annotations

import json
from pathlib import Path

from .config import DATA_ROOT, REPO_ROOT

_CACHE = None

# 대시보드 카메라 id → demo-scenarios / 시연 설정
_CAM_CONFIG = {
    "A1": "configs/cameras/reverse-proximity.json",
    "A2": "configs/cameras/robot-intrusion.json",
    "A3": "configs/cameras/ppe-warehouse-review.json",
    "A4": "configs/cameras/dwell-demo.json",
    "B1": "configs/cameras/warehouse-summary.json",
    "P1": "configs/review/fire-current.json",
}

# fire-current.json 은 리뷰 로그가 커서 temporal 블록만 추출한다.
_FIRE_REL = "configs/review/fire-current.json"


def _resolve(rel: str):
    for root in (Path(DATA_ROOT), Path(REPO_ROOT)):
        path = root / rel
        if path.is_file():
            return path, str(path.relative_to(root))
    return None, rel


def _read_json(rel: str):
    path, label = _resolve(rel)
    if path is None:
        return None, label
    return json.loads(path.read_text(encoding="utf-8")), label


def _extract_json_object_after(text: str, key: str):
    """텍스트에서 \"key\": { ... } 객체만 raw_decode. 실패 시 None."""
    token = f'"{key}"'
    pos = 0
    decoder = json.JSONDecoder()
    while True:
        idx = text.find(token, pos)
        if idx < 0:
            return None
        colon = text.find(":", idx + len(token))
        if colon < 0:
            return None
        j = colon + 1
        while j < len(text) and text[j].isspace():
            j += 1
        if j >= len(text) or text[j] != "{":
            pos = idx + len(token)
            continue
        try:
            obj, _end = decoder.raw_decode(text, j)
        except json.JSONDecodeError:
            pos = idx + len(token)
            continue
        if isinstance(obj, dict):
            return obj
        pos = idx + len(token)


def _read_fire_slim(rel: str):
    """거대한 fire-current.json 전체 파싱을 피하고 temporal만 담는다."""
    path, label = _resolve(rel)
    if path is None:
        return None, label
    # temporal 은 ~150KB 부근 — 앞부분만 읽어 전체 1.4MB 로드 회피
    with path.open("r", encoding="utf-8") as fh:
        text = fh.read(320_000)
    follow_idx = text.find('"runtime_followup"')
    temporal = None
    if follow_idx >= 0:
        chunk = text[follow_idx : follow_idx + 4000]
        temporal = _extract_json_object_after(chunk, "temporal")
    if temporal is None:
        temporal = _extract_json_object_after(text, "temporal")
    if temporal is None:
        # 잘린 구간 밖이면 전체 로드 (비정상 파일 대비)
        doc = json.loads(path.read_text(encoding="utf-8"))
        temporal = _fire_temporal(doc)
        return {"temporal": temporal} if temporal else doc, label
    return {"temporal": temporal, "runtime_followup": {"temporal": temporal}}, label


def _ppe_policy():
    """실행 진입점 src.ppe_runtime.load_policy 와 동일 파일을 연다."""
    try:
        from src.ppe_runtime import load_policy

        return load_policy(), "src.ppe_runtime.load_policy → 승인 PPE 정책"
    except Exception:
        cfg, _ = _read_json("configs/demo-ppe-model.json")
        if not cfg:
            return None, ""
        rel = (cfg.get("runtime") or {}).get("policy") or cfg.get("policy")
        if not rel:
            return None, ""
        policy, path = _read_json(rel)
        return policy, f"설정 파일 {path}" if policy else ""


def _fire_temporal(doc):
    if not isinstance(doc, dict):
        return None
    follow = doc.get("runtime_followup") or {}
    temporal = follow.get("temporal") if isinstance(follow, dict) else None
    if not isinstance(temporal, dict):
        temporal = doc.get("temporal")
    return temporal if isinstance(temporal, dict) else None


def _load():
    out = {"by_cam": {}, "ppe": None, "ppe_source": "", "files": {}}
    for cam_id, rel in _CAM_CONFIG.items():
        if rel == _FIRE_REL or cam_id == "P1":
            doc, path = _read_fire_slim(rel)
        else:
            doc, path = _read_json(rel)
        out["files"][cam_id] = path
        out["by_cam"][cam_id] = doc
    policy, src = _ppe_policy()
    out["ppe"] = policy
    out["ppe_source"] = src
    return out


def criteria_cache():
    global _CACHE
    if _CACHE is None:
        _CACHE = _load()
    return _CACHE


def criteria_bundle(sid: str, cam_id: str):
    """(출처 문구, 기준 줄 목록). 확인 불가면 출처에 명시."""
    cache = criteria_cache()
    sid = str(sid or "")
    cam_id = str(cam_id or "")
    doc = cache["by_cam"].get(cam_id)
    file_note = cache["files"].get(cam_id) or ""
    source = f"현재 설정 파일 기준 ({file_note})" if file_note else "현재 설정 파일 기준"

    if sid == "collision":
        return _collision_lines(doc, cam_id, source)
    if sid == "zone":
        return _zone_lines(doc, source)
    if sid == "dwell":
        return _dwell_lines(doc, cam_id, source)
    if sid == "ppe":
        return _ppe_lines(cache, source)
    if sid == "fire":
        return _fire_lines(doc, source)
    return "적용 기준 확인 불가", ["적용 기준 확인 불가"]


def _collision_lines(doc, cam_id, source):
    if not isinstance(doc, dict):
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]
    warn = doc.get("warning_ratio")
    crit = doc.get("critical_ratio")
    if warn is None or crit is None:
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]
    lines = [
        "화면상 간격(사람 키로 나눈 상대값) 기준 · 실제 거리(m)는 측정하지 않음",
        f"주의: 상대간격 ≤ {float(warn):.1f} · 위험: 상대간격 ≤ {float(crit):.1f}",
    ]
    if doc.get("exclude_probable_operator") or doc.get("associate_riders"):
        lines.append("확정 탑승자는 보행자 근접 판정에서 제외할 수 있음")
    if cam_id == "B1" and doc.get("proximity_requires_observed_rider"):
        lines.append("창고 통합 영상: 관측된 탑승·통로 조건이 있는 근접 설정")
    return source, lines


def _zone_lines(doc, source):
    if not isinstance(doc, dict):
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]
    lines = [
        "사람 박스 밑면 중앙이 지정 위험구역(폴리곤) 안에 있으면 즉시 위험",
        "구역 경계 바깥 접근대이면 주의 · 체류 시간과 무관한 즉시 판정",
    ]
    margin = doc.get("approach_margin_ratio")
    if margin is not None:
        try:
            lines.append(f"접근대 여유 비율 {float(margin):.3f} (설정 파일 값 · 화면 비율)")
        except (TypeError, ValueError):
            pass
    lines.append("표시 ROI와 판정 ROI는 동일 구역 설정을 사용")
    return source, lines


def _dwell_lines(doc, cam_id, source):
    if not isinstance(doc, dict):
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]
    safe = doc.get("safe_seconds")
    vehicle_crit = doc.get("vehicle_critical_seconds")
    gap = doc.get("max_gap_seconds")
    hold = doc.get("vehicle_missing_hold_seconds")
    if safe is None or vehicle_crit is None:
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]
    try:
        safe_f = float(safe)
        vcrit_f = float(vehicle_crit)
        gap_f = float(gap) if gap is not None else None
        hold_f = float(hold) if hold is not None else None
    except (TypeError, ValueError):
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]

    lines = [
        "사람 박스 밑면 중앙이 감시 통로 안에 있는 동안만 체류시간을 누적",
    ]
    if doc.get("vehicle_conditioned", True):
        if doc.get("co_presence_timing"):
            lines.append(
                f"차량이 같은 통로에서 함께 관측될 때: 즉시 주의 · "
                f"차량–사람 동시 관측 누적 ≥ {vcrit_f:.0f}초이면 위험"
            )
        else:
            lines.append(
                f"차량이 같은 통로에서 관측(또는 소실 후 유지)될 때: 즉시 주의 · "
                f"관측 체류 ≥ {vcrit_f:.0f}초이면 위험"
            )
        lines.append(
            f"차량이 통로에서 관측되지 않으면: 체류 < {safe_f:.0f}초는 안전 밴드 · "
            f"≥ {safe_f:.0f}초는 주의 (이 경로에서는 위험 단계로 올리지 않음)"
        )
    else:
        lines.append(f"체류 단계: 안전 밴드 < {safe_f:.0f}초 · 그 이상은 주의/위험 정책에 따름")
    if hold_f is not None:
        lines.append(f"차량 관측이 끊긴 뒤 약 {hold_f:.0f}초는 최근 차량 관측으로 유지")
    if gap_f is not None:
        lines.append(f"사람 관측이 약 {gap_f:.0f}초 이상 끊기면 해당 체류 누적은 초기화")
    # critical_seconds(5)는 ZoneDwell 밴드용이며 LaneHazard 위험 임계(vehicle_critical)와 다름 → 노출하지 않음
    if cam_id == "B1":
        lines.append("창고 통합 영상용 체류·차량 동시 관측 설정")
    return source, lines


def _ppe_lines(cache, source):
    policy = cache.get("ppe")
    if not isinstance(policy, dict):
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]
    src = cache.get("ppe_source") or source
    if "load_policy" in src:
        label = "현재 실행 정책 기준 (승인 PPE · load_policy)"
    else:
        label = f"현재 설정 파일 기준 ({src})" if src else "현재 설정 파일 기준"
    try:
        win = float(policy["window_seconds"])
        n = int(policy["minimum_valid_observations"])
        frac = float(policy["minimum_class_fraction"])
        hel = float(policy["helmet_evidence_confidence"])
        bare = float(policy["no_helmet_evidence_confidence"])
    except (KeyError, TypeError, ValueError):
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]
    lines = [
        f"머리 후보를 시간창 {win:.1f}초에서 모아 유효 관측 {n}회·다수 비율 {frac:.2f}로 판정",
        f"안전모 증거 신뢰도 {hel:.2f} · 미착용 후보 신뢰도 {bare:.2f}",
        "미검출만으로 미착용을 만들지 않음 · 근거 부족은 판정 대기/판단 불가",
    ]
    return label, lines


def _fire_lines(doc, source):
    temporal = _fire_temporal(doc)
    if not temporal:
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]
    try:
        win = float(temporal["window_seconds"])
        n = int(temporal["minimum_observations"])
        span = float(temporal["minimum_span_seconds"])
    except (KeyError, TypeError, ValueError):
        return "적용 기준 확인 불가", ["적용 기준 확인 불가"]
    lines = [
        "짧은 시간창에서 불꽃 관측이 반복·지속될 때 화재 의심으로 올림",
        f"창 {win:.1f}초 · 유효 관측 {n}회 · 최소 지속 {span:.1f}초",
        "연기만으로는 알리지 않음 · 관측 소실을 현장 안전·진화 완료로 보지 않음",
    ]
    return source, lines
