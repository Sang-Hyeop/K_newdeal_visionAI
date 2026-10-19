# 카메라 상세: 판정 기준·관측 근거 표시 (모델/임계값 변경 없음, 표시만)
"""관제용 판정 설명. 이벤트 행 + 설정 파일 캐시를 연결한다.

주의:
- 대시보드 DF에는 evidence 전체가 없고 distance_px·dwell_sec·status·grade·message 중심이다.
- 사건 JSON에 당시 기준 스냅샷이 없으면 현재 설정 파일 기준으로 구분해 표기한다.
- 실제 거리(m)는 제공하지 않는다.
"""

from .config import CAM_BY_ID
from .criteria_runtime import criteria_bundle


# 카메라별 시연 기능 범위 (docs + final-model-lock / demo-feature-show-plan)
CAM_FEATURE_SIDS = {
    "A1": ("collision",),
    "A2": ("zone", "ppe"),
    "A3": ("ppe",),
    "A4": ("dwell",),
    "B1": ("collision", "zone", "ppe", "dwell"),
    "P1": ("fire",),
}

FEATURE_NAME = {
    "collision": "작업자–지게차 근접",
    "zone": "위험구역 침범",
    "ppe": "안전모 착용 상태",
    "dwell": "위험구역 체류",
    "fire": "불꽃 관측",
}


def _esc(text):
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _cell(row, key, default=""):
    if row is None:
        return default
    try:
        value = row[key] if hasattr(row, "index") and key in row.index else row.get(key, default)
    except Exception:
        return default
    if value is None:
        return default
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return default
    except Exception:
        pass
    return value


def _fmt_clock(row):
    ts = str(_cell(row, "timestamp") or "")
    if " " in ts:
        part = ts.split(" ", 1)[1]
        return part[:8] if len(part) >= 8 else part
    return ts[:8] if ts else "기록 없음"


def _level_label(row):
    sid = str(_cell(row, "scenario") or "")
    status = str(_cell(row, "status") or "")
    grade = str(_cell(row, "grade") or "")
    if sid == "fire":
        return status or grade or "기록 없음"
    if sid == "ppe":
        if status in ("착용", "미착용"):
            return f"{status} · 표시 단계 {grade or '—'}"
        return status or grade or "기록 없음"
    return grade or status or "기록 없음"


def _gap_display(row):
    """화면상 간격 표시. 결측·미확인의 0은 관측 0과 구분."""
    gap = _cell(row, "distance_px")
    grade = str(_cell(row, "grade") or "")
    status = str(_cell(row, "status") or "")
    if gap in ("", None):
        return "간격 확인 불가"
    try:
        value = float(gap)
    except (TypeError, ValueError):
        return "간격 확인 불가"
    if value == 0.0 and grade in ("미확인", "") and status in ("미확인", "", "판정 불가"):
        return "간격 확인 불가"
    return f"화면상 간격 {value:.0f}px (상대 판정용 · m 아님)"


def _observation_bits(row, sid):
    """이 기록에서 확인되는 관측값만. 없으면 기록 없음."""
    from .display_text import operator_message_for_row

    bits = []
    when = _fmt_clock(row)
    bits.append(f"기록 시각 {when}" if when != "기록 없음" else "기록 시각: 기록 없음")

    if sid == "collision":
        bits.append(_gap_display(row))
        bits.append("정규화 상대간격: 이 표 행에는 기록 없음")

    stay = _cell(row, "dwell_sec")
    if sid == "dwell":
        if stay not in ("", None):
            try:
                bits.append(f"관측 체류시간 {float(stay):.1f}초 (해당 기록 시점)")
            except (TypeError, ValueError):
                bits.append("관측 체류시간: 기록 없음")
        else:
            bits.append("관측 체류시간: 기록 없음")

    if sid == "ppe":
        st = str(_cell(row, "status") or "")
        if st == "착용":
            bits.append("표시 상태: 안전모 착용")
        elif st == "미착용":
            bits.append("표시 상태: 안전모 미착용 후보(검토)")
        else:
            bits.append(f"표시 상태: {st or '기록 없음'}")
        bits.append("창 관측 횟수·비율: 이 표 행에는 기록 없음")

    if sid == "zone":
        bits.append("진입 기준점: 사람 박스 밑면 중앙 (설정·실행 공통)")
        bits.append("구역 체류시간은 이 기능의 판정 조건이 아님")

    if sid == "fire":
        st = str(_cell(row, "status") or "")
        bits.append(f"상태: {st or '기록 없음'}")
        bits.append("차량–불꽃 위치 관계는 판정하지 않음")

    summary = operator_message_for_row(row)
    if summary and sid not in ("fire",):
        bits.append(f"표시 요약: {summary}")
    elif sid == "fire":
        msg = str(_cell(row, "message") or "").strip()
        if msg:
            bits.append(msg)

    return bits


