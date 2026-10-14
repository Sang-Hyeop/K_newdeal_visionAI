# 이벤트 로그 JSON/CSV 필드 계약 초안

| 항목 | 내용 |
| --- | --- |
| 합의 상태 | **담당자 검토 대기** (승인 전 초안) |
| 승인자 | _(미기입)_ |
| 승인일 | _(미기입)_ |
| 라벨 매핑 | `configs/dashboard-labels.ko.json` |
| 표시 함수 | `backend_v1/dashboard_labels.py` |
| 한글 라벨 설명 | `docs/dashboard-ko-labels.md` |

API 영문 필드·enum은 변경하지 않습니다. 한글은 표시/내보내기 계층만 사용합니다.

---

## 1. 문서·구현 차이 메모

| 주제 | 실제 구현/로그 | 초안·주의 |
| --- | --- | --- |
| `event_type` | 백엔드 허용: proximity, zone_access, zone_dwell, ppe, status | `forklift_proximity`는 생성기 별칭일 수 있으나 **ingest 미지원** |
| `evidence.region` | 계약: outside/approach/inside/unknown | 발표 1~5 로그 실측: outside/inside/unknown (approach 희박·없음) |
| `camera_id` | demo-video2/4/5/7, presentation2-robot-intrusion | demo-video 번호 ≠ 발표 번호 |
| 운영 상태(조치 완료 등) | API에 없음 | 새로 만들지 않음 |

---

## 2. JSON 규칙

- UTF-8, BOM 없음
- 필드명·enum 영문 유지
- `evidence`는 객체, `track_ids`는 배열
- 일반 표시: 정규화 `evidence` / `payload`
- 감사: `evidence_raw_json`, `source_raw_json` (일반 화면과 분리)
- `severity=null`은 JSON null 유지 → 표시만 「미확인」
- `distance_meters`는 보정 없이 생성하지 않음(현재 null)

표시용 래퍼 JSON(`dashboard_display_v1`)은 원본 옆에 `*_label` 필드를 **추가**한 사본이며 API 계약을 대체하지 않습니다.

---

## 3. 컬럼 정의표 (이벤트)

