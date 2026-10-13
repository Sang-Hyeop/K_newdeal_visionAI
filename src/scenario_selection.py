"""User-approved active demo selection; retain historical scenario metadata."""
def review_video_numbers(requested,manifest):
    scenarios=manifest['scenarios'];active={q['video_number']for q in scenarios if q.get('review_enabled',True)}
    if requested is None:return [q['video_number']for q in scenarios if q['video_number']in active]
    disabled=[n for n in requested if any(q['video_number']==n and not q.get('review_enabled',True)for q in scenarios)]
    if disabled:raise ValueError(f'Videos {disabled} excluded by user from active review/demo')
    return requested
