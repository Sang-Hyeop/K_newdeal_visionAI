# 대시보드 한글 라벨 및 이벤트 로그 연동

작성일: 2026-10-14
브랜치: `feat/backend-event-log-review`
평가 항목: 5(조회·표시), 8(문서·인계)

API·JSONL의 **영문 필드명·enum은 유지**하고, 화면 표시만 한글로 매핑합니다.
기계 판독 매핑: `configs/dashboard-labels.ko.json`
표시·CSV 함수: `backend_v1/dashboard_labels.py`
JSON/CSV 계약 초안: `docs/event-log-field-contract.md` (합의 상태: 담당자 검토 대기)
말투: `backend_v1/roi-wording-2026-10-07.md` / `docs/roi-wording-2026-10-07.md`

**실제 화면(프론트엔드) 코드는 이 저장소에 없습니다.**
본 문서는 라벨표·연동 규칙·검증 기록입니다. Gradio/웹 UI에 “적용 완료”로 해석하지 않습니다.

---

## 1. API 원본 값과 화면 표시값

| 구분 | 원본(영문 유지) | 화면 |
| --- | --- | --- |
| 필터·정렬·저장 | `event_type=proximity` 등 | 사용하지 않음(원본 코드만) |
| 목록·배너·상세 문구 | JSON 그대로 수신 | `dashboard_labels.py`로 치환 |
| `severity=null` | JSON `null` | 「미확인」(SAFE로 바꾸지 않음) |
| 빈 `/events` | `events: []`, `total: 0` | 「조회 결과 없음」 |
| 관측 없음 | `feature_status: []` | 「관측 없음」(SAFE 금지) |
| 알 수 없는 enum | 원본 문자열 | 「알 수 없음 (원본값)」 |
| 감사용 | `evidence_raw_json`, `source_raw_json` | 일반 화면 숨김/접기 |

---

## 2. 1~5번 영상 매핑

출처: `configs/demo-videos.json`, `configs/team-runtime-index.json`,  
`http://127.0.0.1:8010/events?video=...` 실측 (2026-10-14).

| 발표 번호 | API `video` 값 | 화면 제목 | 이벤트 건수 | feature-status 스트림 |
| --- | --- | --- | --- | --- |
| 1 | `1_forklift_worker_collision_risk.mp4` | 1. 지게차–작업자 근접 | 145 | 2 |
| 2 | `2_restricted_zone_intrusion.mp4` | 2. 제한구역 접근 | 9 | 2 |
| 3 | `3_PPE_Helmet.mp4` | 3. 안전모(PPE) | 91 | 1 |
| 4 | `4_hazard_zone_dwell.mp4` | 4. 위험구역 체류 | 168 | 3 |
| 5 | `5_Logistics Warehouse.mp4` | 5. 물류창고 종합 | 5726 | 4 |

합계 이벤트 6,139 / 관측 4,142.  
발표 번호와 `video` 문자열은 다릅니다. 조회·필터에는 **API `video` 값**을 URL 인코딩해 사용합니다.

```powershell
$baseUrl = 'http://127.0.0.1:8010'
$video = [uri]::EscapeDataString('5_Logistics Warehouse.mp4')
Invoke-RestMethod "$baseUrl/events?video=$video&limit=5"
Invoke-RestMethod "$baseUrl/feature-status?video=$video"
```

영상마다 `timestamp_seconds` 시계가 다릅니다. 최신 배너는 `camera_id` + `feature` + `video`로 분리합니다.

---

## 3. 한글 라벨표

열: API 필드 또는 값 | 한글 표시명 | 의미 | 적용 위치 | 표시 시 주의사항

### 3.1 이벤트 종류 (`event_type` / `feature`)

| API 필드 또는 값 | 한글 표시명 | 의미 | 적용 위치 | 표시 시 주의사항 |
| --- | --- | --- | --- | --- |
| `proximity` | 지게차·작업자 근접 위험 | 화면상 사람–지게차 거리 규칙 | 목록, 필터 라벨, 배너 | 실제 충돌 발생으로 쓰지 않음. m 없음 |
| `zone_access` | 구역 접근·진입 | 시연 ROI 기준 위치 | 목록, 배너 | 무단 출입·권한 위반으로 쓰지 않음 |
| `zone_dwell` | 구역 체류 | ROI 내부 체류 관측 | 목록, 배너 | 체류 SAFE로 접근 CRITICAL을 덮지 않음 |
| `ppe` | 안전모 착용 상태 | 머리/착용 관측 | 목록, 배너 | 미착용 후보는 검토용 WARNING |
| `status` | 상태 정보 | 대상 없음 등 상태 전환 | 목록 | SAFE로 해석하지 않음 |

