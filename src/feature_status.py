# 역할: 기능별 배너 상태(SAFE/WARNING/CRITICAL/UNKNOWN)를 집계한다. 현장 전체 안전은 선언하지 않는다.
"""기능별 배너 상태(SAFE/WARNING/CRITICAL/UNKNOWN)를 집계한다. 현장 전체 안전은 선언하지 않는다."""

from .observation_display import display_summary


def feature_status(events):
    severities = [
        e.get("severity") if e.get("observation_status") == "confirmed" else None
        for e in events
    ]
    unknown = sum(s is None for s in severities)
    severity = (
        "CRITICAL"
        if "CRITICAL" in severities
        else "WARNING"
        if "WARNING" in severities
        else None
        if not severities or unknown
        else "SAFE"
    )
    return {
        **display_summary(events),
        "severity": severity,
        "display_state": severity or "UNKNOWN",
        "observed_event_count": len(events),
        "unknown_event_count": unknown,
        "coverage": "unconfirmed"
        if not events
        else "partial"
        if unknown
        else "observed_subjects_only",
        "scope": "this_feature_and_observed_subjects_only",
        "global_safety_status": "not_evaluated",
    }
