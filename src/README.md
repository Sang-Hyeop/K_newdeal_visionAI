# 현재 감지 공통 모듈

실행은 최상위 handoff.py → scripts 실행기 → 이 폴더의 모듈 순서입니다. 개별 모듈을 직접 실행하지 않습니다.

- 객체 검출·오탐 정리: object_recall_ensemble, detection_review_profile, equipment_reference, person_display_cleanup.
- 추적·탑승 구분: person_tracker, operator_association, vehicle_occupancy, vehicle_person_cleanup.
- 차량 복구: vehicle_recovery.
- 근접: proximity, tracked_proximity. forklift_proximity는 기존 차량쌍 이벤트·렌더링 호환과 회귀 검사에 남긴 공통 기능이며 현재 발표의 핵심 기능은 아닙니다.
- 구역·체류: zone_access, zone_dwell, lane_hazard, tracked_zone, scenario_zone.
- PPE: ppe_final_detector, ppe_person_crop, ppe_events, ppe_unassigned_heads, ppe_vehicle_guard. ppe_tiled_inference의 공통 박스 겹침 계산 등은 객체/머리 검수 모듈에서도 사용합니다.
- 이벤트·표시·번호 연결: event_contract, feature_status, observation_display, scenario_render, scenario_selection.

2026-10-15 정리에서 현재 사용하지 않는 별도 사람 소스 라우팅, 지게차 타일/전문모델 비교, 과거 PPE 앙상블·머리 재검수·후드 보조 모듈과 해당 실험 전용 테스트를 삭제했습니다. 현재 객체 앙상블에서 사용하던 IoU 계산은 값이 달라지지 않도록 해당 모듈로 옮겼습니다. 빈 dashboard/detection/events 틀도 제거했습니다.

현재 차량복구·추적·판정 임계값·학습 가중치와 전달 이벤트는 유지합니다. 과거 모듈은 Git 이력에서 확인할 수 있습니다.
