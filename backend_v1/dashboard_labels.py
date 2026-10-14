"""Display-only Korean labels for dashboard integration.

API field names and enum values stay English. Callers map for UI rendering only.
Unknown codes return a safe fallback without raising.
"""
from __future__ import annotations

EVENT_TYPE_LABELS = {
    'proximity': '지게차·작업자 근접 위험',
    'zone_access': '구역 접근·진입',
    'zone_dwell': '구역 체류',
    'ppe': '안전모 착용 상태',
    'status': '상태 정보',
}

SEVERITY_LABELS = {
    'SAFE': '안전',
    'WARNING': '주의',
    'CRITICAL': '위험',
}

OBSERVATION_STATUS_LABELS = {
    'confirmed': '확인됨',
    'unconfirmed': '미확인',
}

DISPLAY_STATE_LABELS = {
    'SAFE': '안전',
    'WARNING': '주의',
    'CRITICAL': '위험',
    'UNKNOWN': '미확인',
}

GLOBAL_SAFETY_LABELS = {
    'not_evaluated': '평가하지 않음',
}

REGION_LABELS = {
    'outside': '구역 밖',
    'approach': '구역 접근',
    'inside': '구역 내부',
    'unknown': '미확인',
}

FIELD_LABELS = {
    'camera_id': '카메라',
    'video': '영상',
    'timestamp_seconds': '영상 시간',
    'event_type': '이벤트 종류',
    'severity': '위험도',
    'observation_status': '관측 상태',
    'track_ids': '추적 ID',
    'event_id': '이벤트 ID',
    'observed_dwell_seconds': '관측 체류시간',
    'roi_id': '구역 ID',
    'model_version': '모델 버전',
    'config_version': '설정 버전',
    'source_sha256': '원본 영상 해시',
    'feature': '기능',
    'display_state': '표시 상태',
    'global_safety_status': '전체 안전 상태',
    'evidence': '근거',
    'distance_meters': '미터 거리',
}

PPE_STATE_LABELS = {
    'helmet_detected': '안전모 감지',
    'no_helmet_candidate': '미착용 후보',
    'conflicting_evidence': '근거 충돌',
    'unknown': '불명',
}

REASON_LABELS = {
    'image_plane_proximity_rule': '화면상 거리 규칙',
    'no_observed_subject_pair_or_person': '관측 대상 없음',
    'pair_not_observed': '쌍 관측 끊김',
    'person_track_confirmation_pending': '사람 추적 확인 대기',
    'person_role_confirmation_pending': '역할 확인 대기',
    'pending_temporal_confirmation': '시간 누적 확인 대기',
    'possible_operator_or_occluded_person': '운전자·가림 가능',
    'vehicle_occupancy_unconfirmed': '차량 점유 미확인',
    'forklift_extent_clipped': '지게차 화면 잘림',
    'stable_helmet_evidence': '안전모 착용 근거 안정',
    'stable_no_helmet_candidate_requires_review': '미착용 후보(검토 필요)',
    'stable_low_confidence_ppe_requires_review': 'PPE 신뢰도 낮음(검토)',
    'stable_conflicting_ppe_requires_review': 'PPE 근거 충돌(검토)',
    'conflicting_or_missing_or_low_confidence_head': '머리 검출 충돌·부족·저신뢰',
    'supplement_only_helmet_unconfirmed': '보조 근거만 있어 미확정',
    'outside_restricted_robot_roi': '제한 ROI 밖',
    'inside_restricted_robot_roi': '제한 ROI 안',
    'possible_operator_or_equipment_person_box': '운전자·설비 박스 가능',
    'person_not_observed': '사람 미관측',
    'head_not_observed': '머리 미관측',
}

# presentation_video_number -> API video filter value (from configs/demo-videos.json + live API)
PRESENTATION_VIDEOS = {
    1: '1_forklift_worker_collision_risk.mp4',
    2: '2_restricted_zone_intrusion.mp4',
    3: '3_PPE_Helmet.mp4',
    4: '4_hazard_zone_dwell.mp4',
    5: '5_Logistics Warehouse.mp4',
}

PRESENTATION_TITLES = {
    1: '1. 지게차–작업자 근접',
    2: '2. 제한구역 접근',
    3: '3. 안전모(PPE)',
    4: '4. 위험구역 체류',
    5: '5. 물류창고 종합',
}

EMPTY_EVENTS_MESSAGE = '조회 결과 없음'
EMPTY_OBSERVATIONS_MESSAGE = '관측 없음'
UNKNOWN_LABEL = '알 수 없음'
NOT_PROVIDED_METERS = '미제공'


def label_for(table: dict, value, *, allow_null: bool = False) -> str:
    if value is None:
        return '미확인' if allow_null else UNKNOWN_LABEL
    if value in table:
        return table[value]
    return f'{UNKNOWN_LABEL} ({value})'


def event_type_label(value) -> str:
    return label_for(EVENT_TYPE_LABELS, value)


def severity_label(value, observation_status=None) -> str:
    if value is None:
        if observation_status == 'unconfirmed':
            return '미확인'
        return '미확인'
    return label_for(SEVERITY_LABELS, value)


def observation_status_label(value) -> str:
    return label_for(OBSERVATION_STATUS_LABELS, value)


def display_state_label(value) -> str:
    return label_for(DISPLAY_STATE_LABELS, value)


def global_safety_label(value='not_evaluated') -> str:
    return label_for(GLOBAL_SAFETY_LABELS, value)


def region_label(value) -> str:
    return label_for(REGION_LABELS, value)


def field_label(name: str) -> str:
    return FIELD_LABELS.get(name, name)


def ppe_state_label(value) -> str:
    return label_for(PPE_STATE_LABELS, value)


def reason_label(value) -> str:
    return label_for(REASON_LABELS, value)


def format_timestamp_seconds(value) -> str:
    """Video-relative seconds only; never attaches wall-clock dates."""
    if value is None:
        return UNKNOWN_LABEL
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f'{UNKNOWN_LABEL} ({value})'
    if number != number or number in (float('inf'), float('-inf')):  # NaN/inf
        return f'{UNKNOWN_LABEL} ({value})'
    if number == int(number) and abs(number) < 1e15:
        return f'{int(number)}초'
    text = f'{number:.3f}'.rstrip('0').rstrip('.')
    return f'{text}초'


def format_dwell_seconds(value) -> str:
    return format_timestamp_seconds(value)


def format_distance_meters(value) -> str:
    if value is None:
        return NOT_PROVIDED_METERS
    return f'{UNKNOWN_LABEL} (보정 없는 m 표시 금지: {value})'


def presentation_video(number: int) -> str | None:
    return PRESENTATION_VIDEOS.get(number)


def presentation_title(number: int) -> str | None:
    return PRESENTATION_TITLES.get(number)


def empty_events_message() -> str:
    return EMPTY_EVENTS_MESSAGE


def empty_observations_message() -> str:
    return EMPTY_OBSERVATIONS_MESSAGE
