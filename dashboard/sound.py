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

_WAV_READY = False
_PENDING_TOASTS = []
_TOAST_SEQ = 0
_SOUND_SEQ = 0
_HOT_B64 = None


def reset_notify_state():
    """로그인·새로고침 시 알림 이력 초기화."""
    global _PENDING_TOASTS
    _PENDING_TOASTS = []
    reset_alert_ops()


def write_tone(path, pattern, vol=14000):
    os.makedirs(LOCAL, exist_ok=True)
    rate = 22050
    chunks = []
    for freq, sec in pattern:
        n = int(rate * sec)
        if n <= 0:
            continue
        if freq < 1:
            chunks.append(b"\x00\x00" * n)
            continue
        step = 2 * math.pi * freq / rate
        # pack 일괄 — 샘플 루프마다 struct.pack 호출 제거
        samples = [int(vol * math.sin(step * i)) for i in range(n)]
        chunks.append(struct.pack(f"<{n}h", *samples))
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(chunks))


def write_beep():
    """알람 wav 한 번만 생성."""
    global _WAV_READY, _HOT_B64
    if _WAV_READY and os.path.isfile(ALARM_PATH) and os.path.isfile(WARN_PATH):
        return
    write_tone(ALARM_PATH, [(980, 0.06), (0.001, 0.03)] * 10, vol=15000)
    write_tone(WARN_PATH, [(480, 0.22), (0.001, 0.28), (480, 0.22)], vol=4000)
    _WAV_READY = True
    _HOT_B64 = None


def _hot_wav_b64():
    global _HOT_B64
    if _HOT_B64 is not None:
        return _HOT_B64
    if not os.path.isfile(ALARM_PATH):
        return ""
    with open(ALARM_PATH, "rb") as f:
        _HOT_B64 = base64.b64encode(f.read()).decode("ascii")
    return _HOT_B64


def _sound_html(kind):
    """위험음만 생성. autoplay 없음 — JS가 data-sound-id 당 1회 play.

    주의(warn)는 화면·종 목록만 갱신하고 오디오를 넣지 않는다.
    """
    global _SOUND_SEQ
    if kind != "hot":
        return ""
    b64 = _hot_wav_b64()
    if not b64:
        return ""
    _SOUND_SEQ += 1
    sid = _SOUND_SEQ
    # 요청마다 고유 id. DOM 재삽입·폴링 재처리로 다시 울리지 않게 함.
    return (
        f"<audio class='sisun-beep' data-sound-id='{sid}' "
        f"playsinline preload='auto' "
        f"src='data:audio/wav;base64,{b64}'></audio>"
    )


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
    """소리 HTML(위험만) + 대기 중이던 토스트 페이로드."""
    global _PENDING_TOASTS
    toasts = list(_PENDING_TOASTS)
    _PENDING_TOASTS = []
    # 주의 kind는 소리 없이 목록만
    sound_kind = "hot" if kind == "hot" else ""
    body = _sound_html(sound_kind) + _toast_payload_html(toasts)
    if not body:
        return ""
    return (
        f"<div class='sisun-alert-bundle' data-kind='{sound_kind}' "
        f"data-toast-only='{'1' if not sound_kind else '0'}'>{body}</div>"
    )


def notify(d):
    """운영 경보 계층으로 소리·종 목록 갱신.

    - 주의/위험만 목록 대상(미확인·관측 소실 제외)
    - 소리는 위험 new/upgrade만 (한 배치에 여러 위험이어도 kind는 hot 한 번)
    - 주의·동일 단계 갱신은 목록만
    """
    global _PENDING_TOASTS
    kind, ops = process_alerts(d)
    if not ops:
        return None
    _PENDING_TOASTS.extend(ops)
    if kind == "hot":
        return "hot"
    # 주의만·갱신만: 목록 페이로드는 보내되 소리 없음
    return ""
