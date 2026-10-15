"""Active five-video presentation selection; IDs match data/videos filenames."""
def review_video_numbers(requested,manifest):
    scenarios=manifest['scenarios'];active={q['video_number']for q in scenarios if q.get('review_enabled',True)}
    if requested is None:return [q['video_number']for q in scenarios if q['video_number']in active]
    disabled=[n for n in requested if any(q['video_number']==n and not q.get('review_enabled',True)for q in scenarios)]
    if disabled:raise ValueError(f'Videos {disabled} excluded by user from active review/demo')
    return requested


def scenario_directory(spec):
    """Filesystem folders use the same 1-5 IDs as presentation / filenames."""
    return f"video{spec.get('presentation_video_number') or spec['video_number']}"


def enabled_features(spec):
    """Current presentation feature allowlist; absent in historical metadata."""
    if 'enabled_features' in spec:return set(spec['enabled_features'])
    return None


def presentation_groups(groups, spec):
    enabled=enabled_features(spec)
    return {k:v for k,v in groups.items() if enabled is None or k in enabled}


def presentation_detections(detections, spec):
    enabled=enabled_features(spec)
    if enabled in ({'ppe'}, {'zone_dwell'}):
        return [d for d in detections if d['class']=='person']
    return detections
