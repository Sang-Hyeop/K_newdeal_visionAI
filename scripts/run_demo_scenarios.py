# 역할: 1·3·4·5번 영상의 활성 기능만 추론·판정하고 리뷰와 이벤트를 생성합니다.
# 1번, 3번, 4번, 5번 영상 분석
"""1·3·4·5번 영상의 활성 기능만 추론·판정하고 리뷰와 이벤트를 생성합니다."""

from pathlib import Path
import copy
import argparse
import json
import sys
import os
import hashlib
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / "outputs/runtime/yolo"))
import torch
import cv2
import numpy as np
from ultralytics import YOLO
from src.object_recall_ensemble import ObjectRecallEnsemble
from src.ppe_final_detector import FinalPPEDetector
from src.ppe_events import PPEEvents
from src.person_tracker import PersonTracker
from src.tracked_proximity import TrackedProximity
from src.tracked_zone import TrackedZone
from src.scenario_zone import ScenarioZone, mark_uncertain_lane_events
from src.forklift_proximity import ForkliftProximity
from src.ppe_vehicle_guard import apply_ppe_vehicle_guard
from src.scenario_render import exclude_driver_overlap_pairs, render
from src.feature_status import feature_status
from src.detection_review_profile import (
    predict_review_objects,
    select_review_objects,
    build_review_models,
    exclude_confirmed_equipment,
    refine_reused_vehicle_support,
)
from src.event_contract import export_events
from src.ppe_runtime import (
    load_policy,
    runtime_version,
    runtime_config,
    infer_runtime_heads,
    assign_head_observations,
)
from src.scenario_selection import (
    review_video_numbers,
    scenario_directory,
    presentation_groups,
    presentation_detections,
    cache_model_hashes_match,
)


