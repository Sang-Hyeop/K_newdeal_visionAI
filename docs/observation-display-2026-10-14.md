# 1번 리뷰: 미확인 원인 구분과 확대 추론 (2026-10-14)

발표 1번 입력은 `1_forklift_worker_collision_risk.mp4`이며 기존 내부 시나리오 2번 원본과 해시가 같다. 내부 번호 2는 발표 번호 1과 구분한다.

## 변경

- 해당 카메라의 최종 PPE v6에 현재 관측 사람 주변 확대 추론을 켠다. 신뢰도·연속 관측 기준은 유지한다.
- 기존 위험 판정 필드는 보존하고, `assessment_state`, `alert_eligible`, `notification_category`, `status_reason`을 이벤트에 추가한다.
- 프레임 상태에는 `dashboard_state`, `assessment_counts`, `risk_alert_count`를 추가한다.
- 판정 중(pending), 판정 불가(unassessable), 관측 소실(observation_lost), 대상 미관측(no_observed_subjects)을 분리한다. 대상 미관측은 실제 대상 부재나 현장 안전의 증명이 아니다.
- 영상 배너의 WAIT/CHECK/LOST는 각각 판정 중/판정 불가/관측 소실 수다. 확실한 미착용 관측은 NO HELMET DETECTED, 약하거나 충돌하는 근거는 CANDIDATE로 유지한다.

## 백엔드·대시보드 연결

- 이벤트 이력에는 모든 상태 전환을 저장한다. 푸시·팝업 위험 알림은 `alert_eligible == true`만 사용한다.
- `notification_category == status`는 상태 표시용이다. 카메라 장애나 지속 관측 소실의 별도 운영 알림은 팀이 따로 정한다.
- 배너는 `observations_v1.jsonl`의 `feature_status.dashboard_state`와 `assessment_counts`를 읽는다. 위험은 CRITICAL/WARNING을 우선 표시하고 다른 대상의 불확실성도 개수로 남긴다.
- 기존 `display_state`, `severity`, `observation_status`, 전체 안전 미평가 필드는 유지한다. 기존 대시보드가 UNKNOWN만 읽으면 새 표현이 자동 적용되지 않으므로 담당자가 새 필드로 연결해야 한다.
- 이 필드들은 이벤트 ID 해시에 포함되므로 이전 결과와 새 실행은 별도 실행·버전으로 보관한다.
- 현재 작업 폴더에 실제 백엔드/대시보드 구현이 없어서 감지 출력과 표시 코드까지 반영했다.

## 사용자 검수

1. 비교 영상을 보고 시간·위치·실제 상태를 적는다. 예: `8초, 오른쪽 앉은 작업자, 안전모 미착용`.
2. 머리가 가려져 알 수 없는 장면은 판정 불가로 유지한다. 직접 확인 가능한 오탐·미탐 장면만 CVAT 보강 대상으로 모은다.
3. 검수 라벨로 학습하려면 기존 수정 라벨과 함께 재학습·비교한다. 이번 단계는 재학습이 아니다.

평가 체크리스트 3·5·8(판정/알림 규칙, 이해 가능한 표시, 팀 전달)에 기여한다. 검증 수치와 결과 해시는 실행 폴더의 review_verification.json에 기록한다.

## 이번 검증 결과

전체 106개 분석 프레임에서 PPE UNKNOWN 배너는 91 → 82개, WARNING은 15 → 24개다. 신뢰도 기준 변경 없이 확대 추론으로 추가 후보를 얻었다. 이는 정확도 개선율이 아니며 사용자 검수가 필요하다. 근접 이벤트는 이전 실행과 전부 일치했다. 자동 검사 206개와 두 영상 전체 106프레임 디코딩을 통과했다. 결과·해시는 outputs/diagnostics/presentation1_assessment_final_2026-10-14/video2/review_verification.json에 저장했다.
