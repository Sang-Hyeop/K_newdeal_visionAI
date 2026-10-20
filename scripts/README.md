# 현재 실행 코드

사용자는 `python handoff.py run --video N`만 실행합니다. 전체 결과는 기존 outputs/reviews/와 events/presentationN/을 갱신합니다.

- run_demo_scenarios.py: 1·3·4·5번의 현재 공통 실행.
- run_intrusion_review.py: 2번 ROI 침범·안전모 PPE.
- recover_vehicle_cache.py, review_vehicle_recovery_cache.py: 5번 신규 추론의 차량 복구 단계. 임시 폴더는 완료 후 제거합니다.
- setup_runtime.py: 공개 배포 자료 설치.
- prepare_full_scene_expansion.py: 수동 정답·설비 오라벨 회귀 검증 원천.
- inventory_backend_logs.py: 현재 로그 인계 목록 점검.

PPE의 실제 구현은 src/ppe_runtime.py입니다. 별도 비교 실행기와 실패한 후보 전용 학습 실행기는 삭제했습니다.


6번 주차장 화재: `python handoff.py run --video 6` (내부 `run_fire_review.py`). 현재프레임 불꽃 탐지·문맥 복구·공간/시간 확인·편집 초기화 후 기존6번 리뷰/이벤트/백엔드를 갱신합니다. 기존1~5번은 변경하지 않습니다. 상세 설정과 검증은 `configs/review/fire-current.json`입니다.

현재 handoff는 자산 SHA와 프레임 계약을 순차 읽기로 검사해 전체 진단 파일을 메모리에 올리지 않습니다. 모델·기능별 활성 범위는 그대로 유지합니다.

2026-10-20 최종 정리: 각 Python 파일에 한글 역할 설명을 추가하고 압축된 코드를 일반 들여쓰기로 정리했습니다. 공통·침범 실행기와 차량 복구·검수·로그 목록 도구의 SHA-256은 대용량 파일을 순차 읽어 계산합니다. 출력 해시·이벤트 집계·실행 인수와 현재 결과 경로는 유지합니다.
