# 알람 wav 만들기·새 사건만 소리
import base64
import math
import os
import struct
import wave

import gradio as gr

from .config import ALARM_PATH, LOCAL, WARN_PATH

SEEN_IDS = set()
SOUND_READY = False
_BEEP_HTML = {}
_WAV_READY = False


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


def beep_html(kind):
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
    html = (
        f"<audio autoplay style='display:none'><source src='data:audio/wav;base64,{b64}' type='audio/wav'></audio>"
        f"<script>(function(){{var a=new Audio('data:audio/wav;base64,{b64}');a.play().catch(function(){{}});}})();</script>"
    )
    _BEEP_HTML[kind] = html
    return html


def notify(d):
    """이미 있는 기록은 안 울림. 주의=약한 소리, 위험=빠른 소리. 미확인은 안 울림."""
    global SOUND_READY
    if d is None or len(d) == 0:
        SOUND_READY = True
        return None
    col = "grade" if "grade" in d.columns else "status"
    danger = d[d[col].isin(["주의", "위험"])]
    ids = set(danger["event_id"].astype(str).tolist())
    if not SOUND_READY:
        SEEN_IDS.update(ids)
        SOUND_READY = True
        return None
    new_ids = ids - SEEN_IDS
    SEEN_IDS.update(ids)
    if not new_ids:
        return None
    fresh = danger[danger["event_id"].astype(str).isin(new_ids)]
    gcol = "grade" if "grade" in fresh.columns else "status"
    if int((fresh[gcol] == "위험").sum()):
        gr.Warning("위험 상황이 발생했습니다.")
        return "hot"
    gr.Warning("주의 상황이 발생했습니다.")
    return "warn"
