# 현재 실행 코드

사용자는 `python handoff.py run --video N`만 실행합니다. 전체 결과는 기존 outputs/reviews/와 events/presentationN/을 갱신합니다.

- run_demo_scenarios.py: 1·3·4·5번의 현재 공통 실행.
- run_intrusion_review.py: 2번 ROI 침범·안전모 PPE.
- recover_vehicle_cache.py, review_vehicle_recovery_cache.py: 5번 신규 추론의 차량 복구 단계. 임시 폴더는 완료 후 제거합니다.
- setup_runtime.py: 공개 배포 자료 설치.
- prepare_full_scene_expansion.py: 수동 정답·설비 오라벨 회귀 검증 원천.
- inventory_backend_logs.py: 현재 로그 인계 목록 점검.

PPE의 실제 구현은 src/ppe_runtime.py입니다. 별도 비교 실행기와 실패한 후보 전용 학습 실행기는 삭제했습니다.
