# workspace 사용 안내 — 2026-10-14

## 시작점
현재 최종 발표는 기능별4개와 종합1개, 총5개 영상 구성이다. 실행 설정은 아직 과거1~7번 체계이므로 파일명만 보고 예전 실행 명령을 바로 쓰지 않는다. 번호·입력·ROI 갱신은 다음 단계다.

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
- 4번 이전 통로 리뷰: outputs/diagnostics/video4_batch_review_v9/video4/demo.mp4
- 5번 이전 PPE 리뷰: outputs/reviews/video5_review_final_2026-10-13.mp4
- 7번 이전 종합 최신 보완: outputs/reviews/video7_review_revised_2026-10-13.mp4
- 최신1번 로그: outputs/diagnostics/video1_proximity_safety_v4_verified/
- 최신2번 로그: outputs/diagnostics/video2_distance_review_v7/
- 최신3번 로그: outputs/diagnostics/video3_person_dedup_v5/
- 최신4번 로그: outputs/diagnostics/video4_batch_review_v9/
- 최신5번 로그: outputs/diagnostics/video5_selected_review_2026-10-13/
- 최신7번 로그: outputs/diagnostics/video7_batch_review_v7_final/

위 번호는 기존1~7번 리뷰 번호다. 현재 발표번호1~5와 혼동하지 않는다.
전기 제어실 체류 초안은 메인 채팅 outputs에 있으며 workspace 통합 전이다.

## 현재 모델과 실행 구조
- 기존 통합 진입점: scripts/run_demo_scenarios.py
- 객체 기본: configs/demo-object-model.json
- 카메라별 보완: configs/video1-object-review.json ~ video7-object-review.json
- 최종 PPE: configs/ppe-final-model.json, src/ppe_final_detector.py
- 최종 PPE 가중치: models/ppe_final/ppe_helmet_v6_960.pt
- 기본 PPE/후드 옵션: configs/demo-ppe-model.json, configs/demo-hood-model.json

Python은 /opt/anaconda3/envs/safety/bin/python을 사용한다. 미확인은 정상으로 바꾸지 않는다. 화면상 거리에는 보정 없는 미터 값을 넣지 않는다.
