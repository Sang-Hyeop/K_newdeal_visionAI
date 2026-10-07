# 팀 연동 패키지 (2026-10-07)

백엔드(이벤트 로그) · 대시보드 담당이 **지금 바로** 붙일 수 있는 안내입니다.  
감지 모델 최종 확정 전이어도, **공통 JSONL 형식**으로 저장·조회·배너 연동을 진행하면 됩니다.

관련 문서:

- 스키마 상세: `docs/detection-output-contract.md`
- 실행 모듈: `docs/event-module-v1.md`
- ROI 말투 통일: `docs/roi-wording-2026-10-07.md`
- 브랜치/영상 받는 법: `docs/team-branch-setup-2026-10-07.md`
- 샘플 JSON: `docs/team-samples/2026-10-07/`

---

## 1. 역할 분담 (현재 기준)

| 기능 | 판정 방식 | 담당 출력 |
|---|---|---|
| 사람–지게차 근접 | 고정 ROI **없음**, 화면 전체 검출·거리 | `event_type=proximity` / `person_forklift_proximity` |
| 지게차–지게차 근접 | 고정 ROI **없음**, 관측된 차량 쌍 화면상 거리 | `forklift_forklift_proximity` (3번) |
| 구역/통로 | **별도 고정 ROI** | `zone_access` / `zone_dwell` (+ 차로 조건부 규칙) |
| 안전모 | 사람 추적 + 머리 연결 + 시간 확인 | `event_type=ppe` |
| 후드 보조 (5·6 옵션) | 전신 후드 후보 → SAFE 금지·UNKNOWN | PPE 이벤트에 `hood_evidence` (experimental) |
| 상태 배너 | 기능별 최신 관측 집계 | `observations_v1.jsonl`의 `feature_status` |

거리: **화면상 거리**만 사용. `distance_meters`는 항상 `null`.

---

## 2. 읽을 파일

각 실행 결과 폴더에 다음이 생깁니다.

| 파일 | 용도 |
|---|---|
| `events_v1.jsonl` | 상태 **전환 로그** 저장·검색·타임라인 |
| `observations_v1.jsonl` | 프레임별 **최신 상태** / 배너 갱신 |
| `summary.json` | 실행 요약(디버그) |
| `events.jsonl` / `observations.jsonl` | 예전 개별 형식(참고용, 신규 연동은 v1 사용) |

샘플(앞 8줄):

- 근접 전진: `docs/team-samples/2026-10-07/forward/`
- 근접 후진: `docs/team-samples/2026-10-07/reverse/`
- 구역(구 ROI 결과 포함): `docs/team-samples/2026-10-07/zone/`
- 통로 조건부(최신 ROI 정책): `docs/team-samples/2026-10-07/lane/`
- PPE: `docs/team-samples/2026-10-07/ppe5/`
- 예시 1건: `example_proximity_event.json`, `example_feature_status.json`

전체 영상 결과(로컬, Git 제외 가능):

- `outputs/diagnostics/events_separated_v1/{forward,reverse,zone}/`
- `outputs/diagnostics/lane_policy_v1/video/`
- `outputs/checkpoints/ppe_events_20261007/`

---

## 3. 공통 이벤트 필드 (`events_v1.jsonl`)

한 줄 = JSON 객체 1개.

필수에 가까운 필드:

- `schema_version` — `"1.0"`
- `event_id` — 동일 입력·버전 재실행 시 동일(중복 저장 방지용)
- `camera_id`, `video`, `source_sha256`
- `timestamp_seconds`
- `event_type` — `proximity` / `zone_access` / `zone_dwell` / `ppe` / `status`
- `severity` — `SAFE` / `WARNING` / `CRITICAL` / `null`
- `observation_status` — `confirmed` / `unconfirmed` 등
- `track_ids` — 문자열 배열
- `evidence` — 기능별 근거(bbox, ROI, 거리 등)
- `model_version`, `config_version` — 해시
- `scope` — 관측 범위 설명

규칙:

1. `observation_status=unconfirmed`이면 `severity`는 **반드시 null**
2. PPE `WARNING`은 검토 후보이다. 차량 과겹침 시 기존 관측 상태는 유지하고 `evidence.classification_status=unconfirmed`, `vehicle_overlap_review_required=true`를 함께 표시한다. 관측된 경고 후보와 확정 미착용은 다르다.
3. 대상이 없다고 **SAFE를 만들지 않음**
4. 기능이 다르면 상태를 서로 덮어쓰지 않음
   (예: 침범 CRITICAL을 체류 SAFE가 지우면 안 됨)
5. `feature_status` 배너: CRITICAL > WARNING 유지, 미확인 섞이면 SAFE로 올리지 않음

---

## 4. 배너용 `feature_status` (observations)

`display_state`: `SAFE` / `WARNING` / `CRITICAL` / `UNKNOWN`  
`global_safety_status`: 항상 `not_evaluated`에 가깝게 취급 (전체 현장 안전 선언 금지)

대시보드 권장 표시:

- 기능별 배너 4칸: 근접 / 구역 / PPE / (예비)
- 이벤트 리스트: `events_v1`를 시간 역순
- 필터: `event_type`, `severity`, `camera_id`, `video`

---

## 5. 백엔드 체크리스트

- [ ] `events_v1.jsonl` 파서 작성 (줄 단위 JSON)
- [ ] `event_id` unique 제약으로 중복 insert 방지
- [ ] `severity=null` / `unconfirmed` 저장 가능해야 함
- [ ] `evidence`는 JSON 컬럼 또는 TEXT로 원문 보존
- [ ] API: 최신 N개, 타입/심각도/카메라 필터, 시간 구간 조회
- [ ] `observations_v1`에서 카메라·기능별 최신 `feature_status` 조회 API

