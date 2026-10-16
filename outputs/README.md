# 현재 결과

- reviews/: 영상별 최신 결과 1개씩, 총 5개.
- events/presentation1~5/: 최신 영상과 일치하는 이벤트·관측.
- diagnostics/: 영상별 현재 재현 캐시 하나씩. 변경 이력을 쌓는 폴더가 아닙니다.
- backend/full_review.sqlite3: 현재 로그 전체를 재구성한 조회 DB.
- runtime/: 실행 중 임시 파일과 영상별 단일 짧은 미리보기. 전체 실행의 임시 폴더는 제거됩니다.

`python handoff.py run --video N`은 전체 실행 성공 후 현재 결과를 갱신합니다. 최신 MP4는 모두 *_latest.mp4입니다. PPE 비교·확대·추적 실험 폴더와 별도 5번 복구 캐시·handoff_runs는 삭제하고 필요한 관측을 현재 캐시에 통합했습니다. raw 검출/PPE 입력과 최종 이벤트는 현재 detections.jsonl에 함께 보관합니다.
