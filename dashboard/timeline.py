"""Shared display timestamp parsing and browser playhead input collection."""
import json
import pandas as pd
from .config import clock_start


def event_timestamps(frame):
    return pd.to_datetime(frame["timestamp"], format="ISO8601", errors="coerce")


def event_seconds(frame):
    # Invalid time stays NaN and must never turn into an immediate event.
    return (event_timestamps(frame) - pd.Timestamp(clock_start())).dt.total_seconds()


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
