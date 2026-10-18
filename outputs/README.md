# 현재 결과

- reviews/: 영상별 최신 결과 1개씩, 총 6개.
- events/presentation1~6/: 최신 영상과 일치하는 이벤트·관측.
- diagnostics/: 영상별 현재 재현 캐시 하나씩. 변경 이력을 쌓는 폴더가 아닙니다.
- backend/full_review.sqlite3: 현재 로그 전체를 재구성한 조회 DB.
- runtime/: 실행 중 임시 파일과 영상별 단일 짧은 미리보기. 전체 실행의 임시 폴더는 제거됩니다.

`python handoff.py run --video N`은 전체 실행 성공 후 현재 결과를 갱신합니다. 최신 MP4는 모두 *_latest.mp4입니다. PPE 비교·확대·추적 실험 폴더와 별도 5번 복구 캐시·handoff_runs는 삭제하고 필요한 관측을 현재 캐시에 통합했습니다. raw 검출/PPE 입력과 최종 이벤트는 현재 detections.jsonl에 함께 보관합니다.

- runtime_download/: 과거 공개 Release 설치 캐시. 최신 로컬 결과의 기준이 아니며 6번 화재를 포함하지 않습니다.
- diagnostics/forklift-current-review.jpg: 최종 지게차 선정의 오탐·미탐 비교 근거로 보존합니다.

실제 DB는 실행 시 재구성되므로 DB 바이트 해시를 모델 잠금 조건으로 쓰지 않습니다. 모델·정책 잠금과 결과 스냅샷은 configs/final-model-lock.json을 참고합니다.
