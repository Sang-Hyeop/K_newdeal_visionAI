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

## 다음 공통 이벤트 형식 (통합 미완료)

구역 체류·접근/침범·근접의 개별 실행기는 현재 `events.jsonl`과 `observations.jsonl`을 출력한다. 아래 내용은 이 결과를 팀 로그·대시보드에서 공통으로 받기 위한 통합 초안이며, 모든 기능이 같은 스키마로 연결된 상태는 아니다. 최신 인계 상태는 `docs/handoff-2026-10-06.md`를 참고한다.
검출과 이벤트를 분리한다. severity는 SAFE / WARNING / CRITICAL의 3종으로 유지하며 판단 불가 시 null, observation_status는 unconfirmed로 전달한다. 검출 목록이 비었다고 SAFE 이벤트를 만들지 않는다.

예정 필드: schema_version, event_id, camera_id, video, timestamp_seconds, event_type, severity, observation_status, track_ids, evidence, model_version, config_version.

- event_type: proximity / zone_intrusion / zone_dwell / ppe / status
- evidence: 원본 bbox, ROI ID, 측정 방식, 단위, 기준값, 실제 측정값 등
- 거리: 카메라 보정 전에는 픽셀 또는 정규화 거리라고 명시한다. 이를 미터/법정 작업반경으로 표시하지 않는다.
- 체류: 영상 timestamp 기준으로 계산한다. 3초 이하는 SAFE, 3초 초과 8초 미만은 WARNING, 8초 이상 CRITICAL로 연속 구간을 정의할 예정이다. 사용자 기준의 7~8초 사이도 공백 없이 WARNING으로 처리한다.
- 장면 전환, 추적 끊김, ROI 변경 시 체류 상태 초기화 또는 미확인 처리 필요.
- PPE: person과 head 연결, 상반된 head 클래스 충돌, 가림, 시간적 안정성 처리 후 이벤트를 만든다.

위 이벤트 스키마는 팀 협업 초안이며 이번 시험에서 위험 감지 기능이 구현·검증됐다는 뜻은 아니다.

## 실제 연결된 공통 출력 v1 (2026-10-07)

근접 실행기와 구역 접근·체류 실행기는 이제 `events_v1.jsonl`(상태 전환 로그) 및 `observations_v1.jsonl`(현재 프레임 관측)을 출력한다. 예전 `events.jsonl`/`observations.jsonl`은 개별 기능 형식으로 함께 보존한다. PPE 공통 출력은 아직 연결하지 않았다.

공통 이벤트의 구현 필드: schema_version=1.0, event_id, camera_id, video, source_sha256, timestamp_seconds, event_type, severity, observation_status, track_ids, evidence, model_version(가중치SHA256), config_version(설정SHA256), scope. event_id는 동일 입력·버전·내용의 재실행 시 동일하며 백엔드 중복 저장 방지에 사용할 수 있다.

- event_type: proximity / zone_access / zone_dwell / status.
- zone_access의 evidence.region은 outside / approach / inside / unknown이다. entry_observed/exit_observed로 실제 관측된 경계 통과를 구별한다. 영상만으로 접근 권한이나 무단 여부를 판단하지 않는다.
- 근접 evidence: image_gap_pixels, normalized_image_gap, distance_unit, distance_meters=null, person/forklift ID와 지면 대리 박스. 고정 ROI는 사용하지 않는다.
- 구역 evidence: roi_id, inside, observed_dwell_seconds 또는 signed_distance_pixels 등. 3초 이하/3초 초과~8초 미만/8초 이상이 SAFE/WARNING/CRITICAL이다.
- observation_status=unconfirmed면 severity는 반드시 null이다. 대상이 없는 프레임도 SAFE를 생성하지 않는다.
- 상태 배너는 최신 observations_v1의 해당 기능·대상 상태로 갱신한다. 전환 로그의 마지막 SAFE를 대상 누락 이후에도 유지하면 안 된다. 전체 현장 안전을 선언하지 않는다.
- 구역 침범이 CRITICAL이고 체류가 SAFE인 경우 서로 다른 기능의 판정이다. 대시보드는 체류SAFE로 침범CRITICAL을 덮어쓰면 안 된다.

팀 검사용 실제 영상 출력 위치: outputs/diagnostics/events_separated_v1/{forward,reverse,zone}. 현재 시연용 개발 출력이며 알림 개수는 정확도 지표가 아니다.
