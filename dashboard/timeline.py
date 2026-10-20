# 역할: 이벤트 시각을 해석하고 브라우저 영상의 재생 위치를 수집합니다.
"""이벤트 시각을 해석하고 브라우저 영상의 재생 위치를 수집합니다."""

import json
import pandas as pd
from .config import clock_start


def event_timestamps(frame):
    return pd.to_datetime(frame["timestamp"], format="ISO8601", errors="coerce")


def event_seconds(frame):
    # Invalid time stays NaN and must never turn into an immediate event.
    stamps = event_timestamps(frame)
    # 영상 시각은 각 기록 날짜의 09:00:00 기준이다. 서버를 밤새 켜 두어도
    # 어제 적재한 캐시를 오늘 날짜와 빼서 음수로 만들지 않는다.
    origins = stamps.dt.normalize() + pd.Timedelta(hours=9)
    return (stamps - origins).dt.total_seconds()


def playback_inputs(wall_id, cameras):
    ids = {cam["id"]: f"sisun-video-{wall_id}-{cam['id']}" for cam in cameras}
    return """(on, previous, ready) => {
      const ids = IDS;
      const positions = {};
      for (const [camera, id] of Object.entries(ids)) {
        const video = document.getElementById(id)?.querySelector('video');
        if (video && video.readyState >= 2 && !video.seeking &&
            Number.isFinite(video.currentTime)) positions[camera] = video.currentTime;
      }
      return [on, positions, ready];
    }""".replace("IDS", json.dumps(ids))