## 6. 대시보드 체크리스트

- [ ] 샘플 JSON만으로 화면 골격 동작
- [ ] 배너가 기능별로 분리됨
- [ ] SAFE를 “현장 전체 안전”으로 문구 쓰지 않음
- [ ] 미터(m) 단위 표시하지 않음 (null)
- [ ] ROI/구역 문구는 `docs/roi-wording-2026-10-07.md` 따름
- [ ] PPE 미착용 WARNING이 0개여도 파이프라인 연결은 완료로 표시 가능 (검출 품질은 별도)
- [ ] **고정 ROI 오버레이**: 시연 영상(`demo.mp4`)에는 감지 쪽이 칠하지만, 관제보드는 이벤트/설정의 다각형을 **직접 그려야** 함
  - 4번: `summary.json`의 `camera_config.polygon_normalized` **또는** zone 이벤트 `evidence.roi_polygon_normalized`
  - 7번: `camera_config.monitor_floor_normalized` + `safe_polygons_normalized` **또는** `evidence` 동명 필드
  - 알파: `evidence.roi_alpha_safe`(≈0.15) / `evidence.roi_alpha_alert`(≈0.2) 또는 summary camera_config
  - SAFE=초록·WARNING=주황·CRITICAL=빨강 (시연 mp4에 이미 칠해져 있어도 보드는 별도 렌더 필요)

---

## 7. 현재 한계 (화면에 같이 적을 것)

- 기본 개발 검출기는 **v16**. 후진 가림 시연만 선택적 recall bundle (독립 현장 정확도 아님)
- PPE WARNING은 **검토 후보**이며 확정 위반 증명이 아님 · 후드 보조는 experimental
- 구역 ROI는 **시연용 통로/작업 영역**, 법적 출입금지 확정 아님
- 3번 지게차–지게차는 **화면상 거리** (`distance_meters=null`), 박스 합침 시 근사 한계
- 모델 `.pt`는 Git에 없음 → 별도 전달
- 결정 요약: `docs/demo-adaptation-decision-2026-10-07.md`
- 1~7 통합 실행: `docs/demo-scenario-runbook-2026-10-07.md`

---

## 8. 실행 명령 (참고, safety 환경)

```bash
cd ~/Desktop/workspace   # 또는 clone한 경로
conda activate safety
git switch fix/proximity-detection-audit
git pull --ff-only

# 권장: 시연 1~7 통합 러너 (PPE 전 영상 ON)
python scripts/run_demo_scenarios.py \
  --videos 1 2 3 4 5 6 7 \
  --output outputs/diagnostics/scenario_team_$(date +%H%M%S) \
  --sample-fps 5

# 5·6 후드 보조 (SAFE → UNKNOWN, WARNING 보존)
python scripts/run_demo_scenarios.py \
  --videos 5 6 \
  --hood-auxiliary \
  --output outputs/diagnostics/scenario_hood_$(date +%H%M%S) \
  --sample-fps 5 \
  --ppe-search person_context

# 개별 근접 예시 (기본 v16)
python scripts/run_proximity_video.py \
  --source data/videos/1_forklift_forward.mp4 \
  --weights models/pilot_v16_related/person_forklift.pt \
  --config configs/cameras/forward-proximity.json \
  --output outputs/demo/team_forward_$(date +%H%M%S)

# 후진 시연용 recall bundle (v16 유지 + demo supplement)
python scripts/run_proximity_video.py \
  --source data/videos/2_forklift_back.mp4 \
  --weights models/pilot_v16_related/person_forklift.pt \
  --supplement-object-weights models/demo_object_adaptation_v1/best.pt \
  --demo-adapted \
  --config configs/cameras/reverse-proximity.json \
  --output outputs/demo/team_reverse_bundle_$(date +%H%M%S)

# 구역/통로 예시
python scripts/run_zone_dwell_video.py \
  --source data/videos/4_hazard_zone_dwell.mp4 \
  --weights models/pilot_v16_related/person_forklift.pt \
  --config configs/cameras/dwell-demo.json \
  --output outputs/demo/team_zone_$(date +%H%M%S) \
  --imgsz 1280
```

이미 만든 샘플 영상:

- `outputs/diagnostics/demo_object_recall_bundle_v1/forward/proximity.mp4`
- `outputs/diagnostics/demo_object_recall_bundle_v1/reverse/proximity.mp4`
- `outputs/diagnostics/scenario_plan_v2_hood_active/` (후드 활성 5·6)

`--output`은 **없는 새 폴더**여야 합니다.

## 최신 연동 확인

122개 자동 테스트 통과. 7개 영상 총 1,377개 샘플을 실제 추론 캐시에서 재계산했다. 종합 영상에서 차량 겹침 WARNING 검토 후보 93개가 공통 observations_v1에도 유지됨을 확인했다. 이전 dd3e22d 수정은 내부 경고만 유지하고 공통 변환에서 지워지는 문제가 있었으며 이번 수정으로 보완했다. 검토 후보 수는 정확도/확정 위반 수가 아니다.

최신 출력: `scenario_ppe_contract_short`(1~4), `scenario_ppe_contract_hood`(5~6), `scenario_ppe_contract_verified`(7), 모두 outputs/diagnostics 아래. 후드 v2는 미채택이며 v1을 유지한다.
