# 역할: 기능별 배너·박스·ROI를 영상에 그려 시연용 demo.mp4를 만든다.
"""기능별 배너·박스·ROI를 영상에 그려 시연용 demo.mp4를 만든다."""

import cv2
import numpy as np
from src.feature_status import feature_status
from src.observation_display import display_label, event_display, LABELS

COLORS = {
    "SAFE": (0, 180, 0),
    "WARNING": (0, 140, 255),
    "CRITICAL": (0, 0, 255),
    None: (150, 150, 150),
}


def roi_overlay(
    frame,
    polygon,
    safe_polygons,
    severity,
    active=True,
    alpha_safe=0.15,
    alpha_alert=0.2,
    unknown_color=None,
    alpha_unknown=0.2,
    draw_outer_boundary=True,
):
    mask = np.zeros(frame.shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.asarray(polygon, np.int32)], 255)
    for p in safe_polygons:
        cv2.fillPoly(mask, [np.asarray(p, np.int32)], 0)
    if not active:
        severity = None
    color = (
        tuple(unknown_color)
        if severity is None and unknown_color is not None
        else COLORS[severity]
    )
    layer = frame.copy()
    layer[mask > 0] = color
    alpha = (
        alpha_unknown
        if severity is None and unknown_color is not None
        else alpha_alert
        if severity in {"WARNING", "CRITICAL"}
        else alpha_safe
    )
    frame[:] = cv2.addWeighted(layer, alpha, frame, 1 - alpha, 0)
    # Excluded storage/walking regions are not the monitored lane or a safety verdict.
    if draw_outer_boundary:
        cv2.polylines(frame, [np.asarray(polygon, np.int32)], True, color, 2)
    for p in safe_polygons:
        cv2.polylines(frame, [np.asarray(p, np.int32)], True, COLORS[None], 1)
    return frame


