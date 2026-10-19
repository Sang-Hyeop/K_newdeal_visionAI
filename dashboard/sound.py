# 알람 wav · 종(벨) 알림함 페이로드
import base64
import html
import json
import math
import os
import struct
import wave

from .alert_ops import process_alerts, reset_alert_ops
from .config import ALARM_PATH, LOCAL, WARN_PATH

_BEEP_HTML = {}
_WAV_READY = False
_PENDING_TOASTS = []
_TOAST_SEQ = 0


def reset_notify_state():
    """로그인·새로고침 시 알림 이력 초기화."""
    global _PENDING_TOASTS
    _PENDING_TOASTS = []
    reset_alert_ops()


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
    body = _sound_html(kind) + _toast_payload_html(toasts)
    if not body:
        return ""
    return f"<div class='sisun-alert-bundle' data-kind='{kind or ''}'>{body}</div>"


def notify(d):
    """운영 경보 계층으로 소리·종 목록 갱신.

    - 주의/위험만 대상(미확인·관측 소실 제외 → 안전/종료로 취급하지 않음)
    - 같은 event_id 재조회·같은 에피소드 동일 단계는 소리/새 카드 없음
    - 주의→위험은 upgrade로 다시 알림
    """
    global _PENDING_TOASTS
    kind, ops = process_alerts(d)
    if not ops:
        return None
    # update만 있어도 목록 시각·건수는 갱신. 소리는 new/upgrade일 때만.
    _PENDING_TOASTS.extend(ops)
    if kind:
        return kind
    # 갱신만 있을 때는 소리 없이 페이로드만 (beep_html("") 가 페이로드를 붙여야 함)
    return ""

