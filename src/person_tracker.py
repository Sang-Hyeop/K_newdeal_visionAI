# 역할: ByteTrack 기반 사람/지게차 추적. 끊김·장면 전환을 반영한 track_id를 유지한다.
"""ByteTrack 기반 사람/지게차 추적. 끊김·장면 전환을 반영한 track_id를 유지한다."""

from types import SimpleNamespace
import math
import itertools
import numpy as np
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker, STrack


class PersonTracker:
    def __init__(
        self,
        processed_fps,
        max_gap_seconds=1.0,
        target_class="person",
        namespace="",
        expose_current_candidates=False,
        fuse_score=True,
        high_threshold=0.25,
    ):
        if processed_fps <= 0 or max_gap_seconds <= 0:
            raise ValueError("Positive FPS and gap required")
        if not 0.1 < high_threshold <= 1:
            raise ValueError("Tracker threshold must exceed low threshold")
        self.gap = max_gap_seconds
        self.target_class = target_class
        self.namespace = namespace
        self.expose_current_candidates = expose_current_candidates
        self._counter = itertools.count(1)
        self.backend = BYTETracker(
            SimpleNamespace(
                track_high_thresh=high_threshold,
                track_low_thresh=0.1,
                new_track_thresh=high_threshold,
                track_buffer=max(1, math.ceil(processed_fps * max_gap_seconds)),
                match_thresh=0.8,
                fuse_score=fuse_score,
            )
        )
        # Independent counters prevent one class's reset reusing another class's ID.
        self.backend.track_class = type(
            "LocalSTrack",
            (STrack,),
            {"next_id": staticmethod(lambda: next(self._counter))},
        )
        self.scene = 0
        self.last_timestamp = None
        self.last_seen = {}

    def reset(self):
        self.backend.reset()
        self._counter = itertools.count(1)
        self.scene += 1
        self.last_seen.clear()

    def update(self, timestamp, detections, shape, scene_cut=False):
        if (
            not math.isfinite(timestamp)
            or timestamp < 0
            or (self.last_timestamp is not None and timestamp <= self.last_timestamp)
        ):
            raise ValueError("Source timestamps must strictly increase")
        if scene_cut or (
            self.last_timestamp is not None
            and timestamp - self.last_timestamp > self.gap
        ):
            self.reset()
        self.last_timestamp = timestamp
        rows = []
        for detection in detections:
            if detection["class"] != self.target_class:
                continue
            box = detection["bbox_xyxy"]
            score = detection["confidence"]
            if (
                len(box) != 4
                or not all(math.isfinite(v) for v in box)
                or not 0 <= score <= 1
            ):
                raise ValueError("Invalid detection")
            if box[2] <= box[0] or box[3] <= box[1]:
                raise ValueError("Invalid detection dimensions")
            rows.append([*box, score, 0])
        boxes = Boxes(np.asarray(rows, dtype=np.float32).reshape(-1, 6), shape)
        tracks = list(self.backend.update(boxes))
        candidate_ids = set()
        if self.expose_current_candidates:
            known = {int(t[4]) for t in tracks}
            for current in self.backend.tracked_stracks:
                if (
                    not current.is_activated
                    and current.frame_id == self.backend.frame_id
                    and current.track_id not in known
                ):
                    tracks.append(current.result)
                    candidate_ids.add(current.track_id)
        observed = []
        for track in tracks:
            identity = f"{self.namespace}{self.scene}:{int(track[4])}"
            self.last_seen[identity] = timestamp
            observed.append(
                {
                    "track_id": identity,
                    "bbox_xyxy": list(map(float, track[:4])),
                    "detected_bbox_xyxy": rows[int(track[-1])][:4],
                    "confidence": float(track[5]),
                    "observation_status": "unconfirmed"
                    if int(track[4]) in candidate_ids
                    else "confirmed",
                    "current_detection_candidate": int(track[4]) in candidate_ids,
                }
            )
        observed_ids = {row["track_id"] for row in observed}
        missing = []
        for identity, last_seen in list(self.last_seen.items()):
            if identity in observed_ids:
                continue
            missing.append(
                {
                    "track_id": identity,
                    "observation_status": "unconfirmed",
                    "ppe_state": "unknown",
                    "gap_seconds": timestamp - last_seen,
                }
            )
            if timestamp - last_seen > self.gap:
                del self.last_seen[identity]
        return observed, missing
