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

근접 실행기와 구역 접근·체류 실행기는 이제 `events_v1.jsonl`(상태 전환 로그) 및 `observations_v1.jsonl`(현재 프레임 관측)을 출력한다. 예전 `events.jsonl`/`observations.jsonl`은 개별 기능 형식으로 함께 보존한다. PPE도 아래 후속 단계에서 공통 출력에 연결했다.

공통 이벤트의 구현 필드: schema_version=1.0, event_id, camera_id, video, source_sha256, timestamp_seconds, event_type, severity, observation_status, track_ids, evidence, model_version(가중치SHA256), config_version(설정SHA256), scope. event_id는 동일 입력·버전·내용의 재실행 시 동일하며 백엔드 중복 저장 방지에 사용할 수 있다.

- event_type: proximity / zone_access / zone_dwell / status.
- zone_access의 evidence.region은 outside / approach / inside / unknown이다. entry_observed/exit_observed로 실제 관측된 경계 통과를 구별한다. 영상만으로 접근 권한이나 무단 여부를 판단하지 않는다.
- 근접 evidence: image_gap_pixels, normalized_image_gap, distance_unit, distance_meters=null, person/forklift ID와 지면 대리 박스. 고정 ROI는 사용하지 않는다.
- 구역 evidence: roi_id, inside, observed_dwell_seconds 또는 signed_distance_pixels 등. 3초 이하/3초 초과~8초 미만/8초 이상이 SAFE/WARNING/CRITICAL이다.
- observation_status=unconfirmed면 severity는 반드시 null이다. 대상이 없는 프레임도 SAFE를 생성하지 않는다.
- 상태 배너는 최신 observations_v1의 해당 기능·대상 상태로 갱신한다. 전환 로그의 마지막 SAFE를 대상 누락 이후에도 유지하면 안 된다. 전체 현장 안전을 선언하지 않는다.
- 구역 침범이 CRITICAL이고 체류가 SAFE인 경우 서로 다른 기능의 판정이다. 대시보드는 체류SAFE로 침범CRITICAL을 덮어쓰면 안 된다.

팀 검사용 실제 영상 출력 위치: outputs/diagnostics/events_separated_v1/{forward,reverse,zone}. 현재 시연용 개발 출력이며 알림 개수는 정확도 지표가 아니다.

## PPE 연결 및 상태 배너 (2026-10-07 후속)

`validate_tracked_ppe.py`도 동일 공통출력을 생성한다. event_type=ppe가 추가됐으며 model_version은 사람 모델과PPE모델의 해시를 합친 버전이다. evidence에 ppe_state, 사람박스, 머리 후보, 이유, violation_status가 포함된다.

PPE는 신뢰도0.5 이상 같은 종류 머리 근거가3개 연속 관측이면서0.4초 이상 이어져야 상태를 확정한다. 착용근거는SAFE, 미착용후보는WARNING(검토 필요), 누락·충돌·미확정은null이다. 후드·가림을 고려해 미착용 후보를 검증된 위반으로 격상하지 않는다. 누락·장면 전환 시 확인을 새로 시작한다.

관측파일의 feature_status는 기능별 배너용 집계다. CRITICAL > WARNING을 유지하고, 위험·주의가 없더라도 미확인 대상이 섞이면SAFE로 만들지 않는다. 대상이 없는 경우UNKNOWN이다. coverage와unknown_event_count를 함께 표시한다. 이 상태도 전체 현장 안전이나 검출 정확도를 보증하지 않는다.

5/6번 실제 영상에서 미착용 주의는0개였다. 안전모가 없는 실제 사람도 있어 미착용 감지 성공으로 보고하지 않는다. 공통 출력 연결과 검출 성능 완료는 구분한다.

## 2026-10-07 확정: 지게차 통로 조건부 감시
- 왼쪽 기계 작업영역과 초록색 보행로는 허용구역이다. 중앙 노란선 사이만 통로 ROI로 수정했다. 사람의 바닥 기준점이 통로 내부이고 지게차가 검출되지 않으면 체류시간과 관계없이 WARNING이다. 지게차가 같은 통로에 관측되면 CRITICAL이다.
- 지게차 미검출은 부재 증명이 아니다. 관측된 차량이 사라지면 1초 동안 최근 위험을 유지하며 vehicle_observation_status=unconfirmed와 마지막 관측 경과시간을 기록한다. 이후 UNKNOWN으로 전환하고 같은 차량의 관측된 이탈 또는 장면 초기화로 해제한다. ID 변경/가림은 미확인을 지속시킬 수 있다.
- dwell_time_band는 기존 3초/8초 체류 구간을 보존하는 근거이며 최종 severity와 다르다. 8초 이상이어도 차량이 검출되지 않으면 WARNING이다. 통로 밖 SAFE는 해당 구역 판정만 뜻하며 전체 안전이 아니다. 운전자 포함 가능성·잘린 차량은 미확인 처리한다. 근접은 계속 full_frame, 거리 단위는 image_plane이다.
- 4번 영상 92샘플 검증: 통로 작업자 최대 관측 체류 14.598초, WARNING 유지, 16.266초 이탈. 왼쪽 작업자와 초록색 보행로는 통로 밖. 실제 영상의 차량 존재 CRITICAL은 아직 검증하지 못했고 자동 테스트로 확인했다. 설비→사람 오탐과 안전모 미착용/후진 지게차 미탐은 남는다.
- 자동 테스트 54개 통과. 신규 학습 없이 v16 유지. 이전 넓은 기계영역 ROI 결과는 역사적 결과이며 현재 시연 기준이 아니다. 다음은 기능 확대보다 실제 미탐과 차량 존재 구간 검증을 우선한다.