def _why_lines(row, sid):
    grade = str(_cell(row, "grade") or "")
    status = str(_cell(row, "status") or "")
    if sid == "collision":
        gap = _cell(row, "distance_px")
        has_gap = gap not in ("", None)
        if grade == "위험":
            if has_gap:
                return (
                    "저장된 위험 판정 기록임. "
                    "이 행의 화면상 간격은 관측값으로 표시되며, 상대간격 재계산 검증은 하지 않음"
                )
            return "저장된 위험 판정 기록임. 이 행에서 간격 관측값은 확인되지 않음"
        if grade == "주의":
            if has_gap:
                return (
                    "저장된 주의 판정 기록임. "
                    "이 행의 화면상 간격은 관측값으로 표시되며, 상대간격 재계산 검증은 하지 않음"
                )
            return "저장된 주의 판정 기록임. 이 행에서 간격 관측값은 확인되지 않음"
        return "근접 단계 판정 이유를 이 행에서 확인하기 어려움"
    if sid == "zone":
        if grade == "위험":
            return "저장된 위험 판정 기록임(밑면 중앙이 위험구역 내부로 기록됨)"
        if grade == "주의":
            return "저장된 주의 판정 기록임(위험구역 접근대로 기록됨)"
        return "구역 판정 이유를 이 행에서 확인하기 어려움"
    if sid == "dwell":
        stay = _cell(row, "dwell_sec")
        stay_txt = ""
        if stay not in ("", None):
            try:
                stay_txt = f" · 기록된 관측 체류 {float(stay):.1f}초"
            except (TypeError, ValueError):
                pass
        if grade == "위험":
            return f"저장된 위험 판정 기록임(통로 체류·차량 조건){stay_txt}"
        if grade == "주의":
            return f"저장된 주의 판정 기록임(통로 체류){stay_txt}"
        return "체류 단계 판정 이유를 이 행에서 확인하기 어려움"
    if sid == "ppe":
        if status == "미착용":
            return (
                "저장된 안전모 미착용 후보 기록임(검토 단계). "
                "탐지 신뢰도를 사건 위험도와 같은 수치로 쓰지 않음"
            )
        if status == "착용":
            return "저장된 안전모 착용 기록임"
        return "안전모 상태 판정 이유를 이 행에서 확인하기 어려움"
    if sid == "fire":
        if status == "화재 의심":
            return "저장된 화재 의심 기록임(반복 관측 조건 충족으로 기록됨)"
        if status == "확인 중":
            return "불꽃 후보는 있으나 반복 관측 확인이 끝나지 않은 기록임"
        if status == "관측 소실":
            return "이전에 보이던 불꽃 관측이 끊긴 기록임(안전 복귀·진화 완료 아님)"
        if status == "판정 불가":
            return "불꽃 판정 근거가 부족한 기록임"
        return "불꽃 상태 확인이 필요함(근거 없이 화재 의심으로 대체하지 않음)"
    return "판정 이유를 이 행에서 확인하기 어려움"


def _check_lines(sid, status=""):
    if sid == "collision":
        return "영상에서 작업자와 지게차의 실제 간격·접촉 위험을 확인"
    if sid == "zone":
        return "영상에서 사람이 위험구역 안에 있는지 확인"
    if sid == "dwell":
        return "영상에서 통로 체류가 계속되는지 확인(과거 기록 시간을 현재 체류로 보지 말 것)"
    if sid == "ppe":
        if status == "미착용":
            return "영상에서 안전모 미착용 여부를 직접 확인(후보 표시는 검토용)"
        return "영상에서 안전모 착용 상태를 확인"
    if sid == "fire":
        if status == "관측 소실":
            return "영상에서 불꽃 재출현 여부를 확인(관측 끊김을 현장 안전으로 보지 말 것)"
        if status == "확인 중":
            return "영상에서 불꽃 후보가 반복되는지 확인"
        if status == "화재 의심":
            return "영상에서 실제 화재·불꽃 여부를 확인"
        if status == "판정 불가":
            return "영상에서 불꽃 후보와 판정 가능 여부를 확인"
        return "영상에서 불꽃 상태와 기록을 대조해 확인"
    return "영상에서 실제 상황을 확인"


