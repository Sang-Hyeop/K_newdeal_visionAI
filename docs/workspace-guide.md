# workspace 사용 안내 — 2026-10-14

## 시작점
현재 최종 발표는 기능별4개와 종합1개, 총5개 영상 구성이다. 발표 번호와 기존 내부 실행 번호는 다르다. 발표 1/3/4/5는 내부 2/5/4/7이며, 발표 2번 ROI는 별도 실행기를 쓴다. 현재 원본 메타데이터는 configs/demo-videos.json, 실행 예시는 docs/progress-2026-10-14.md를 확인한다.

- 프로젝트 기준: docs/detection-goal.md
- 이전 시연 기준과 최신 변경: docs/demo-feature-show-plan-2026-10-07.md
- 최신 종합 리뷰 규칙: docs/video7-batch-review-2026-10-13.md
- 이번 정리 내역: docs/cleanup-2026-10-14.md
- 팀 연동: docs/team-integration-pack-2026-10-07.md
- 스크립트 용도: scripts/README.md

## 폴더 역할
- src/: 실제 감지·추적·판정·이벤트·표시 구현.
- scripts/: 실행·학습·검수·평가 도구. 과거 도구를 모두 실행할 필요는 없다.
- configs/: 실행 및 카메라 설정. review/는 학습·검수 프로토콜.
- tests/: 판정·이벤트 회귀 검사.
- docs/: 기준·인계·진행 기록. history/는 과거 자료, checkpoints/는 저장 증거.
- data/: 입력 영상과 학습·검수 자료. 오래된 폴더도 현재 학습목록이 참조하므로 임의 삭제하지 않는다.
- models/: 최종/기준/비교 가중치. configs의 기본 모델과 카메라별 검수 조합은 구분한다.
- outputs/reviews/: 최신 재생용 리뷰 영상.
- outputs/diagnostics/: 최신 검출 로그·재처리 캐시·필요한 비교 자료.
- outputs/presentation/: 발표용 사진.
- outputs/handoff/: 팀 연동 자료.
- outputs/training/: 학습 결과·평가 요약. models 보존본과 동일한 가중치 복사본은 정리했다.
- outputs/checkpoints/: 중요 복구 자료. 10/13 설비 오라벨 수정 전 라벨도 보존한다.
- _local_archive/: 과거 복구 자료. 현재 변경 중인 원본의 유일한 백업은 삭제하지 않았다.

## 최신 결과 찾기

아래 번호는 최종 발표 1~5번이다. 모두 workspace의 outputs/reviews/에 보관한다.

- 1번: outputs/reviews/1_forklift_worker_collision_risk_latest.mp4
- 2번: outputs/reviews/2_restricted_zone_intrusion_latest.mp4
- 3번: outputs/reviews/3_PPE_Helmet_latest.mp4
- 4번: outputs/reviews/4_hazard_zone_dwell_worker_fixed.mp4
- 5번: outputs/reviews/5_Logistics_Warehouse_vehicle_rider_review_v2.mp4

5번 최신 실행 로그는 outputs/diagnostics/presentation5_vehicle_rider_review_v2_2026-10-14/video7/이다. `video7`은 기존 내부 번호다. 이전 리뷰와 latest 파일을 혼동하지 않도록 docs/progress-2026-10-14.md의 현재 결과를 우선한다. 모델·생성 결과는 Git 제외이며 원본 MP4 5개와 코드·설정·검증 기록을 Git으로 공유한다.

## 현재 모델과 실행 구조
- 기존 통합 진입점: scripts/run_demo_scenarios.py
- 객체 기본: configs/demo-object-model.json
- 카메라별 보완: configs/video1-object-review.json ~ video7-object-review.json
- 최종 PPE: configs/ppe-final-model.json, src/ppe_final_detector.py
- 최종 PPE 가중치: models/ppe_final/ppe_helmet_v6_960.pt
- 기본 PPE/후드 옵션: configs/demo-ppe-model.json, configs/demo-hood-model.json

Python은 /opt/anaconda3/envs/safety/bin/python을 사용한다. 미확인은 정상으로 바꾸지 않는다. 화면상 거리에는 보정 없는 미터 값을 넣지 않는다.
