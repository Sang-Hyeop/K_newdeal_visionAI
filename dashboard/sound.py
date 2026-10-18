# 알람 wav · 종(벨) 알림함 페이로드
import base64
import html
import json
import math
import os
import re
import struct
import wave

from .config import ALARM_PATH, LOCAL, WARN_PATH


def _camera_no(row):
    """CAM03 / 3 / A3 등에서 카메라 번호만 뽑음."""
    for key in ("camera", "cam", "video"):
        raw = str(row.get(key) or "")
        m = re.search(r"(\d+)", raw)
        if m:
            return str(int(m.group(1)))
    return "?"

SEEN_IDS = set()
_BEEP_HTML = {}
_WAV_READY = False
_PENDING_TOASTS = []
_TOAST_SEQ = 0


def reset_notify_state():
    """로그인·새로고침 시 알림 이력 초기화."""
    global _PENDING_TOASTS
    SEEN_IDS.clear()
    _PENDING_TOASTS = []


def write_tone(path, pattern, vol=14000):
    os.makedirs(LOCAL, exist_ok=True)
    rate = 22050
    buf = bytearray()
    for freq, sec in pattern:
        n = int(rate * sec)
        if freq < 1:
            buf.extend(b"\x00\x00" * n)
            continue
        step = 2 * math.pi * freq / rate
        for i in range(n):
            v = int(vol * math.sin(step * i))
            buf.extend(struct.pack("<h", v))
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(buf))


def write_beep():
    """알람 wav 한 번만 생성."""
    global _WAV_READY
    if _WAV_READY and os.path.isfile(ALARM_PATH) and os.path.isfile(WARN_PATH):
        return
    write_tone(ALARM_PATH, [(980, 0.06), (0.001, 0.03)] * 10, vol=15000)
    write_tone(WARN_PATH, [(480, 0.22), (0.001, 0.28), (480, 0.22)], vol=4000)
    _WAV_READY = True
    _BEEP_HTML.clear()


def _sound_html(kind):
    """스크립트 없이 audio 태그만 — Gradio sanitize에도 재생 가능."""
    if not kind:
        return ""
    cached = _BEEP_HTML.get(kind)
    if cached is not None:
        return cached
    path = ALARM_PATH if kind == "hot" else WARN_PATH if kind == "warn" else ""
    if not path or not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    # 매번 다른 id → 같은 kind여도 DOM이 바뀌어 autoplay가 다시 시도됨
    html_out = (
        f"<audio class='sisun-beep' autoplay playsinline "
        f"src='data:audio/wav;base64,{b64}'></audio>"
    )
    _BEEP_HTML[kind] = html_out
    return html_out


def _toast_payload_html(toasts):
    """script 대신 data 속성 — BOOT_JS가 폴링으로 읽어 스택에 푸시."""
    global _TOAST_SEQ
    if not toasts:
        return ""
    _TOAST_SEQ += 1
    payload = html.escape(json.dumps(toasts, ensure_ascii=False), quote=True)
    return (
        f"<div class='sisun-toast-payload' data-seq='{_TOAST_SEQ}' "
        f"data-items=\"{payload}\" hidden></div>"
    )


def beep_html(kind):
    """소리 HTML + 대기 중이던 토스트 페이로드."""
    global _PENDING_TOASTS
    toasts = list(_PENDING_TOASTS)
    _PENDING_TOASTS = []
    # kind가 같아도 토스트 seq가 바뀌도록 토스트를 뒤에 붙임
    body = _sound_html(kind) + _toast_payload_html(toasts)
    if not body:
        return ""
    # Gradio가 동일 문자열이면 DOM 갱신을 건너뛸 수 있어 seq 마커 포함
    return f"<div class='sisun-alert-bundle' data-kind='{kind or ''}'>{body}</div>"


def notify(d):
    """이미 본 event_id는 제외. 주의/위험만 토스트·소리. 미확인 제외.
    라이브로 새로 들어온 건 종(벨) 알림함에 쌓음. 화면 떠다니는 토스트는 쓰지 않음.
    """
    if d is None or len(d) == 0:
        return None
    col = "grade" if "grade" in d.columns else "status"
    danger = d[d[col].isin(["주의", "위험"])]
    if len(danger) == 0:
        return None
    ids = set(danger["event_id"].astype(str).tolist())
    new_ids = ids - SEEN_IDS
    SEEN_IDS.update(ids)
    if not new_ids:
        return None
    fresh = danger[danger["event_id"].astype(str).isin(new_ids)].copy()
    if "timestamp" in fresh.columns:
        fresh = fresh.sort_values(["timestamp", "event_id"], kind="mergesort")
    gcol = "grade" if "grade" in fresh.columns else "status"
    for _, row in fresh.iterrows():
        grade = str(row.get(gcol) or "")
        cam_no = _camera_no(row)
        if grade == "위험":
            _PENDING_TOASTS.append(
                {
                    "level": "hot",
                    "title": "Danger",
                    "text": f"위험 알람 {cam_no}번 카메라 확인 요망",
                }
            )
        else:
            _PENDING_TOASTS.append(
                {
                    "level": "warn",
                    "title": "Warning",
                    "text": f"주의 알람 {cam_no}번 카메라 확인 요망",
                }
            )
    if int((fresh[gcol] == "위험").sum()):
        return "hot"
    return "warn"