def render(
    frame,
    groups,
    zone=None,
    detections=None,
    proximity_warning_ratio=1.6,
    driver_overlap_threshold=0.8,
    include_other_safe_people=False,
    vehicle_occupancy=None,
):
    compact_people = bool(
        zone and getattr(zone[0], "config", {}).get("compact_person_display")
    )
    if detections is not None and "proximity" in groups:
        groups = {
            **groups,
            "proximity": exclude_driver_overlap_pairs(
                groups["proximity"], driver_overlap_threshold
            ),
        }
    if zone:
        pipeline, row = zone
        cfg = getattr(pipeline, "config", {})
        roi_overlay(
            frame,
            pipeline.polygon,
            getattr(pipeline, "safe_polygons", []),
            feature_status(row["events"])["severity"],
            row["roi_active"],
            cfg.get("roi_alpha_safe", 0.15),
            cfg.get("roi_alpha_alert", 0.2),
            cfg.get("roi_unknown_color"),
            cfg.get("roi_alpha_unknown", 0.2),
            cfg.get("roi_draw_outer_boundary", True),
        )
        if cfg.get("compact_risk_display"):
            movement = feature_status(
                groups.get("zone_dwell", []) + groups.get("proximity", [])
            )
            groups = {k: v for k, v in groups.items() if k != "zone_access"}
            if cfg.get("proximity_alert_lines_only"):
                display_groups = {
                    **groups,
                    "proximity": [
                        e
                        for e in groups.get("proximity", [])
                        if e.get("severity") in {"WARNING", "CRITICAL"}
                        and e.get("observation_status") == "confirmed"
                    ],
                }
            else:
                display_groups = groups
        else:
            display_groups = groups
            movement = None
    else:
        display_groups = groups
        movement = None
    if detections is not None:
        if compact_people:
            from .person_display_cleanup import draw_compact_people

            draw_review_objects(
                frame,
                [d for d in detections if d["class"] != "person"],
                {},
                proximity_warning_ratio,
                driver_overlap_threshold,
                include_other_safe_people,
            )
            draw_compact_people(frame, detections, groups)
        else:
            draw_review_objects(
                frame,
                detections,
                display_groups,
                proximity_warning_ratio,
                driver_overlap_threshold,
                include_other_safe_people,
            )
        draw_vehicle_pair_connections(frame, groups.get("forklift_proximity", []))
    if vehicle_occupancy:
        for state in vehicle_occupancy.values():
            x, y, _, _ = map(int, state["bbox_xyxy"])
            known = state["status"] == "occupied_observed"
            cv2.putText(
                frame,
                "RIDER OBSERVED" if known else "RIDER UNKNOWN",
                (x, max(135, y + 17)),
                0,
                0.4,
                (0, 200, 120) if known else (160, 160, 160),
                1,
            )
    for feature, events in groups.items():
        if compact_people and feature in {"zone_access", "zone_dwell", "ppe"}:
            continue
        if detections is not None and feature not in {"zone_access", "zone_dwell"}:
            continue
        for e in events:
            if feature == "zone_access" and any(
                q.get("track_id") == e.get("track_id")
                for q in groups.get("zone_dwell", [])
            ):
                continue
            color = COLORS[
                e["severity"] if e.get("observation_status") == "confirmed" else None
            ]
            box = e.get("person_bbox_xyxy", e.get("head_bbox_xyxy"))
            if feature == "ppe" and e["severity"] == "WARNING":
                bare = [
                    h
                    for h in e.get("head_candidates", [])
                    if h["class"] == "no_helmet_head"
                ]
                if bare:
                    box = max(bare, key=lambda h: h["confidence"])["bbox_xyxy"]
            boxes = [box] if box else e.get("forklift_bboxes_xyxy", [])
            if e.get("forklift_bbox_xyxy"):
                boxes += [e["forklift_bbox_xyxy"]]
            for b in boxes:
                a, y, c, d = map(int, b)
                cv2.rectangle(frame, (a, y), (c, d), color, 2)
                label = e["severity"] or "UNKNOWN"
                if feature in {"zone_access", "zone_dwell"}:
                    label = "LANE " + label
                    if (
                        e.get("position_observation_status") == "confirmed"
                        and e.get("lane_membership") == "inside"
                        and e.get("severity") is None
                    ):
                        label = "LANE IN / RISK UNKNOWN"
                if feature == "ppe":
                    label = (
                        "HELMET"
                        if e["ppe_state"] == "helmet_detected"
                        and e["severity"] == "SAFE"
                        else "NO HELMET? REVIEW"
                        if e["severity"] == "WARNING"
                        else "PPE UNKNOWN"
                    )
                if (
                    feature == "ppe"
                    and e.get("vehicle_overlap_review_required")
                    and e["severity"] == "WARNING"
                ):
                    label = "PPE REVIEW: VEHICLE OVERLAP"
                if feature == "ppe" and e.get("hood_evidence"):
                    label = (
                        "PPE REVIEW: HOOD"
                        if e["severity"] == "WARNING"
                        else "PPE UNKNOWN: HOOD"
                    )
                if "observed_dwell_seconds" in e:
                    elapsed = (
                        e.get(
                            "observed_vehicle_co_presence_seconds",
                            e["observed_dwell_seconds"],
                        )
                        if e.get("vehicle_lane_state") == "observed_in_lane"
                        and e.get("inside")
                        else e["observed_dwell_seconds"]
                    )
                    label += f" {elapsed:.1f}s"
                label_y = (
                    y + 14
                    if feature == "ppe"
                    else max(105, y - 20)
                    if feature in {"zone_access", "zone_dwell"}
                    else max(105, y - 5)
                )
                cv2.putText(frame, label, (a, label_y), 0, 0.48, color, 1)
    y = 22
    if movement is not None:
        cv2.rectangle(
            frame, (5, 5), (min(frame.shape[1] - 5, 660), 27), (20, 20, 20), -1
        )
        cv2.putText(
            frame,
            "MOVEMENT RISK: " + movement["display_state"],
            (12, y),
            0,
            0.55,
            COLORS[movement["severity"]],
            2,
        )
        y += 27
    for feature, events in groups.items():
        status = feature_status(events)
        color = COLORS[status["severity"]]
        label = f"{feature.upper()}: {display_label(events)}  WAIT={status['assessment_counts']['pending']} CHECK={status['assessment_counts']['unassessable']} LOST={status['assessment_counts']['observation_lost']}"
        cv2.rectangle(
            frame, (5, y - 17), (min(frame.shape[1] - 5, 660), y + 5), (20, 20, 20), -1
        )
        cv2.putText(frame, label, (12, y), 0, 0.55, color, 2)
        y += 27
    return frame


