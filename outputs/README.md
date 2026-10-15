# 현재 결과

- reviews/: 확정 리뷰 MP4 5개만 보관합니다.
- events/presentation1~5/: 확정 리뷰와 같은 버전의 전체 이벤트·관측 JSONL.
- diagnostics/: 확정 결과와 재실행에 필요한 실제 검출 캐시. 별도 실행 대상이 아닙니다.
- backend/: 위 로그의 조회용 SQLite DB.
- handoff_runs/: 새 실행 결과. 검수 전이며 확정 리뷰를 대체하지 않습니다.
- runtime/: 실행 도중 라이브러리가 만드는 설정/캐시.

`python handoff.py list`로 현재 영상별 경로를 확인합니다. 대체된 5번 거리 비교와 미채택 63장 PPE 비교 출력은 삭제했습니다. `diagnostics/ppe_compare_expanded1577_2026-10-15/`는 후속 후보 모델 판단에 필요해 보존합니다. 최신 파일 이름과 연결 기준은 configs/team-runtime-index.json입니다.

현재 diagnostics의 하위 video 번호는 발표 번호입니다. JSON과 Python 실행 번호도 모두 1~5입니다. 설치 시 Release의 과거 경로를 자동 변환합니다.