### 3.2 위험도·관측·배너

| API 필드 또는 값 | 한글 표시명 | 의미 | 적용 위치 | 표시 시 주의사항 |
| --- | --- | --- | --- | --- |
| `severity=SAFE` | 안전 | 해당 기능·관측 대상 규칙 결과 | 배지, 목록 | 현장 전체 안전 선언 금지 |
| `severity=WARNING` | 주의 | 주의·검토 필요 | 배지, 목록 | 미확인과 섞여도 유지 |
| `severity=CRITICAL` | 위험 | 확인된 위험 | 배지, 목록 | 미확인과 섞여도 유지 |
| `severity=null` | 미확인 | 판정 불가/미확정 | 배지, 목록 | SAFE로 변환 금지. 원인마다 `reason`·`observation_status` 확인 |
| `observation_status=confirmed` | 확인됨 | 확정 관측 | 상세, 목록 | |
| `observation_status=unconfirmed` | 미확인 | 미확정 관측 | 상세, 목록 | 이때 severity는 null |
| `display_state=UNKNOWN` | 미확인 | 배너 집계 미확인 | feature-status | 관측 없음·혼합 미확인. SAFE 금지 |
| `global_safety_status=not_evaluated` | 평가하지 않음 | 현장 전체 미평가 | 화면 고정 문구 | 항상 이 의미 유지 |

### 3.3 구역 `evidence.region`

| API 필드 또는 값 | 한글 표시명 | 의미 | 적용 위치 | 표시 시 주의사항 |
| --- | --- | --- | --- | --- |
| `evidence.region=outside` | 구역 밖 | ROI 밖 | 상세 evidence | 최상위 필드 아님 |
| `evidence.region=approach` | 구역 접근 | ROI 접근 | 상세 evidence | 계약값. 현재 발표 로그에는 outside/inside/unknown 위주 |
| `evidence.region=inside` | 구역 내부 | ROI 안 | 상세 evidence | |
| `evidence.region=unknown` | 미확인 | 위치 미확인 | 상세 evidence | |

### 3.4 공통 필드

| API 필드 또는 값 | 한글 표시명 | 의미 | 적용 위치 | 표시 시 주의사항 |
| --- | --- | --- | --- | --- |
| `camera_id` | 카메라 | 카메라/스트림 ID | 목록, 필터 | 최상위 |
| `video` | 영상 | 원본 파일명 | 목록, 필터 | 발표 번호와 별개 |
| `timestamp_seconds` | 영상 시간 | 영상 시작 기준 초 | 목록, 상세 | 상대시간만. 오늘 날짜 붙이지 않음 |
| `event_type` | 이벤트 종류 | 기능 종류 | 목록, 필터 | |
| `severity` | 위험도 | SAFE/WARNING/CRITICAL/null | 목록, 배지 | |
| `observation_status` | 관측 상태 | confirmed/unconfirmed | 목록, 상세 | |
| `track_ids` | 추적 ID | 해당 영상·카메라 내 ID | 목록, 상세 | 다른 영상과 동일 인물로 간주 금지 |
| `event_id` | 이벤트 ID | 고유 ID | 상세, 링크 | |
| `evidence.observed_dwell_seconds` | 관측 체류시간 | 체류 초 | 상세 | evidence 내부. 초 단위 |
| `evidence.roi_id` | 구역 ID | ROI 식별자 | 상세 | evidence 내부 |
| `model_version` | 모델 버전 | 가중치 해시 등 | 상세 | 최상위 |
| `config_version` | 설정 버전 | 설정 해시 | 상세 | 최상위 |
| `source_sha256` | 원본 영상 해시 | 입력 영상 해시 | 상세 | 최상위 |
| `evidence.distance_meters` | 미터 거리 | 항상 null(현재) | 상세 | 「미제공». 보정 없이 m 생성 금지 |
| `evidence.ppe_state` | PPE 세부 상태 | 착용/후보/충돌/불명 | 상세 | 아래 PPE 표 |
| `evidence.reason` | 사유 | 판정 근거 코드 | 상세 | `dashboard_labels.REASON_LABELS` |

### 3.5 PPE `evidence.ppe_state` (실제 로그 확인값)

