"""Per-feature banner aggregation; never declares the entire site safe."""
def feature_status(events):
    severities=[e.get('severity') if e.get('observation_status')=='confirmed' else None for e in events]
    unknown=sum(s is None for s in severities)
    severity='CRITICAL' if 'CRITICAL' in severities else 'WARNING' if 'WARNING' in severities else None if not severities or unknown else 'SAFE'
    return {'severity':severity,'display_state':severity or 'UNKNOWN','observed_event_count':len(events),
            'unknown_event_count':unknown,'coverage':'unconfirmed' if not events else 'partial' if unknown else 'observed_subjects_only',
            'scope':'this_feature_and_observed_subjects_only','global_safety_status':'not_evaluated'}
