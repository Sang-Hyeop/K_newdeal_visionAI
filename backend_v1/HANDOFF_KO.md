# 대시보드 전달용 백엔드 v1

## 실행

Python 3.11 이상에서 추가 패키지 설치 없이 실행합니다.
이 폴더를 작업 디렉터리로 사용합니다.

```powershell
python backend.py --import-only
python -m unittest -v test_backend
python backend.py --port 8010
```

샘플 5개 폴더로 이벤트 40건, 관측 40건을 DB에 적재했습니다.
자동 테스트 8개가 통과했으며 테스트 중 실제 HTTP 서버로 3개 API를 호출했습니다.
YOLO, 학습, 영상 추론은 실행하지 않았습니다.

## 연결 규격

- 목록: `GET /events` — events, total, count, limit, offset 반환
- 상세: `GET /events/{event_id}` — 이벤트 전체 및 원문 감사 필드 반환
- 최신 배너: `GET /feature-status` — feature_status 배열 반환

목록 필터는 event_type, severity, camera_id, video, start_seconds,
end_seconds, limit, offset입니다. `severity=null`은 미확인 이벤트를 조회합니다.
시간 구간은 영상 시작 기준 초 단위이며 양 끝을 포함합니다.
최신 배너 필터는 camera_id, feature, video입니다.
카메라·기능·영상 조합마다 최신 관측을 반환하므로 대시보드에서 활성 영상을 선택하세요.
데이터가 없는 기능은 결과에 없으며 SAFE 배너를 만들지 않습니다.

## 보존 규칙

SQLite DB는 `data/backend.sqlite3`에 있습니다.
event_id는 PRIMARY KEY로 UNIQUE이고 severity는 NULL을 허용합니다.
unconfirmed 이벤트의 severity는 NULL로 정규화하며 DB CHECK도 적용했습니다.
동일 ID 재적재는 첫 데이터를 유지하고 추가 저장하지 않습니다.
JSONL 오류는 파일명·줄 번호와 함께 보고하고 적재 전체를 롤백합니다.

evidence JSON 컬럼에는 입력 JSON 값을 공백과 숫자 표현까지 그대로 보존합니다.
raw_json은 입력 한 줄 전체를 보존합니다. 상세 응답의 evidence_raw_json,
source_raw_json은 감사용 원문입니다. 화면에는 정규화된 evidence를 사용하세요.
정규화 데이터의 distance_meters는 항상 null입니다.
빈 관측은 SAFE가 되지 않고, 미확인 대상이 섞이면 SAFE 승격을 막습니다.
CRITICAL > WARNING 경고는 유지하고 기능별 상태를 별도로 반환합니다.
global_safety_status는 not_evaluated로 유지합니다.
PPE의 confirmed WARNING 검토 후보는 classification_status=unconfirmed여도
지우지 않고 vehicle_overlap_review_required 등 근거를 그대로 전달합니다.

## 자료 위치 및 범위

요청한 새파일 프로젝트에는 10월 7일 자료가 없어, 옆의
`시선_팀프로젝트_공유본/docs/team-integration-pack-2026-10-07.md`와
`docs/team-samples/2026-10-07/`를 기준으로 구현했습니다.
샘플 사본은 이 폴더의 samples에 포함되어 독립 실행할 수 있습니다.
문서의 모델 실행 명령은 실행하지 않았습니다.

현재 API는 로컬 Python 표준 HTTP 서버입니다. 인증과 브라우저 CORS는
구현하지 않았습니다. Gradio의 서버 측 Python에서는 바로 호출할 수 있습니다.
기존 src/api.py의 구형 API와 별도이며 실행 진입점은 backend.py입니다.

## 대시보드 전달 파일

API 상세 규격은 API_SPEC.md입니다. responses 폴더에는 실제 HTTP로 조회한
근접·zone·PPE 목록 예시와 이벤트 상세, 최신 배너 예시가 있습니다.
원본 문구 규칙은 roi-wording-2026-10-07.md에 동봉했습니다.
화면용 한글 라벨·연동 규칙은 ../docs/dashboard-ko-labels.md 와
dashboard_labels.py 입니다. 요약은 dashboard-labels-ko.md 입니다.
대시보드 AI에는 API_SPEC.md, roi-wording-2026-10-07.md,
docs/dashboard-ko-labels.md를 함께 전달하세요.
ROI는 evidence 다각형 또는 별도로 전달한 summary.json의 camera_config로
대시보드가 직접 fill합니다. SAFE 초록, WARNING 주황, CRITICAL 빨강이며
알파 기본값은 약 0.15 / 0.2입니다. 좌표가 없으면 임의로 만들지 않습니다.
