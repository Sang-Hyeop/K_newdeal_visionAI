# 현재 실행 및 후속 학습 코드

프로젝트 최상위에서 `python handoff.py run --video 1`처럼 실행합니다. 원본·설정·실행 번호는 모두 1~5입니다.

- `run_demo_scenarios.py`: 1·3·4·5번 공통 구현. 기능 구성은 configs/demo-scenarios.json을 따릅니다.
- `run_intrusion_review.py`: 2번 사람 탐지·ROI 침범·안전모 PPE.
- `recover_vehicle_cache.py`, `review_vehicle_recovery_cache.py`: 5번 신규 추론 시 차량 복구 및 검수.
- `setup_runtime.py`: 현재 모델·리뷰·로그 설치. 제외된 구 비교 결과는 복원하지 않습니다.
- `compare_ppe_video1.py`: 1577장 PPE 후보 모델의 후속 비교 도구. 현재 발표 모델은 자동 교체하지 않습니다. 기존 비교 결과와 함께 보존하며, 기능별 출력 분리 이후 비교 입력의 PPE 관측 유무 확인이 필요합니다.
- `train_ppe_expansion.py`: 1577장 확장 학습 재현 및 분할·라벨 검증. 기존 실행 폴더를 덮어쓰지 않습니다.
- `prepare_full_scene_expansion.py`: 수동 정답과 설비 오라벨 회귀 검증 원천. 일반 실행 대상은 아닙니다.
- `inventory_backend_logs.py`: 현재 이벤트/관측 로그 인계용 목록 점검.

공통 라이브러리는 src/, 회귀 검증은 tests/에 있습니다. 위 파일은 모두 현재 실행 또는 후속 작업에서 필요합니다.