def select_proximity_display_events(
    events,
    warning_ratio=1.6,
    driver_overlap_threshold=0.8,
    include_other_safe_people=False,
):
    """Select alerts and near ambiguity before distant safe fallback.

    Box overlap alone does not establish the operator role; nearby ambiguous
    pairs remain visible. Safe pairs are only a per-person fallback without alerts.
    """
    pairs = [
        e
        for e in events
        if e.get("person_anchor_xy")
        and e.get("nearest_vehicle_point_xy")
        and e.get("normalized_image_gap") is not None
        and e.get("distance_display_enabled", True)
    ]
    pairs = exclude_driver_overlap_pairs(pairs, driver_overlap_threshold)
    alerts = [
        e
        for e in pairs
        if e.get("observation_status") == "confirmed"
        and e.get("severity") in {"WARNING", "CRITICAL"}
    ]
    uncertain = [
        e
        for e in pairs
        if e.get("observation_status") != "confirmed"
        and e["normalized_image_gap"] <= warning_ratio
    ]
    if alerts or uncertain:
        selected = alerts + uncertain
        if include_other_safe_people:
            covered = {e.get("person_track_id") for e in selected}
            safe = [
                e
                for e in pairs
                if e.get("observation_status") == "confirmed"
                and e.get("severity") == "SAFE"
                and e.get("person_track_id") not in covered
            ]
            for person_id in dict.fromkeys(e.get("person_track_id") for e in safe):
                selected.append(
                    min(
                        (e for e in safe if e.get("person_track_id") == person_id),
                        key=lambda e: e["normalized_image_gap"],
                    )
                )
        return selected
    safe = [
        e
        for e in pairs
        if e.get("observation_status") == "confirmed" and e.get("severity") == "SAFE"
    ]
    selected = []
    for person_id in dict.fromkeys(e.get("person_track_id") for e in safe):
        per_person = [e for e in safe if e.get("person_track_id") == person_id]
        if per_person:
            selected.append(min(per_person, key=lambda e: e["normalized_image_gap"]))
    return selected


