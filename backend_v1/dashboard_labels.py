"""Display-only Korean labels loaded from configs/dashboard-labels.ko.json.

API field names and enums stay English. Mapping is for UI/CSV display layers.
Functions never mutate the input event object.
"""
from __future__ import annotations

import copy
import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELS_PATH = ROOT / 'configs' / 'dashboard-labels.ko.json'

_CACHE: dict | None = None
_CACHE_PATH: Path | None = None


def load_labels(path: Path | None = None) -> dict:
    """Load UTF-8 label JSON without BOM. Cached per path."""
    global _CACHE, _CACHE_PATH
    target = Path(path) if path is not None else DEFAULT_LABELS_PATH
    if _CACHE is not None and _CACHE_PATH == target:
        return _CACHE
    raw = target.read_bytes()
    if raw.startswith(b'\xef\xbb\xbf'):
        raise ValueError(f'BOM not allowed in default label file: {target}')
    data = json.loads(raw.decode('utf-8'))
    _CACHE, _CACHE_PATH = data, target
    return data


def reload_labels(path: Path | None = None) -> dict:
    global _CACHE, _CACHE_PATH
    _CACHE, _CACHE_PATH = None, None
    return load_labels(path)


def _table(name: str) -> dict:
    return load_labels().get(name) or {}


def label_for(table: dict, value, *, null_as: str | None = None) -> str:
    labels = load_labels()
    if value is None:
        return null_as if null_as is not None else labels.get('null_display', '미확인')
    key = value if not isinstance(value, bool) else value
    if key in table:
        return table[key]
    if value is None and 'null' in table:
        return table['null']
    prefix = labels.get('unknown_prefix', '알 수 없음')
    return f'{prefix} ({value})'


def event_type_label(value) -> str:
    return label_for(_table('event_types'), value)


def severity_label(value, observation_status=None) -> str:
    table = _table('severities')
    if value is None:
        return table.get('null', load_labels().get('null_display', '미확인'))
    return label_for(table, value)


def observation_status_label(value) -> str:
    return label_for(_table('observation_statuses'), value)


def assessment_state_label(value) -> str:
    return label_for(_table('assessment_states'), value)


def display_state_label(value) -> str:
    return label_for(_table('display_states'), value)


def notification_category_label(value) -> str:
    return label_for(_table('notification_categories'), value)


def global_safety_label(value='not_evaluated') -> str:
    return label_for(_table('global_safety_statuses'), value)


def region_label(value) -> str:
    return label_for(_table('regions'), value)


def ppe_state_label(value) -> str:
    return label_for(_table('ppe_states'), value)


def violation_status_label(value) -> str:
    return label_for(_table('violation_statuses'), value)


def object_class_label(value) -> str:
    return label_for(_table('object_classes'), value)


def camera_label(camera_id) -> str:
    table = _table('cameras')
    if camera_id in table:
        return table[camera_id]
    prefix = load_labels().get('unknown_prefix', '알 수 없음')
    return f'{prefix} ({camera_id})'


def zone_label(roi_id) -> str:
    if roi_id is None:
        return ''
    table = _table('zones')
    if roi_id in table:
        return table[roi_id]
    prefix = load_labels().get('unknown_prefix', '알 수 없음')
    return f'{prefix} ({roi_id})'


def video_label(video) -> str:
    entry = _table('videos').get(video)
    if isinstance(entry, dict) and entry.get('label'):
        return entry['label']
    if isinstance(entry, str):
        return entry
    prefix = load_labels().get('unknown_prefix', '알 수 없음')
    return f'{prefix} ({video})'


def field_label(name: str) -> str:
    return _table('columns').get(name, name)


def format_timestamp_seconds(value) -> str:
    if value is None:
        return load_labels().get('null_display', '미확인')
    try:
        number = float(value)
    except (TypeError, ValueError):
        return label_for({}, value)
    if number != number or number in (float('inf'), float('-inf')):
        return label_for({}, value)
    if number == int(number) and abs(number) < 1e15:
        return f'{int(number)}초'
    text = f'{number:.3f}'.rstrip('0').rstrip('.')
    return f'{text}초'


def format_dwell_seconds(value) -> str:
    return format_timestamp_seconds(value)


def format_distance_meters(value) -> str:
    if value is None:
        return load_labels().get('meters_not_provided', '미제공')
    return f'{load_labels().get("unknown_prefix", "알 수 없음")} (보정 없는 m 표시 금지: {value})'


