"""Presentation and alert routing, independent of the underlying risk verdict."""
from collections import Counter

PENDING_REASONS = {'pending_temporal_confirmation', 'person_track_confirmation_pending'}
LOST_REASONS = {'person_not_observed', 'pair_not_observed'}
LABELS = {'pending': 'PENDING', 'unassessable': 'UNASSESSABLE',
          'observation_lost': 'NOT OBSERVED', 'no_observed_subjects': 'NO OBSERVED TARGET',
          'observed': 'OBSERVED'}

def event_display(event):
    confirmed = event.get('observation_status') == 'confirmed' and event.get('severity') is not None
    reason = event.get('reason')
    state = 'no_observed_subjects' if reason == 'no_observed_subject_pair_or_person' else 'observed' if confirmed else 'pending' if reason in PENDING_REASONS else 'observation_lost' if reason in LOST_REASONS else 'unassessable'
    return {'assessment_state': state,
            'alert_eligible': confirmed and event.get('severity') in {'WARNING', 'CRITICAL'},
            'notification_category': 'risk' if confirmed and event.get('severity') in {'WARNING', 'CRITICAL'} else 'status',
            'status_reason': reason or 'insufficient_observation'}

def display_summary(events):
    counts = Counter(event_display(e)['assessment_state'] for e in events)
    alerts = [e['severity'] for e in events if event_display(e)['alert_eligible']]
    state = 'CRITICAL' if 'CRITICAL' in alerts else 'WARNING' if alerts else 'unassessable' if counts['unassessable'] else 'pending' if counts['pending'] else 'observation_lost' if counts['observation_lost'] else 'observed' if events else 'no_observed_subjects'
    return {'dashboard_state': state,
            'assessment_counts': {k: counts[k] for k in ['observed', 'pending', 'unassessable', 'observation_lost']},
            'risk_alert_count': len(alerts),
            'notification_category': 'risk' if alerts else 'status'}

def display_label(events):
    summary = display_summary(events)
    state = summary['dashboard_state']
    if state == 'observed':
        return 'OBSERVED / NO RISK ALERT'
    return LABELS.get(state, state)