def _limit_lines(sid, cam_id, criteria_source=""):
    limits = []
    if sid == "collision":
        limits.append("실제 거리(m)는 측정하지 않음 · 화면상 상대값만 사용")
        limits.append("근접 판정을 충돌이 일어난 것으로 단정하지 않음")
    if sid == "zone":
        limits.append("구역 진입과 장시간 체류는 다른 기능임")
        if cam_id == "A2":
            limits.append("시연용 AI 생성 영상이며 독립 CCTV 일반화 평가가 아님")
    if sid == "dwell":
        limits.append("표시된 체류시간은 해당 기록 시점의 관측값이며 현재 실시간 체류가 아닐 수 있음")
        limits.append("차량 조건·관측 끊김에 따라 단계가 달라질 수 있음")
    if sid == "ppe":
        limits.append("상세 표의 착용/미착용은 요약 표시이며, 판정 대기·판단 불가 상태는 이 행에 없을 수 있음")
        limits.append("머리 가림·작은 크기 등은 이 행에 근거가 없어 원인으로 단정하지 않음")
    if sid == "fire":
        limits.append("차량 주변 화재로 단정하지 않음")
        limits.append("화재 확정·자동 진압·신고 기능 없음 · 관측이 끊겨도 현장 안전으로 보지 않음")
    if criteria_source:
        limits.append(f"아래 단계 임계는 사건 당시 스냅샷이 아니라 {criteria_source}")
    else:
        limits.append("아래 단계 임계는 사건 당시 스냅샷이 아니라 현재 설정 파일 기준임")
    return limits


def judgment_sections(row, cam=None):
    """표시용 섹션 dict. 값이 없으면 안내 문구."""
    sid = str(_cell(row, "scenario") or "")
    cam_id = ""
    if cam:
        cam_id = str(cam.get("id") or "")
    if not cam_id:
        cam_id = str(_cell(row, "area") or "")
    cam_meta = cam or CAM_BY_ID.get(cam_id, {})

    allowed = CAM_FEATURE_SIDS.get(cam_id)
    if allowed and sid and sid not in allowed:
        return {
            "feature": FEATURE_NAME.get(sid, sid or "기록 없음"),
            "level": _level_label(row),
            "observation": ["이 카메라 시연 범위 밖 기능의 기록일 수 있음"],
            "criteria": ["적용 기준 확인 불가"],
            "why": "카메라별 기능 범위와 기록이 일치하지 않음",
            "check": "영상과 이벤트 표를 함께 확인",
            "limits": ["기능 범위: " + ", ".join(FEATURE_NAME.get(s, s) for s in allowed)],
            "criteria_source": "적용 기준 확인 불가",
        }

    source, criteria = criteria_bundle(sid, cam_id)
    if not criteria:
        criteria = ["적용 기준 확인 불가"]
        source = "적용 기준 확인 불가"

    return {
        "feature": FEATURE_NAME.get(sid, sid or "기록 없음"),
        "level": _level_label(row),
        "observation": _observation_bits(row, sid),
        "criteria": criteria,
        "why": _why_lines(row, sid),
        "check": _check_lines(sid, str(_cell(row, "status") or "")),
        "limits": _limit_lines(sid, cam_id, source),
        "criteria_source": source,
        "place": (cam_meta or {}).get("zone") or _cell(row, "zone") or "",
    }


def judgment_panel_html(row, cam=None):
    """접이식 본문 HTML (Accordion 안쪽에 넣음)."""
    if row is None:
        return ""
    sec = judgment_sections(row, cam=cam)

    def bullets(items):
        if not items:
            return "<li>기록 없음</li>"
        return "".join(f"<li>{_esc(x)}</li>" for x in items if x)

    return (
        "<div class='sisun-judgment'>"
        f"<div class='sisun-judgment-row'><span>대상 기능</span>"
        f"<b>{_esc(sec['feature'])}</b> · {_esc(sec['level'])}</div>"
        f"<div class='sisun-judgment-row'><span>관측값 · 시점</span>"
        f"<ul>{bullets(sec['observation'])}</ul></div>"
        f"<div class='sisun-judgment-row'><span>판정 기준</span>"
        f"<div class='sisun-judgment-note'>{_esc(sec['criteria_source'])}</div>"
        f"<ul>{bullets(sec['criteria'])}</ul></div>"
        f"<div class='sisun-judgment-row'><span>판정 이유</span>"
        f"<p>{_esc(sec['why'])}</p></div>"
        f"<div class='sisun-judgment-row'><span>확인 사항</span>"
        f"<p>{_esc(sec['check'])}</p></div>"
        f"<div class='sisun-judgment-row'><span>해석 한계</span>"
        f"<ul>{bullets(sec['limits'])}</ul></div>"
        "</div>"
    )
