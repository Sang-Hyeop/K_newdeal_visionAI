# 역할: 내부 감지 값을 운영자가 이해할 한글 표시 문구로 변환합니다.
# 관제 화면용 표시 문구 (원본 이벤트·message 저장값은 바꾸지 않음)
"""구조화 필드를 우선하고, 레거시 CRIT/WARN 등은 제한적으로만 해석한다."""

from __future__ import annotations

import math
import re

import pandas as pd

_GRADE_EN_TO_KO = {
    "CRIT": "위험",
    "CRITICAL": "위험",
    "WARN": "주의",
    "WARNING": "주의",
    "SAFE": "안전",
    "UNKNOWN": "미확인",
    "WORN": "착용",
    "NOT WORN": "미착용",
}

_FIRE_REASON = {
    "화재 의심": "불꽃 의심",
    "확인 중": "불꽃 확인 중",
    "관측 소실": "불꽃 관측 소실",
    "판정 불가": "불꽃 판정 불가",
}

_FIRE_EVIDENCE = {
    "화재 의심": (
        "반복 관측 조건이 충족된 화재 의심 기록",
        "영상에서 실제 화재·불꽃 여부를 확인",
    ),
    "확인 중": (
        "불꽃 후보의 반복 관측을 확인 중",
        "영상에서 불꽃 후보가 반복되는지 확인",
    ),
    "관측 소실": (
        "이전 불꽃 관측이 끊긴 상태(진화·안전을 뜻하지 않음)",
        "영상에서 불꽃 재출현 여부를 확인(관측 끊김을 현장 안전으로 보지 말 것)",
    ),
    "판정 불가": (
        "불꽃 판정 근거 부족",
        "영상에서 불꽃 후보와 판정 가능 여부를 확인",
    ),
}


def _cell(row, key, default=""):
    if row is None:
        return default
    try:
        value = (
            row[key]
            if hasattr(row, "index") and key in row.index
            else row.get(key, default)
        )
    except Exception:
        try:
            value = row.get(key, default)
        except Exception:
            return default
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return value


def fire_reason_label(status: str) -> str:
    status = str(status or "").strip()
    if status in _FIRE_REASON:
        return _FIRE_REASON[status]
    return "불꽃 상태 확인 필요"


def fire_evidence_lines(status: str):
    status = str(status or "").strip()
    if status in _FIRE_EVIDENCE:
        return _FIRE_EVIDENCE[status]
    return (
        "불꽃 상태를 이 기록만으로 단정할 수 없음",
        "영상과 상태 기록을 대조해 확인",
    )


def grade_ko(token: str) -> str:
    raw = str(token or "").strip()
    if raw in ("위험", "주의", "안전", "미확인", "착용", "미착용"):
        return raw
    return _GRADE_EN_TO_KO.get(raw.upper(), raw)


def gap_phrase(row) -> str | None:
    """근접 간격 표시. None이면 해당 문구를 붙이지 않음."""
    gap = _cell(row, "distance_px")
    grade = str(_cell(row, "grade") or "")
    status = str(_cell(row, "status") or "")
    if gap in ("", None):
        return "간격 확인 불가"
    try:
        value = float(gap)
    except (TypeError, ValueError):
        return "간격 확인 불가"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "간격 확인 불가"
    # 미확인 등급의 0은 결측 대체를 의심 → 확인 불가
    if value == 0.0 and (grade in ("미확인", "") or status in ("미확인", "")):
        return "간격 확인 불가"
    return f"화면상 간격 {value:.0f}px"


def _legacy_message(msg: str) -> str | None:
    """알려진 ‘N 사람 CRIT · Npx’ / ‘N WORN’ 형식만 변환. 그 외는 None."""
    text = str(msg or "").strip()
    if not text:
        return None
    m = re.match(
        r"^(\d+)\s*사람\s+(CRIT|CRITICAL|WARN|WARNING|SAFE|UNKNOWN)"
        r"(?:\s*·\s*(\d+(?:\.\d+)?)px)?\s*$",
        text,
        re.I,
    )
    if m:
        num, tag, px = m.group(1), m.group(2), m.group(3)
        bits = [f"사람 {num}", grade_ko(tag)]
        if px is not None:
            try:
                if float(px) == 0.0 and grade_ko(tag) == "미확인":
                    bits.append("간격 확인 불가")
                else:
                    bits.append(f"화면상 간격 {float(px):.0f}px")
            except (TypeError, ValueError):
                bits.append("간격 확인 불가")
        return " · ".join(bits)
    m = re.match(r"^(\d+)\s+(NOT\s+WORN|WORN)\s*$", text, re.I)
    if m:
        return f"사람 {m.group(1)} · {grade_ko(m.group(2))}"
    # 토큰만 치환할 수 있는 짧은 레거시
    if re.search(r"\b(CRIT|WARN|SAFE|UNKNOWN)\b", text):
        out = text
        for en, ko in (
            ("CRITICAL", "위험"),
            ("CRIT", "위험"),
            ("WARNING", "주의"),
            ("WARN", "주의"),
            ("SAFE", "안전"),
            ("UNKNOWN", "미확인"),
        ):
            out = re.sub(rf"\b{en}\b", ko, out)
        out = re.sub(r"(\d+)\s*사람", r"사람 \1", out)
        out = re.sub(r"(\d+(?:\.\d+)?)px", r"화면상 간격 \1px", out, count=1)
        return out
    return None


def operator_message_for_row(row) -> str:
    """표·요약·패널용 한 줄. 구조화 필드 우선."""
    sid = str(_cell(row, "scenario") or "")
    status = str(_cell(row, "status") or "")
    grade = str(_cell(row, "grade") or "")
    msg = str(_cell(row, "message") or "").strip()

    if sid == "fire":
        return msg or fire_evidence_lines(status)[0]

    worker = str(_cell(row, "worker") or "").strip()
    person_no = _cell(row, "person_no")
    subject = worker
    if not subject and person_no not in ("", None, 0, "0"):
        try:
            subject = f"사람 {int(float(person_no))}"
        except (TypeError, ValueError):
            subject = f"사람 {person_no}"

    level = grade_ko(grade) if grade else grade_ko(status)
    if sid == "ppe" and status in ("착용", "미착용"):
        level = status

    bits = []
    if subject:
        bits.append(subject)
    if level and level not in bits:
        bits.append(level)

    if sid == "collision":
        bits.append(gap_phrase(row))
    elif sid == "dwell":
        stay = _cell(row, "dwell_sec")
        if stay not in ("", None):
            try:
                bits.append(f"관측 체류 {float(stay):.0f}초")
            except (TypeError, ValueError):
                pass

    def _safe_ko_message(text: str) -> bool:
        return bool(text) and not re.search(
            r"\b(CRIT|CRITICAL|WARN|WARNING|SAFE|UNKNOWN|WORN)\b", text, re.I
        )

    # PPE 미확인 등은 저장 message가 이미 관제용 한글이면 우선
    if sid == "ppe" and status == "미확인" and _safe_ko_message(msg):
        return msg

    if bits:
        return " · ".join(b for b in bits if b)

    legacy = _legacy_message(msg)
    if legacy:
        return legacy
    return msg
