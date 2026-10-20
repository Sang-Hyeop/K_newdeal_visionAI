# 역할: 발표용 1~5번 영상 선택과 켤 기능(proximity/zone/ppe) 필터를 담당한다.
"""발표용 1~5번 영상 선택과 켤 기능(proximity/zone/ppe) 필터를 담당한다."""


def review_video_numbers(requested, manifest):
    scenarios = manifest["scenarios"]
    active = {q["video_number"] for q in scenarios if q.get("review_enabled", True)}
    if requested is None:
        return [q["video_number"] for q in scenarios if q["video_number"] in active]
    disabled = [
        n
        for n in requested
        if any(
            q["video_number"] == n and not q.get("review_enabled", True)
            for q in scenarios
        )
    ]
    if disabled:
        raise ValueError(f"Videos {disabled} excluded by user from active review/demo")
    return requested


def scenario_directory(spec):
    """Filesystem folders use the same 1-5 IDs as presentation / filenames."""
    return f"video{spec.get('presentation_video_number') or spec['video_number']}"


def enabled_features(spec):
    """Current presentation feature allowlist; absent in historical metadata."""
    if "enabled_features" in spec:
        return set(spec["enabled_features"])
    return None


def presentation_groups(groups, spec):
    enabled = enabled_features(spec)
    return {k: v for k, v in groups.items() if enabled is None or k in enabled}


def presentation_detections(detections, spec):
    enabled = enabled_features(spec)
    if enabled in ({"ppe"}, {"zone_dwell"}):
        return [d for d in detections if d["class"] == "person"]
    return detections


def cache_model_hashes_match(cached, current, ppe_enabled, ppe_weights):
    """A disabled PPE feature must not invalidate cached movement observations."""
    return all(
        cached_hash == current[path]
        for path, cached_hash in cached.items()
        if path in current
        and "hoodie" not in path
        and (ppe_enabled or path != ppe_weights)
    )