def sha(p):
    # 영상·가중치를 한꺼번에 메모리에 올리지 않고 같은 SHA-256을 계산합니다.
    with Path(p).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ppe-final", action="store_true", default=True)
    p.add_argument("--temporal-riders", action="store_true")
    p.add_argument("--proximity-geometry", choices=["box_boundary", "bottom_center"])
    p.add_argument("--max-seconds", type=float)
    p.add_argument("--object-review-cache", type=Path)
    p.add_argument(
        "--ppe-profile", type=Path, default=ROOT / "configs/demo-ppe-model.json"
    )
    p.add_argument("--videos", type=int, nargs="+", default=None)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sample-fps", type=float, default=5)
    p.add_argument("--append", action="store_true")
    p.add_argument("--reuse-run", type=Path)
    p.add_argument("--reuse-objects", action="store_true")
    p.add_argument("--refine-reused-vehicles", action="store_true")
    a = p.parse_args()
    if a.temporal_riders and a.videos != [5]:
        raise ValueError("Temporal rider review is restricted to video5")
    if a.refine_reused_vehicles and (not a.reuse_objects):
        raise ValueError("Vehicle refinement requires validated object reuse")
    if a.reuse_objects and (not a.reuse_run):
        raise ValueError("Object reuse requires validated source run")
    selection_manifest = json.load(open(ROOT / "configs/demo-scenarios.json"))
    a.videos = review_video_numbers(a.videos, selection_manifest)
    spec_by_number = {s["video_number"]: s for s in selection_manifest["scenarios"]}
    if a.proximity_geometry and a.videos != [5]:
        raise ValueError("Comparison geometry is restricted to video5")
    if a.max_seconds is not None and (
        not math.isfinite(a.max_seconds) or a.max_seconds <= 0
    ):
        raise ValueError("Positive review duration required")
    if a.reuse_run and (not a.reuse_objects):
        raise ValueError("Final PPE cache reuse requires --reuse-objects")
    if (
        len(set(a.videos)) != len(a.videos)
        or any((n not in spec_by_number for n in a.videos))
        or (a.output.exists() and (not a.append))
        or any(
            (
                (a.output / scenario_directory(spec_by_number[n])).exists()
                for n in a.videos
            )
        )
        or (not math.isfinite(a.sample_fps))
        or (a.sample_fps <= 0)
    ):
        raise ValueError("New output, valid videos and positive FPS required")
    torch.set_num_threads(4)
    manifest = json.load(open(ROOT / "configs/demo-scenarios.json"))
    obj = json.load(open(ROOT / "configs/demo-object-model.json"))
    profile = json.load(open(a.ppe_profile))
    policy = load_policy()
    profile = {
        **profile,
        "weights": {
            "objects": profile["weights"]["objects"],
            "ppe_baseline": "models/ppe_final/ppe_helmet_v6_960.pt",
        },
    }
    paths = [
        obj["baseline_weights"],
        obj["supplement_weights"],
        *profile["weights"].values(),
    ]
    hashes = {s: sha(ROOT / s) for s in paths}
    models = None
    ppe = None
    person_model = None
    a.output.mkdir(parents=True, exist_ok=a.append)
    totals = (
        json.load(open(a.output / "manifest.json"))
        if a.append and (a.output / "manifest.json").exists()
        else []
    )
    for n in a.videos:
        spec = spec_by_number[n]
        ppe_enabled = spec.get("ppe_enabled", True)
        source = ROOT / "data/videos" / spec["source_name"]
        assert sha(source) == spec["source_sha256"]
        folder = scenario_directory(spec)
        dest = a.output / folder
        dest.mkdir()
        cap = cv2.VideoCapture(str(source))
        fps = cap.get(5)
        h, w = (int(cap.get(4)), int(cap.get(3)))
        stride = max(1, round(fps / a.sample_fps))
        rate = fps / stride
        cached = {}
        pcfg = (
            json.load(open(ROOT / spec["camera_config"]))
            if spec["camera_config"]
            else None
        )
        if a.proximity_geometry:
            pcfg = {**pcfg, "distance_geometry": a.proximity_geometry}
        if a.temporal_riders:
            pcfg = {
                **pcfg,
                "temporal_riders": True,
                "exclude_riders_from_all_proximity": True,
                "expose_current_person_candidates": True,
                "occupancy_minimum_observations": 1,
            }
        review = (
            json.load(open(ROOT / pcfg["object_review_profile"]))
            if pcfg.get("object_review_profile")
            else None
        )
        if review and review.get("vehicle_weights"):
            hashes[review["vehicle_weights"]] = sha(ROOT / review["vehicle_weights"])
        if review and review.get("vehicle_support_weights"):
            hashes[review["vehicle_support_weights"]] = sha(
                ROOT / review["vehicle_support_weights"]
            )
        review_rows = None
        review_person_model = None
        review_models = None
        reuse_vehicle_model = None
        if a.object_review_cache:
            if not review:
                raise ValueError(
                    "Object review cache requires a reviewed camera profile"
                )
            metadata = json.load(open(a.object_review_cache / "metadata.json"))
            assert (
                metadata["source_sha256"] == spec["source_sha256"]
                and all((hashes[k] == v for k, v in metadata["model_hashes"].items()))
                and (abs(metadata["processed_fps"] - rate) < 1e-09)
            )
            review_rows = {
                r["frame_index"]: r
                for r in map(
                    json.loads,
                    (a.object_review_cache / "highres.jsonl").read_text().splitlines(),
                )
            }
        if a.reuse_run:
            cache = a.reuse_run / folder
            cs = json.load(open(cache / "summary.json"))
            assert (
                cs["source_sha256"] == spec["source_sha256"]
                and cache_model_hashes_match(
                    cs["model_hashes"],
                    hashes,
                    ppe_enabled,
                    profile["weights"]["ppe_baseline"],
                )
                and (abs(cs["processed_fps"] - rate) < 1e-09)
            )
            cached = {
                r["frame_index"]: {
                    "events": r["feature_events"].get("ppe", []),
                    "tracks": r.get("ppe_tracks", []),
                    "head_detections": r.get("head_detections", []),
                    "object_detections": r.get(
                        "movement_input_detections", r["object_detections"]
                    ),
                    "ppe_input_detections": r.get("ppe_input_detections"),
                    "ppe_runtime_version": r.get("ppe_runtime_version"),
                    "ppe_blocked_helmet_candidates": r.get(
                        "ppe_blocked_helmet_candidates", []
                    ),
                    "rejected_object_proposals": r.get("rejected_object_proposals", []),
                }
                for r in map(
                    json.loads, (cache / "detections.jsonl").read_text().splitlines()
                )
            }
            if a.reuse_objects:
                ignored = (
                    {"vehicle_support_person_context_scale"}
                    if a.refine_reused_vehicles
                    else set()
                )
                assert {
                    k: v
                    for k, v in cs.get("object_review_profile", {}).items()
                    if k not in ignored
                } == {k: v for k, v in review.items() if k not in ignored}, (
                    "Object review profile changed; fresh inference required"
                )
                if ppe_enabled:
                    assert cs.get("ppe_final_selected") is True, (
                        "Final PPE cache required"
                    )
        if (
            models is None
            and (not a.reuse_run)
            and spec.get("enabled_features") != ["ppe"]
        ):
            models = ObjectRecallEnsemble(
                YOLO(ROOT / obj["baseline_weights"]),
                YOLO(ROOT / obj["supplement_weights"]),
            )
        if ppe_enabled and not cached and ppe is None:
            person_model = YOLO(ROOT / profile["weights"]["objects"])
            ppe = FinalPPEDetector()
        pcfg = (
            json.load(open(ROOT / spec["camera_config"]))
            if spec["camera_config"]
            else None
        )
        if a.proximity_geometry:
            pcfg = {**pcfg, "distance_geometry": a.proximity_geometry}
        if a.temporal_riders:
            pcfg = {
                **pcfg,
                "temporal_riders": True,
                "exclude_riders_from_all_proximity": True,
                "expose_current_person_candidates": True,
                "occupancy_minimum_observations": 1,
            }
        # Presentation IDs match data/videos: 1 proximity, 3 PPE, 4 dwell, 5 warehouse summary.
        zone = (
            TrackedZone(pcfg, (h, w), rate)
            if n == 4
            else ScenarioZone(pcfg, (h, w), rate)
            if n == 5
            else None
        )
        prox = (
            TrackedProximity(pcfg, rate)
            if n == 1
            else TrackedProximity(
                {
                    **json.load(open(ROOT / "configs/cameras/forward-proximity.json")),
                    **pcfg,
                    "camera_id": "warehouse-conditional",
                    "warning_ratio": 1.0,
                    "critical_ratio": pcfg.get("critical_ratio", 0.3),
                    "distance_geometry": pcfg.get("distance_geometry", "box_boundary"),
                    "associate_riders": True,
                    "tracker_fuse_score": pcfg.get("tracker_fuse_score", True),
                    "forklift_tracker_fuse_score": pcfg.get(
                        "forklift_tracker_fuse_score", True
                    ),
                    "forklift_tracker_high_threshold": pcfg.get(
                        "forklift_tracker_high_threshold", 0.25
                    ),
                },
                rate,
            )
            if n == 5
            else None
        )
        vehicle_tracker = None
        pair = None
        pt = PersonTracker(
            rate,
            expose_current_candidates=True,
            fuse_score=runtime_config()["tracker_fuse_score"],
        )
        prule = PPEEvents(policy) if ppe_enabled else None
        rows = []
        feature_rows = {}
        laststate = {}
        prev = None
        idx = 0
        writer = cv2.VideoWriter(
            str(dest / "demo.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), rate, (w, h)
        )
        if not writer.isOpened():
            raise ValueError("Writer failed")
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if idx % stride:
                    idx += 1
                    continue
                t = idx / fps
                if a.max_seconds is not None and t >= a.max_seconds:
                    break
                small = cv2.resize(frame, (96, 54)).astype(np.float32) / 255
                cut = (
                    prev is not None
                    and float(np.abs(small - prev).mean())
                    > manifest["scene_cut_threshold"]
                )
                prev = small
                if a.reuse_run:
                    assert idx in cached
                    detections = cached[idx]["object_detections"]
                elif review:
                    detections = []
                else:
                    prediction = models.predict(
                        frame,
                        conf=0.1,
                        imgsz=1280 if n in [4, 5] else 640,
                        device="cpu",
                        verbose=False,
                    )[0]
                    detections = [
                        {
                            "class": prediction.names[int(b.cls.item())],
                            "confidence": float(b.conf.item()),
                            "bbox_xyxy": b.xyxy[0].tolist(),
                        }
                        for b in prediction.boxes
                    ]
                rejected_objects = (
                    cached[idx].get("rejected_object_proposals", [])
                    if a.reuse_objects
                    else []
                )
                if (
                    review
                    and (not a.reuse_objects)
                    and spec.get("enabled_features") == ["ppe"]
                ):
                    if review_person_model is None:
                        review_person_model = YOLO(ROOT / profile["weights"]["objects"])
                    pred = review_person_model.predict(
                        frame,
                        classes=[0],
                        conf=review["minimum_confidence_by_class"]["person"],
                        imgsz=1280,
                        device="cpu",
                        verbose=False,
                    )[0]
                    detections = [
                        {
                            "class": "person",
                            "confidence": float(b.conf.item()),
                            "bbox_xyxy": b.xyxy[0].tolist(),
                        }
                        for b in pred.boxes
                    ]
                    detections, rejected_objects = exclude_confirmed_equipment(
                        detections, (h, w), review, frame
                    )
                elif review and (not a.reuse_objects):
                    if review_rows:
                        detections, rejected_objects = select_review_objects(
                            review_rows[idx], (h, w), review
                        )
                    else:
                        if models is None:
                            models = ObjectRecallEnsemble(
                                YOLO(ROOT / obj["baseline_weights"]),
                                YOLO(ROOT / obj["supplement_weights"]),
                            )
                        if review_models is None:
                            review_models = build_review_models(
                                models, review, lambda path: YOLO(ROOT / path)
                            )
                        if review_person_model is None:
                            review_person_model = YOLO(
                                ROOT / profile["weights"]["objects"]
                            )
                        detections, rejected_objects = predict_review_objects(
                            review_models, review_person_model, frame, review
                        )
                if a.refine_reused_vehicles:
                    if reuse_vehicle_model is None:
                        reuse_vehicle_model = YOLO(
                            ROOT / review["vehicle_support_weights"]
                        )
                    detections, rejected_objects = refine_reused_vehicle_support(
                        frame, detections, rejected_objects, review, reuse_vehicle_model
                    )
                movement_inputs = copy.deepcopy(detections)
                if a.temporal_riders:
                    from src.vehicle_person_cleanup import (
                        separate_merged_vehicle_people,
                    )

                    detections, merged = separate_merged_vehicle_people(detections)
                    rejected_objects = rejected_objects + merged
                groups = {}
                zrow = zone.update(t, detections, (h, w), cut) if zone else None
                if zrow:
                    mark_uncertain_lane_events(zrow["events"])
                if zrow:
                    for kind in ["zone_access", "zone_dwell"]:
                        groups[kind] = [
                            e for e in zrow["events"] if e["event_type"] == kind
                        ]
                if prox:
                    proximity = prox.update(
                        t,
                        detections,
                        (h, w),
                        cut,
                        roi_active=zrow["roi_active"] if zrow else True,
                    )
                    events = proximity["events"]
                    if n == 1:
                        events = exclude_driver_overlap_pairs(
                            events, pcfg.get("driver_overlap_exclusion_ratio", 0.8)
                        )
                    groups["proximity"] = events
                if pair:
                    old = vehicle_tracker.scene
                    vehicles, _ = vehicle_tracker.update(t, detections, (h, w), cut)
                    if old != vehicle_tracker.scene:
                        pair.reset()
                    groups["forklift_proximity"] = pair.update(t, vehicles, (h, w))
                suppressed_ppe = []
                ppe_inputs = []
                blocked_helmets = []
                if ppe_enabled:
                    if idx in cached:
                        entry = cached[idx]
                        if (
                            entry["ppe_runtime_version"] != runtime_version(n)
                            or entry["ppe_input_detections"] is None
                        ):
                            raise ValueError(
                                "PPE cache is not current; install the latest runtime or run --fresh"
                            )
                        ppe_inputs = entry["ppe_input_detections"]
                        heads = entry["head_detections"]
                        blocked_helmets = entry["ppe_blocked_helmet_candidates"]
                        ppe_tracks, _ = pt.update(t, ppe_inputs, (h, w), cut)
                    else:
                        ppe_inputs = [
                            dict(d) for d in detections if d["class"] == "person"
                        ]
                        if not review:
                            pp = person_model.predict(
                                frame,
                                classes=[0],
                                conf=0.1,
                                imgsz=1280,
                                device="cpu",
                                verbose=False,
                            )[0]
                            ppe_inputs = [
                                {
                                    "class": "person",
                                    "confidence": float(b.conf.item()),
                                    "bbox_xyxy": b.xyxy[0].tolist(),
                                }
                                for b in pp.boxes
                            ]
                        ppe_tracks, _ = pt.update(t, ppe_inputs, (h, w), cut)
                        heads, blocked_helmets = infer_runtime_heads(
                            ppe,
                            frame,
                            [tr["detected_bbox_xyxy"] for tr in ppe_tracks],
                            policy,
                            review,
                            n,
                        )
                    ppe_tracks = assign_head_observations(ppe_tracks, heads, h)
                    ppe_events, _ = prule.update(t, ppe_tracks, (), cut)
                    ppe_events = apply_ppe_vehicle_guard(
                        ppe_events,
                        [
                            d["bbox_xyxy"]
                            for d in detections
                            if d.get("class") == "forklift"
                        ],
                    )
                    groups["ppe"] = ppe_events
                else:
                    ppe_tracks, heads = [], []
                groups = presentation_groups(groups, spec)
                if spec.get("enabled_features") == ["ppe"]:
                    detections = presentation_detections(detections, spec)
                if zrow:
                    zrow["events"] = [
                        e for e in zrow["events"] if e["event_type"] in groups
                    ]
                    zrow["transitions"] = [
                        e
                        for e in zrow.get("transitions", [])
                        if e["event_type"] in groups
                    ]
                record = {
                    "frame_index": idx,
                    "timestamp_seconds": t,
                    "scene_cut": cut,
                    "object_detections": detections,
                    "ppe_tracks": ppe_tracks,
                    "head_detections": heads,
                    "features": {k: feature_status(v) for k, v in groups.items()},
                    "feature_events": groups,
                    "zone": zrow,
                    "global_safety_status": "not_evaluated",
                    "movement_input_detections": movement_inputs,
                }
                if ppe_enabled:
                    record.update(
                        ppe_input_detections=ppe_inputs,
                        ppe_runtime_version=runtime_version(n),
                        ppe_blocked_helmet_candidates=blocked_helmets,
                    )
                if prox:
                    record["proximity_tracking"] = proximity
                if review:
                    record.update(
                        rejected_object_proposals=rejected_objects,
                        unassociated_ppe_review=suppressed_ppe,
                    )
                rows.append(record)
                for feature, events in groups.items():
                    old = laststate.setdefault(feature, {})
                    transitions = []
                    now = {}
                    for e in events:
                        identity = tuple(e.get("forklift_track_ids", [])) or tuple(
                            (
                                str(e.get(k, ""))
                                for k in [
                                    "track_id",
                                    "person_track_id",
                                    "forklift_track_id",
                                ]
                            )
                        )
                        key = (e["event_type"], identity)
                        state = (
                            e.get("severity"),
                            e.get("observation_status"),
                            e.get("ppe_state"),
                            e.get("inside"),
                            e.get("reason"),
                            e.get("risk_reason"),
                            bool(e.get("hood_evidence")),
                        )
                        now[key] = state
                        if old.get(key) != state:
                            transitions.append(e)
                    laststate[feature] = now
                    feature_rows.setdefault(feature, []).append(
                        {
                            "frame_index": idx,
                            "timestamp_seconds": t,
                            "events": events,
                            "transitions": transitions,
                            "scene_id": zrow["scene_id"] if zrow else pt.scene,
                            "roi_active": zrow["roi_active"] if zrow else True,
                        }
                    )
                canvas = render(
                    frame.copy(),
                    groups,
                    (zone, zrow) if zone else None,
                    detections=presentation_detections(detections, spec)
                    if review
                    else None,
                    proximity_warning_ratio=pcfg.get("warning_ratio", 1.6),
                    include_other_safe_people=review.get(
                        "show_safe_pairs_for_other_people", False
                    ),
                    vehicle_occupancy=proximity.get("vehicle_occupancy")
                    if prox
                    else None,
                )
                if a.temporal_riders and prox:
                    for person in proximity["people"]:
                        if person["track_id"] not in proximity["rider_associations"]:
                            continue
                        x, y, _, _ = map(int, person["detected_bbox_xyxy"])
                        cv2.putText(
                            canvas,
                            "RIDER / NOT PEDESTRIAN",
                            (x, max(135, y + 32)),
                            0,
                            0.38,
                            (255, 220, 80),
                            1,
                        )
                if review and n in [1, 5] and pcfg:
                    cv2.putText(
                        canvas,
                        f"WARNING <= {pcfg['warning_ratio']:.2f} / CRITICAL <= {pcfg['critical_ratio']:.2f} person-height gap",
                        (12, h - 34),
                        0,
                        0.42,
                        (230, 230, 230),
                        1,
                    )
                cv2.putText(
                    canvas,
                    f"VIDEO {spec.get('presentation_video_number', n)} / t={t:.2f}s / DEMO-ADAPTED / METERS UNCALIBRATED",
                    (12, h - 14),
                    0,
                    0.48,
                    (0, 190, 255),
                    1,
                )
                writer.write(canvas)
                if len(rows) in [1, 26, 51, 76]:
                    cv2.imwrite(str(dest / f"preview_{len(rows) - 1}.jpg"), canvas)
                if len(rows) % 25 == 0:
                    print(f"video{n}: {len(rows)} samples / {t:.1f}s", flush=True)
                idx += 1
        finally:
            cap.release()
            writer.release()
        (dest / "detections.jsonl").write_text(
            "".join((json.dumps(r) + "\n" for r in rows))
        )
        # Keep inert legacy keys to preserve config hashes and event IDs.
        context = {
            "camera_id": f"demo-video{n}",
            "video": source.name,
            "source_sha256": spec["source_sha256"],
            "model_version": hashlib.sha256(
                json.dumps(hashes, sort_keys=True).encode()
            ).hexdigest(),
            "config_version": hashlib.sha256(
                json.dumps(
                    {
                        "spec": spec,
                        "camera": pcfg,
                        "ppe_policy": policy,
                        "sample_fps": a.sample_fps,
                        "ppe_search": "full_recall",
                        "ppe_runtime": runtime_version(n) if ppe_enabled else None,
                        "hood_auxiliary": False,
                        "ppe_final": True,
                        "max_seconds": a.max_seconds,
                        "object_review_profile": review,
                        "forklift_specialist": None,
                        "forklift_specialist_imgsz": None,
                        "forklift_geometric_association": False,
                        "proximity_geometry_override": a.proximity_geometry,
                        "temporal_riders": a.temporal_riders,
                        "vehicle_recovery_provenance": cs.get(
                            "vehicle_recovery_provenance"
                        )
                        if a.reuse_run
                        else None,
                        "forklift_additional_weights": [],
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest(),
        }
        counts = {}
        for feature, records in feature_rows.items():
            directory = dest / feature
            directory.mkdir()
            export_events(
                records, directory / "events_v1.jsonl", feature=feature, context=context
            )
            counts[feature] = {
                state: sum(
                    (
                        feature_status(r["events"])["display_state"] == state
                        for r in records
                    )
                )
                for state in ["SAFE", "WARNING", "CRITICAL", "UNKNOWN"]
            }
        summary = {
            "source": str(source),
            "source_sha256": spec["source_sha256"],
            "video_number": n,
            "presentation_video_number": spec.get("presentation_video_number") or n,
            "samples": len(rows),
            "processed_fps": rate,
            "ppe_enabled": ppe_enabled,
            "ppe_final_selected": ppe_enabled,
            "review_max_seconds": a.max_seconds,
            "forklift_geometric_association": False,
            "ppe_cache_reused": bool(cached),
            "all_real_inference_reused_from": str(a.reuse_run)
            if a.reuse_objects
            else None,
            "ppe_reused_from": str(a.reuse_run) if a.reuse_run else None,
            "reused_vehicle_context_refinement": a.refine_reused_vehicles,
            "ppe_search": "full_recall",
            "features": counts,
            "context": context,
            "model_hashes": hashes,
            "camera_config": pcfg,
            "geometry_comparison_override": a.proximity_geometry,
            "temporal_riders": a.temporal_riders,
            "vehicle_recovery_provenance": cs.get("vehicle_recovery_provenance")
            if a.reuse_run
            else None,
            "limitations": [
                "Sampled frames; zero misses not proven for unseen scenes",
                "No calibrated meter distance",
                "Hood-only follows user bare-head labeling policy; missing or uncertain detections remain UNKNOWN",
                "PPE WARNING is review candidate, not verified violation",
                "ROI floor proxies and geometry require review; scene cuts disable ROI",
            ],
        }
        summary["enabled_features"] = sorted(groups)
        if ppe_enabled:
            summary["ppe_runtime_version"] = runtime_version(n)
        if a.temporal_riders:
            summary.update(
                status="current_default",
                rider_confirmation_observations=3,
                role_pending_policy="unconfirmed_no_distance_or_lane_alert",
                ppe_body_cache_note="PPE observations preserved from validated original cache; body cleanup applies to movement rules and display objects",
            )
        if review:
            summary.update(
                object_review_profile=review,
                object_review_cache=str(a.object_review_cache)
                if a.object_review_cache
                else None,
            )
        (dest / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        totals.append(summary)
        (a.output / "manifest.json").write_text(json.dumps(totals, indent=2) + "\n")
        print(f"video{n} complete", flush=True)


if __name__ == "__main__":
    main()