| 영문 필드명 | 한글 표시명 | JSON 원본 경로 | 자료형 | 필수 | null 허용 | 단위 | 설명 | 예시 | CSV 변환 규칙 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| schema_version | 스키마 버전 | `$.schema_version` | string | Y | N | - | 계약 버전 | `1.0` | 문자열 그대로 |
| event_id | 이벤트 ID | `$.event_id` | string | Y | N | - | 고유 ID | `e998…` | 문자열 |
| camera_id | 카메라 ID | `$.camera_id` | string | Y | N | - | 스트림 ID | `demo-video7` | 원본 + `camera_label` 표시 컬럼 |
| video | 영상 | `$.video` | string | Y | N | - | 원본 파일명 | `5_Logistics Warehouse.mp4` | 원본 + `video_label` |
| source_sha256 | 원본 영상 해시 | `$.source_sha256` | string | N* | Y | - | 입력 해시 | `4f8e…` | 문자열; 없으면 빈칸 |
| timestamp_seconds | 영상 시간 | `$.timestamp_seconds` | number | Y | N | 초(상대) | 영상 시작 기준. 날짜 아님 | `12.5` | **숫자 유지** |
| event_type | 이벤트 유형 | `$.event_type` | string enum | Y | N | - | 기능 종류 | `proximity` | 원본 + `event_type_label` |
| severity | 심각도 | `$.severity` | string\|null | Y | Y | - | SAFE/WARNING/CRITICAL/null | `null` | null→빈칸; 라벨은 `severity_label` |
| observation_status | 관측 상태 | `$.observation_status` | string enum | Y | N | - | confirmed/unconfirmed | `unconfirmed` | 원본 + 라벨 컬럼 |
| assessment_state | 판정 상태 | `$.assessment_state` | string enum | N* | Y | - | observation_display 결과 | `pending` | 원본 + 라벨 |
| alert_eligible | 위험 알림 대상 여부 | `$.alert_eligible` | boolean | N* | Y | - | WARNING/CRITICAL 확정 시 true | `true` | `true`/`false`/빈칸 |
| notification_category | 알림 분류 | `$.notification_category` | string | N* | Y | - | risk/status | `status` | 원본 + 라벨 |
| status_reason | 상태 사유 | `$.status_reason` | string | N* | Y | - | 사유 코드 | `pending_temporal_confirmation` | 문자열 |
| track_ids | 추적 ID | `$.track_ids` | string[] | N* | Y | - | 해당 영상·카메라 한정 | `["P0:1"]` | JSON 배열 문자열 |
| evidence | 판정 근거 | `$.evidence` | object | Y | N | - | 기능별 근거 | `{…}` | JSON 객체 문자열 |
| model_version | 모델 버전 | `$.model_version` | string | N* | Y | - | 가중치 해시 등 | `45d1…` | 문자열 |
| config_version | 설정 버전 | `$.config_version` | string | N* | Y | - | 설정 해시 | `3d2b…` | 문자열 |
| scope | 판정 범위 | `$.scope` | string | N* | Y | - | 적용 범위 문구 | `observed_subjects_…` | 문자열 |
| roi_id | 구역 ID | `$.evidence.roi_id` | string | N | Y | - | **evidence 내부** | `yellow_line_vehicle_lane` | 파생 컬럼 + `zone_label` |
| observed_dwell_seconds | 관측 체류시간 | `$.evidence.observed_dwell_seconds` | number | N | Y | 초 | **evidence 내부** | `3.2` | 숫자 또는 빈칸 |
| ppe_state | 보호구 상태 | `$.evidence.ppe_state` | string | N | Y | - | evidence 내부 | `no_helmet_candidate` | 원본 + 라벨 |
| violation_status | 위반 확인 상태 | `$.evidence.violation_status` | string | N | Y | - | evidence 내부 | `not_verified` | 원본 + 라벨(위험) |
| region | 구역 위치 | `$.evidence.region` | string | N | Y | - | evidence 내부 | `outside` | 원본 + 라벨 |
| distance_meters | 미터 거리 | `$.evidence.distance_meters` | number\|null | N | Y | m | 현재 null | `null` | 빈칸; 표시는 미제공 |

\* N*: 공통 계약상 포함되나 백엔드 최소 검증 필드는 아님. 발표 로그에는 대체로 존재.

---

## 4. CSV 규칙

### 4.1 헤더 순서 (기계 연동용 영문)

`configs/dashboard-labels.ko.json` → `csv_header_order` 와 동일:

1. schema_version  
2. event_id  
3. camera_id  
4. camera_label *(표시용)*  
5. video  
6. video_label *(표시용)*  
7. source_sha256  
8. timestamp_seconds  
9. event_type  
10. event_type_label *(표시용)*  
11. severity  
12. severity_label *(표시용)*  
13. observation_status  
14. observation_status_label *(표시용)*  
15. assessment_state  
16. assessment_state_label *(표시용)*  
17. alert_eligible  
18. notification_category  
19. notification_category_label *(표시용)*  
20. status_reason  
21. track_ids  
22. roi_id  
23. zone_label *(표시용)*  
24. observed_dwell_seconds  
25. ppe_state  
26. ppe_state_label *(표시용)*  
27. violation_status  
28. violation_status_label *(표시용)*  
29. evidence  
30. model_version  
31. config_version  
32. scope  

`*_label` 컬럼은 **API 원본 필드가 아닙니다.**

### 4.2 직렬화

| 값 | CSV 표현 |
| --- | --- |
| null | 빈 칸 (`""`) |
| 빈 문자열 | 빈 칸 (null과 구분 어려움 → JSON 병행 권장) |
| 빈 배열 `[]` | `[]` |
| 배열/객체 | `json.dumps(..., ensure_ascii=False)` 한 칸 |
| boolean | `true` / `false` (한글 치환 없음) |
| number | 숫자 문자열, 단위 문자 없음 |

