# 백엔드·이벤트 로그 검토 (2026-10-14)

브랜치: `feat/backend-event-log-review`  
환경: `safety` / Python 3.11.16  
평가 항목: 4(연동 흐름), 5(조회), 8(문서·인계). 모델 학습·임계값·ROI·재추론은 하지 않음.

## 처리 흐름

입력 JSONL → 유효성 검사 → 정규화 → SQLite 저장 → API 조회

## 문서·코드 대조

| 주제 | 최신 코드/README | 과거 초안 주의 |
| --- | --- | --- |
| 공통 로그 파일 | `events_v1.jsonl`, `observations_v1.jsonl` (+ `*.head.jsonl`) | `detections.jsonl` / 구 `events.jsonl`은 전환 이벤트로 취급하지 않음 |
| event_type | `proximity` / `zone_access` / `zone_dwell` / `ppe` / `status` | 초안의 `zone_intrusion` 명칭은 현재 계약이 아님 |
| 전체 로그 건수 | 이벤트 6,139 / 관측 4,142 (`outputs/events/presentation1~5`) | quickstart·인계 숫자와 일치 |
| `source_sha256`·`scope` 등 | 있으면 `payload`에 보존, 없으면 채우지 않음 | 초안 필수 나열과 달리 백엔드 필수 검증 대상은 아님 |

## 입력 로그 요약

상세 해시·카메라·시각 범위: `outputs/backend/cursor_log_inventory.json`  
생성: `python scripts/inventory_backend_logs.py`

발표용 전체 로그(`outputs/events/`):

- 파일 24개 (이벤트 12 + 관측 12)
- 이벤트 6,139 / 관측 4,142
- 원본 JSONL은 수정·이동하지 않음

샘플(`backend_v1/samples/`): 시나리오 5개 × head JSONL 각 8행.

## 코드 개선

`backend_v1/backend.py`:

- 가져오기 결과: `ok`, `files`, `read`, `inserted`, `duplicates`, `conflicts`, `conflict_ids`
- 동일 `event_id`·다른 정규화 내용 → 충돌로 집계, 최초 행 유지
- 이벤트 중복은 정규화 payload 동등성(키 순서 무시)
- 관측 id = 원본 줄 UTF-8 SHA-256 (공백/키 순서만 다르면 새 id)
- 오류: `path:line: error_type=...; field=...; message` (원본 행 전체 비노출)
- 실패 시 트랜잭션 롤백, 종료 코드 1
- `observation_status` 허용값 검사 강화

테스트(`backend_v1/test_backend.py`): 기존 8 + 충돌/공백중복/정렬·시간경계 등 → **11개 통과**.

## 검증 DB·API

| 항목 | 값 |
| --- | --- |
| 검증 DB | `outputs/backend/cursor_review.sqlite3` |
| 기존 DB | `outputs/backend/full_review.sqlite3` 보존(미수정) |
| 1차 가져오기 | inserted events 6139 / observations 4142, conflicts 0 |
| 2차 가져오기 | inserted 0, duplicates events 6139 / observations 4142 |
| 서버 | `python backend_v1/backend.py --samples outputs/events --db outputs/backend/cursor_review.sqlite3 --port 8010` |
| 주소 | `http://127.0.0.1:8010` |

스모크: `/events?limit=5` total=6139, `/events?severity=null` total=4667, `/feature-status` count=12·`global_safety_status=not_evaluated`, 상세·video 필터·404/400 확인.

## 보존·범위

수정하지 않음: `models/`, `data/videos/`, `outputs/events/` 원본, `outputs/reviews/`, `full_review.sqlite3`.  
미구현(별도 작업): 실시간 CCTV 수신, WebSocket, 알림, 외부 공개, 인증/CORS.

## 변경 파일

- `backend_v1/backend.py`
- `backend_v1/test_backend.py`
- `backend_v1/README.md`
- `backend_v1/API_SPEC.md`
- `scripts/inventory_backend_logs.py`
- `docs/progress-backend-event-log-review-2026-10-14.md`

## 남은 항목

- Windows에서 장시간 API 부하·동시 클라이언트는 측정하지 않음
- 관측 줄의 공백/키 순서 차이로 생기는 추가 row는 계약상 새 id이며, 의미 중복 병합은 하지 않음
- 원격 push / main 병합은 이번 요청 범위 밖
