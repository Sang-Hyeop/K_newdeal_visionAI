# 현재 이벤트·관측 출력 계약 v1

현재 실행은 `handoff.py`이며 공통 직렬화는 `src/event_contract.py`입니다. 백엔드 HTTP 계약은 [API_SPEC](../backend_v1/API_SPEC.md)를 따릅니다.

## 파일 구분

- `outputs/events/presentation1`~`presentation5` 아래 기능별 `events_v1.jsonl`: 상태 전환 이벤트 이력.
- 같은 위치의 `observations_v1.jsonl`: 각 분석 프레임의 관측·대상별 이벤트·기능 집계 상태.
- `outputs/diagnostics/`의 `detections.jsonl`: 객체·머리 검출 및 재현용 기록. 전환 이벤트 테이블에 매 프레임 검출을 새 알람으로 삽입하지 않습니다.

## 이벤트 필드

`schema_version`, `event_id`, `camera_id`, `video`, `source_sha256`, `timestamp_seconds`, `event_type`, `severity`, `observation_status`, `track_ids`, `evidence`, `model_version`, `config_version`, `scope`를 포함합니다. 표시용 `assessment_state`, `alert_eligible`, `notification_category`, `status_reason`도 전달합니다.

- event_type: proximity / zone_access / zone_dwell / ppe / status. 공통 모듈은 forklift_proximity도 지원하지만 현재 발표의 필수 기능은 아닙니다.
- severity: SAFE / WARNING / CRITICAL / null. observation_status가 unconfirmed이면 severity는 null입니다.
- timestamp_seconds는 원본 영상 내 초입니다. 영상별 시간이므로 서로 다른 영상의 초를 하나의 실시간 시계로 비교하지 않습니다.
- event_id는 입력·버전·내용에 기반한 해시로, 같은 이벤트 재가져오기 중복 방지에 사용합니다.
- evidence에는 bbox·추적 ID·ROI·거리 방법·체류 등 근거를 보존합니다. 원본 bbox는 영상 픽셀 좌표이고 정규화 ROI 좌표와 혼용하지 않습니다. 거리 보정이 없으므로 distance_meters는 null입니다.

## 상태와 알림

위험 푸시·팝업 대상은 `alert_eligible == true`입니다. 상태 표시용 미확인 전환까지 모두 위험 알람으로 만들지 않습니다. 판정 중, 판정 불가, 관측 소실, 대상 미관측은 상태 구분을 유지합니다. 카메라 장애·장기 관측 소실에 대한 운영 알림은 별도 정책입니다.

관측에는 feature, camera_id, video, timestamp_seconds, frame_index, scene_id, events, feature_status, observation_status와 global_safety_status=not_evaluated가 들어갑니다. feature_status의 display_state 및 dashboard_state, assessment_counts, risk_alert_count 등을 사용합니다. CRITICAL/WARNING을 미확인이 덮지 않으며, 위험이 없어도 미확인 대상이 있으면 임의 SAFE로 만들지 않습니다. 기능별 상태를 현장 전체 안전으로 확대하지 않습니다.

PPE 머리 클래스는 작업자 전체 미착용 이벤트와 동일하지 않습니다. 사람 연결·시간적 확인·충돌 근거를 고려한 결과를 사용하며 WARNING은 검토 후보입니다. 실제 위반 확정으로 설명하지 않습니다. 구체 임계값은 `configs/ppe-user-approved-policy-2026-10-15.json`과 카메라 설정을 따릅니다.

## 현재 백엔드의 범위

JSONL 가져오기→SQLite 저장→GET 조회가 구현돼 있습니다. `/feature-status`는 선택한 영상의 마지막 관측이며 재생 중인 특정 시각을 자동 조회하는 기능이 아닙니다. 영상 재생 시각별 상태 조회와 신규 이벤트 실시간 수신·푸시는 후속 구현입니다. 최신 설치·실행은 [팀 시작 안내](github-team-quickstart.md)를 따릅니다.