- 기본 파일: **UTF-8, BOM 없음** (`write_events_csv(..., utf8_sig=False)`)
- Excel용: `utf8_sig=True` → UTF-8 with BOM (기본과 별도 옵션)
- 쉼표·따옴표·줄바꿈: Python `csv` 모듈 표준 quoting

---

## 5. 제안된 한글 표시명 (요약)

이벤트 유형·심각도·관측·판정·구역·카메라·영상·객체·PPE는  
`configs/dashboard-labels.ko.json` 및 `docs/dashboard-ko-labels.md` 참고.

주요 확정 제안:

| 코드 | 한글 |
| --- | --- |
| proximity | 지게차·작업자 근접 위험 |
| zone_access | 구역 접근·진입 |
| SAFE / WARNING / CRITICAL / null | 안전 / 주의 / 위험 / 미확인 |
| confirmed / unconfirmed | 확인됨 / 미확인 |
| not_verified | 위험 |
| no_helmet_head | 안전모 미착용 머리 (사람 전체 확정 위반 아님) |

---

## 6. 영상·카메라·구역 매핑

| 발표 | API `video` | camera_id | camera 표시명 | 대표 roi_id | zone 표시명 |
| --- | --- | --- | --- | --- | --- |
| 1 | `1_forklift_worker_collision_risk.mp4` | `demo-video2` | 1번 영상 카메라 | (근접 ROI 없음) | - |
| 2 | `2_restricted_zone_intrusion.mp4` | `presentation2-robot-intrusion` | 2번 영상 카메라 | `robot-red-floor` | 로봇 작업구역(시연 ROI) |
| 3 | `3_PPE_Helmet.mp4` | `demo-video5` | 3번 영상 카메라 | - | - |
| 4 | `4_hazard_zone_dwell.mp4` | `demo-video4` | 4번 영상 카메라 | `yellow_line_vehicle_lane` | 안전 통로(시연 ROI) |
| 5 | `5_Logistics Warehouse.mp4` | `demo-video7` | 5번 영상 카메라 | `warehouse_lane_outside_safe_boxes` | 안전 통로(시연 ROI) |

시연 ROI이며 검증된 법적 위험구역으로 표시하지 않습니다.

---

## 7. null·미확인 표시

- `severity=null` → 표시 「미확인」. SAFE 금지. 상세에서 `observation_status`·`status_reason`·`evidence.reason` 확인
- 관측 없음 → 「관측 없음」
- 빈 이벤트 목록 → 「조회 결과 없음」
- 알 수 없는 코드/ID → 「알 수 없음 (원본)」

관측 상태·판정 상태·심각도는 **한 필드로 합치지 않음**.

---

## 8. 담당자 확인이 필요한 질문

1. `warehouse_lane_outside_safe_boxes` 표시명을 「안전 통로」로 둘지, 창고 통로 등 다른 명칭으로 할지  
2. `violation_status=not_verified` → 「위험」 표기가 PPE 검토 문맥에 적절한지  
3. `conflicting_evidence`를 「안전모 미착용 감지」로 동일 표기할지, 「근거 충돌」로 분리할지  
4. CSV에 `*_label` 컬럼을 기본 포함할지, 원본 컬럼만 둘지  
5. Excel용 `utf-8-sig`를 팀 표준으로 할지  

---

## 9. 샘플·검증

| 산출물 | 경로 |
| --- | --- |
| 표시 JSON 샘플 | `backend_v1/samples/display/events_display_sample.json` |
| 표시 CSV 샘플 | `backend_v1/samples/display/events_display_sample.csv` |
| 단위 테스트 | `backend_v1/test_dashboard_labels.py` |

샘플은 실제 `outputs/events`에서 event_id·코드를 보존하고 evidence만 축소한 것입니다.
