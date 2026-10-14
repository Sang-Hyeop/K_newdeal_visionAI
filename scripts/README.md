# 현재 실행 코드

사용자는 프로젝트 최상위에서 `python handoff.py run --video 1`처럼 실행합니다. `--video`는 발표 번호 1~5입니다.

- `run_demo_scenarios.py`: 발표 1·3·4·5 공통 구현. 내부 과거 번호를 사용하므로 handoff.py로 호출합니다. 기본 PPE는 현재 최종 모델입니다.
- `run_intrusion_review.py`: 발표 2 ROI 침범 구현.
- `recover_vehicle_cache.py`, `review_vehicle_recovery_cache.py`: 발표 5 새 추론 시 차량 복구 단계.
- `setup_runtime.py`: 모델·결과·로그 설치.
- `prepare_full_scene_expansion.py`: 수동 정답 데이터 준비 및 정답 회귀 테스트에서 참조하는 코드. 발표 실행기가 아닙니다.

과거 실험·비교·리뷰 실행기는 삭제했습니다. 공통 라이브러리는 src/, 검증은 tests/에 있습니다.
