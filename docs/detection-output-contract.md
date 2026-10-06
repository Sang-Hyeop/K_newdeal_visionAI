# 팀 연동용 검출 출력 v1

현재 구현된 출력은 scripts/run_pilot_videos.py의 영상별 detections.jsonl이다. 한 줄은 샘플링한 원본 영상 프레임 하나이며 아래 필드는 실제 코드와 일치한다.

- video: 원본 파일명
- frame_index: 원본 프레임 번호 (0부터)
- timestamp_seconds: frame_index / 원본 FPS
- detections: model, class, confidence, bbox_xyxy 목록
- model: objects 또는 ppe
- class: person, forklift, helmeted_head, no_helmet_head
- bbox_xyxy: 원본 해상도의 [왼쪽, 위쪽, 오른쪽, 아래쪽] 픽셀
- risk_status: 현재 항상 not_evaluated

프론트/로그 담당자는 지금 이 검출 출력을 읽는 작업부터 진행할 수 있다. no_helmet_head는 머리 검출 클래스이며 작업자 전체의 미착용 이벤트와 같지 않다. 두 모델 결과에 같은 사람이 중복 나타날 수 있고 아직 track_id가 없다.

## 다음 이벤트 형식 (아직 미구현)
검출과 이벤트를 분리한다. severity는 SAFE / WARNING / CRITICAL의 3종으로 유지하며 판단 불가 시 null, observation_status는 unconfirmed로 전달한다. 검출 목록이 비었다고 SAFE 이벤트를 만들지 않는다.

예정 필드: schema_version, event_id, camera_id, video, timestamp_seconds, event_type, severity, observation_status, track_ids, evidence, model_version, config_version.

- event_type: proximity / zone_intrusion / zone_dwell / ppe / status
- evidence: 원본 bbox, ROI ID, 측정 방식, 단위, 기준값, 실제 측정값 등
- 거리: 카메라 보정 전에는 픽셀 또는 정규화 거리라고 명시한다. 이를 미터/법정 작업반경으로 표시하지 않는다.
- 체류: 영상 timestamp 기준으로 계산한다. 3초 이하는 SAFE, 3초 초과 8초 미만은 WARNING, 8초 이상 CRITICAL로 연속 구간을 정의할 예정이다. 사용자 기준의 7~8초 사이도 공백 없이 WARNING으로 처리한다.
- 장면 전환, 추적 끊김, ROI 변경 시 체류 상태 초기화 또는 미확인 처리 필요.
- PPE: person과 head 연결, 상반된 head 클래스 충돌, 가림, 시간적 안정성 처리 후 이벤트를 만든다.

위 이벤트 스키마는 팀 협업 초안이며 이번 시험에서 위험 감지 기능이 구현·검증됐다는 뜻은 아니다.