def _person_vehicle_overlap(event):
    person = event.get("person_bbox_xyxy")
    vehicle = event.get("forklift_bbox_xyxy")
    if not person or not vehicle:
        return 0.0
    x1 = max(person[0], vehicle[0])
    y1 = max(person[1], vehicle[1])
    x2 = min(person[2], vehicle[2])
    y2 = min(person[3], vehicle[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area = max(1e-9, (person[2] - person[0]) * (person[3] - person[1]))
    return intersection / area


def exclude_driver_overlap_pairs(events, threshold=0.8):
    """Only explicit operator evidence can remove a pair; box overlap is ambiguous.

    Preserve nearby UNKNOWN so a distant SAFE pair cannot mask possible danger.
    """
    return [event for event in events if not event.get("operator_confirmed", False)]


def _box_iou(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    return inter / max(1e-9, area_a + area_b - inter)


def select_ppe_review_candidates(events, iou_threshold=0.5):
    """Deduplicate repeated model/tile proposals while preserving class conflicts."""
    selected = []
    for event in events:
        candidates = sorted(
            event.get("head_candidates", []),
            key=lambda h: h.get("confidence", 0),
            reverse=True,
        )
        kept = []
        for candidate in candidates:
            if candidate.get("class") not in {"helmeted_head", "no_helmet_head"}:
                continue
            if any(
                candidate["class"] == prior["class"]
                and _box_iou(candidate["bbox_xyxy"], prior["bbox_xyxy"])
                >= iou_threshold
                for prior in kept
            ):
                continue
            kept.append(candidate)
        selected.extend((event, candidate) for candidate in kept)
    return selected


def draw_review_objects(
    frame,
    detections,
    groups,
    warning_ratio=1.6,
    driver_overlap_threshold=0.8,
    include_other_safe_people=False,
):
    """Draw each observed object once; unassociated head proposals stay in diagnostics."""
    for d in detections:
        if d["confidence"] < 0.1:
            continue
        a, y, c, b = map(int, d["bbox_xyxy"])
        low_person = d["class"] == "person" and d["confidence"] < 0.25
        color = (
            (0, 165, 255)
            if low_person
            else (255, 170, 0)
            if d["class"] == "person"
            else (0, 210, 255)
        )
        cv2.rectangle(frame, (a, y), (c, b), color, 2)
        label = (
            f"LOW PERSON {d['confidence']:.2f}"
            if low_person
            else f"{d['class'].upper()} {d['confidence']:.2f}"
        )
        cv2.putText(frame, label, (a, max(105, y - 5)), 0, 0.45, color, 1)
    for e in groups.get("ppe", []):
        candidates = e.get("head_candidates", [])
        if not e.get("person_bbox_xyxy"):
            continue
        x, y, _, _ = map(int, e["person_bbox_xyxy"])
        status = None
        if e.get("severity") == "SAFE" and e.get("observation_status") == "confirmed":
            status = "PPE OK"
            status_color = COLORS["SAFE"]
        elif e.get("severity") == "WARNING" and not candidates:
            status = "PPE REVIEW"
            status_color = COLORS["WARNING"]
        elif e.get("ppe_state") == "conflicting_evidence" and not candidates:
            status = "PPE CONFLICT"
            status_color = COLORS["WARNING"]
        elif not candidates:
            status = "PPE " + LABELS[event_display(e)["assessment_state"]]
            status_color = COLORS[None]
        if status:
            cv2.putText(
                frame,
                status,
                (x + 2, min(frame.shape[0] - 8, y + 18)),
                0,
                0.38,
                status_color,
                1,
            )
    for e, h in select_ppe_review_candidates(groups.get("ppe", [])):
        a, y, c, b = map(int, h["bbox_xyxy"])
        helmet = h["class"] == "helmeted_head"
        confirmed = (
            e.get("observation_status") == "confirmed"
            and e.get("severity") == "SAFE"
            and helmet
        )
        color = (
            COLORS["SAFE"] if confirmed else (255, 180, 0) if helmet else (0, 165, 255)
        )
        label = (
            "HELMET"
            if confirmed
            else "HELMET CANDIDATE"
            if helmet
            else "NO HELMET DETECTED"
            if e.get("severity") == "WARNING"
            and e.get("observation_status") == "confirmed"
            and e.get("classification_status") == "observed_candidate"
            else "NO HELMET CANDIDATE"
        ) + f" {h['confidence']:.2f}"
        cv2.rectangle(frame, (a, y), (c, b), color, 2)
        cv2.putText(frame, label, (a, max(120, y - 5)), 0, 0.4, color, 1)
    display_events = select_proximity_display_events(
        groups.get("proximity", []),
        warning_ratio,
        driver_overlap_threshold,
        include_other_safe_people,
    )
    legend_y = frame.shape[0] - 100
    for e in display_events:
        confirmed = e.get("observation_status") == "confirmed" and e.get(
            "severity"
        ) in {"SAFE", "WARNING", "CRITICAL"}
        state = e["severity"] if confirmed else "UNKNOWN / CHECK"
        color = COLORS[state if confirmed else "WARNING"]
        a = tuple(map(int, e["person_anchor_xy"]))
        b = tuple(map(int, e["nearest_vehicle_point_xy"]))
        cv2.line(frame, a, b, color, 3)
        cv2.circle(frame, a, 5, color, -1)
        cv2.circle(frame, b, 5, color, -1)
        if len(display_events) <= 3:
            mark = (
                (
                    "CRIT"
                    if e["severity"] == "CRITICAL"
                    else "WARN"
                    if e["severity"] == "WARNING"
                    else "SAFE"
                )
                if confirmed
                else "CHECK"
            )
            person = e.get("person_track_id", "?")
            vehicle = e.get("forklift_track_id", "?")
            label = (
                f"P{person} -> F{vehicle}  {mark}  gap {e['normalized_image_gap']:.2f}"
            )
            y = legend_y + 22 * display_events.index(e)
            cv2.rectangle(
                frame,
                (7, y - 15),
                (min(frame.shape[1] - 7, 410), y + 5),
                (20, 20, 20),
                -1,
            )
            cv2.putText(frame, label, (12, y), 0, 0.45, color, 1)
    if len(display_events) > 3:
        cv2.rectangle(
            frame,
            (7, legend_y - 15),
            (min(frame.shape[1] - 7, 410), legend_y + 5),
            (20, 20, 20),
            -1,
        )
        cv2.putText(
            frame,
            f"{len(display_events)} person-forklift pairs shown; details in event log",
            (12, legend_y),
            0,
            0.43,
            (0, 165, 255),
            1,
        )


def draw_vehicle_pair_connections(frame, events):
    """Draw the same ground-band rectangle gap used by ForkliftProximity."""

    def axis(a, b, c, d):
        if b < c:
            return b, c
        if d < a:
            return a, d
        shared = (max(a, c) + min(b, d)) / 2
        return shared, shared

    for e in events:
        boxes = e.get("forklift_bboxes_xyxy")
        if not boxes or len(boxes) != 2:
            continue
        p, q = e.get(
            "distance_bboxes_xyxy",
            [[v[0], v[3] - 0.15 * (v[3] - v[1]), v[2], v[3]] for v in boxes],
        )
        x, y = axis(p[0], p[2], q[0], q[2])
        u, v = axis(p[1], p[3], q[1], q[3])
        confirmed = e.get("observation_status") == "confirmed"
        state = e.get("severity") if confirmed else None
        color = COLORS[state] if state else (0, 165, 255)
        a, b = (int(x), int(u)), (int(y), int(v))
        cv2.line(frame, a, b, color, 3)
        cv2.circle(frame, a, 5, color, -1)
        cv2.circle(frame, b, 5, color, -1)
        label = f"FORKLIFT PAIR: {state or 'UNKNOWN / CHECK'}  gap {e.get('normalized_image_gap', 0):.2f}"
        cv2.putText(
            frame,
            label,
            (max(5, min(a[0], b[0])), max(85, min(a[1], b[1]) - 12)),
            0,
            0.45,
            color,
            1,
        )