def presentation_video(number: int) -> str | None:
    for video, meta in _table('videos').items():
        if isinstance(meta, dict) and meta.get('presentation_video_number') == number:
            return video
    return None


def presentation_title(number: int) -> str | None:
    video = presentation_video(number)
    return video_label(video) if video else None


def empty_events_message() -> str:
    return load_labels().get('empty_events_message', '조회 결과 없음')


def empty_observations_message() -> str:
    return load_labels().get('empty_observations_message', '관측 없음')


def csv_header_order() -> list[str]:
    return list(load_labels().get('csv_header_order') or [])


def display_view(event: dict) -> dict:
    """Return a new display dict; does not mutate event."""
    source = copy.deepcopy(event)
    evidence = source.get('evidence') if isinstance(source.get('evidence'), dict) else {}
    return {
        'event_id': source.get('event_id'),
        'schema_version': source.get('schema_version'),
        'camera_id': source.get('camera_id'),
        'camera_label': camera_label(source.get('camera_id')),
        'video': source.get('video'),
        'video_label': video_label(source.get('video')),
        'source_sha256': source.get('source_sha256'),
        'timestamp_seconds': source.get('timestamp_seconds'),
        'timestamp_display': format_timestamp_seconds(source.get('timestamp_seconds')),
        'event_type': source.get('event_type'),
        'event_type_label': event_type_label(source.get('event_type')),
        'severity': source.get('severity'),
        'severity_label': severity_label(source.get('severity'), source.get('observation_status')),
        'observation_status': source.get('observation_status'),
        'observation_status_label': observation_status_label(source.get('observation_status')),
        'assessment_state': source.get('assessment_state'),
        'assessment_state_label': assessment_state_label(source.get('assessment_state')),
        'alert_eligible': source.get('alert_eligible'),
        'notification_category': source.get('notification_category'),
        'notification_category_label': notification_category_label(source.get('notification_category')),
        'status_reason': source.get('status_reason'),
        'track_ids': source.get('track_ids'),
        'roi_id': evidence.get('roi_id'),
        'zone_label': zone_label(evidence.get('roi_id')),
        'observed_dwell_seconds': evidence.get('observed_dwell_seconds'),
        'ppe_state': evidence.get('ppe_state'),
        'ppe_state_label': ppe_state_label(evidence.get('ppe_state')) if evidence.get('ppe_state') is not None else '',
        'violation_status': evidence.get('violation_status'),
        'violation_status_label': (
            violation_status_label(evidence.get('violation_status'))
            if evidence.get('violation_status') is not None else ''),
        'region': evidence.get('region'),
        'region_label': region_label(evidence.get('region')) if evidence.get('region') is not None else '',
        'distance_meters': evidence.get('distance_meters', source.get('distance_meters')),
        'distance_meters_label': format_distance_meters(
            evidence.get('distance_meters', source.get('distance_meters'))),
        'model_version': source.get('model_version'),
        'config_version': source.get('config_version'),
        'scope': source.get('scope'),
        'evidence': evidence,
    }


def _csv_cell(value) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return str(value)


def event_to_csv_row(event: dict) -> dict:
    view = display_view(event)
    row = {}
    for key in csv_header_order():
        if key in view:
            row[key] = view[key]
        elif key == 'evidence':
            row[key] = view.get('evidence')
        else:
            row[key] = event.get(key)
    return row


def write_events_csv(events: list[dict], path: Path | None = None, *, utf8_sig: bool = False) -> str:
    """Write display CSV. Default UTF-8 without BOM; utf8_sig=True for Excel."""
    header = csv_header_order()
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    for event in events:
        raw_row = event_to_csv_row(event)
        writer.writerow({key: _csv_cell(raw_row.get(key)) for key in header})
    text = buffer.getvalue()
    if path is not None:
        encoding = 'utf-8-sig' if utf8_sig else 'utf-8'
        Path(path).write_text(text, encoding=encoding, newline='')
    return text


def write_display_json(events: list[dict], path: Path | None = None) -> str:
    payload = {
        'schema': 'dashboard_display_v1',
        'label_version': load_labels().get('version'),
        'count': len(events),
        'events': [display_view(event) for event in events],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    if path is not None:
        Path(path).write_text(text, encoding='utf-8', newline='\n')
    return text


# Compatibility aliases used by earlier tests
PRESENTATION_VIDEOS = {n: None for n in range(1, 6)}  # filled lazily via presentation_video

def _fill_presentation_videos():
    global PRESENTATION_VIDEOS
    PRESENTATION_VIDEOS = {n: presentation_video(n) for n in range(1, 6)}


_fill_presentation_videos()