| API 필드 또는 값 | 한글 표시명 | 의미 | 적용 위치 | 표시 시 주의사항 |
| --- | --- | --- | --- | --- |
| `helmet_detected` | 안전모 감지 | 착용 근거 | 상세 | |
| `no_helmet_candidate` | 미착용 후보 | 검토 후보 | 상세 | 확정 위반 아님 |
| `conflicting_evidence` | 근거 충돌 | 상충 | 상세 | |
| `unknown` | 불명 | 분류 불가 | 상세 | |

존재하지 않는 PPE 상태를 새로 만들지 않았습니다.

---

## 4. 시간·거리·미확인 표시 규칙

- `timestamp_seconds`: `12.5초` 형식. 벽시계/오늘 날짜 금지.
- `observed_dwell_seconds`: 초 단위 동일 포맷.
- `distance_meters`: null → 「미제공」. 값이 있어도 보정 근거 없으면 m로 확정 표시하지 않음.
- `severity=null` + `unconfirmed` → 「미확인」. 모든 null을 같은 원인으로 설명하지 않음(`reason` 확인).
- 빈 이벤트 목록 → 「조회 결과 없음」. API 오류와 구분.
- 관측 없음 → 「관측 없음」. SAFE 배너 생성 금지.
- 알 수 없는 enum → 「알 수 없음 (원본)」. 화면 중단 금지.
- 정렬·필터는 한글 문자열이 아니라 **영문 원본 값** 사용.

---

## 5. 기능별 상태 유지

- 최신 상태: `camera_id` / `feature` / `video`별 (`GET /feature-status`).
- 선택 영상의 실제 `video`로만 조회.
- 확인된 CRITICAL/WARNING은 미확인 대상이 있어도 유지.
- 다른 기능 SAFE로 WARNING/CRITICAL 덮어쓰기 금지.
- `global_safety_status=not_evaluated` 유지.
- `events_v1.jsonl`(전환)과 `observations_v1.jsonl`(프레임 관측) 역할 분리. 관측을 전환 테이블에 중복 저장하지 않음.

---

## 6. 화면 적용 위치

| 위치 | 상태 |
| --- | --- |
| 저장소 내 React/Vue/HTML 대시보드 | **없음** (검색 결과 0) |
| 표시용 매핑 모듈 | `backend_v1/dashboard_labels.py` |
| 단위 테스트 | `backend_v1/test_dashboard_labels.py` |
| 팀 인계 라벨 요약 | `backend_v1/dashboard-labels-ko.md` → 본 문서 참조 |
| API 서버 | `http://127.0.0.1:8010` (`outputs/backend/full_review.sqlite3`) |

향후 프론트엔드를 붙일 때: API 응답은 영문 유지, 렌더 직전에 `dashboard_labels` 함수 사용.

---

## 7. API 조회 예시

```powershell
$baseUrl = 'http://127.0.0.1:8010'
$page = Invoke-RestMethod "$baseUrl/events?limit=5"
Invoke-RestMethod "$baseUrl/feature-status"
Invoke-RestMethod "$baseUrl/events?severity=null&limit=5"
if ($page.events.Count -gt 0) {
  $encodedEventId = [uri]::EscapeDataString([string]$page.events[0].event_id)
  Invoke-RestMethod "$baseUrl/events/$encodedEventId"
}
```

서버 시작(기존 DB 보존):

```powershell
python handoff.py backend --port 8010
# 또는
python backend_v1/backend.py --samples outputs/events --db outputs/backend/full_review.sqlite3 --port 8010
```

---

## 8. 테스트 결과 (2026-10-14)

| 항목 | 결과 |
| --- | --- |
| `python -m unittest discover -s backend_v1 -p "test_dashboard_labels.py" -v` | 10개 OK |
| `python -m unittest discover -s backend_v1 -p "test_backend.py" -v` | 11개 OK |
| API 1~5 `video` 필터 | 145 / 9 / 91 / 168 / 5726 |
| `feature-status` | count=12, `global_safety_status=not_evaluated` |
| `severity=null` | total=4667 |
| 상세 `event_id` | 조회 성공 |
| 프론트 lint/build | 해당 없음(화면 코드 없음) |

원본 `outputs/events` JSONL·기존 SQLite·모델·결과 영상은 수정하지 않음.

---

## 9. 남은 문제

- 대시보드 UI가 없어 브라우저 레이아웃·모바일 줄바꿈·색상 대조는 미검증.
- CORS/인증은 로컬 API 범위 그대로(추가하지 않음).
- `evidence.region=approach`는 계약·라벨에 포함, 현재 발표 로그 빈도는 outside/inside/unknown 위주.
- 원격 push·PR·main 병합은 이번 작업 범위 밖.
