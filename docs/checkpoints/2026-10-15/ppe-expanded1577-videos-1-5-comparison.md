최신 재검증 완료: 동일 검색 조건의 구모델 대비 신모델 미확정은 2번 3.45→3.45%, 3번 23.17→29.27%, 5번 68.55→70.36%다. 저장 오류는 복구했고 현재 발표 모델은 유지한다. 자세한 최신 결과는 문서 끝의 “동일 추론 조건 재검증 완료”를 참고한다.

> 보존된 비교 기록: 영상별 기능 분리 이전 실행 결과입니다. 현재 1·4번은 PPE가 비활성화되어 있어 이 보고서의 수치를 현재 발표 결과로 사용하지 않습니다. 1577장 후보는 아직 미채택이며, 이후 PPE 비교 시 현재 캐시에 없는 PPE 관측 재생성과 후보 ppe_tracks의 head_candidates 일관성을 먼저 검증해야 합니다.

# PPE expanded1577 — 발표 영상 1~5 통제 비교 (2026-10-15)

상태: `experimental_not_promoted` / **비교 전용**.  
시연 기본 모델(`models/ppe_final/ppe_helmet_v6_960.pt`)·handoff 기본 경로·확정 리뷰(`outputs/reviews/`)는 **교체하지 않음**.  
합의 PPE 정책 파일은 **변경하지 않음**. GitHub 업로드하지 않음.

평가 체크리스트: 항목 2·3·6에 해당(모델 후보 비교, 확정 규칙 동일 적용, 영상별 출력 커버리지).  
**정답 GT 기반 정확도가 아님.** person-time 커버리지·상태 안정성만 측정. 독립 현장 일반화로 해석하지 않음.

---

## 1. 선행 완료 (Codex) — 재학습

| 항목 | 값 |
|------|-----|
| 후보 모델 | `models/experiments/ppe_expanded_1577/weights/best.pt` |
| SHA-256 | `5e77cd429820ba2389fc709dd9eb2db7281234689a493dc5d9d3cbd2d49c2df9` |
| 분할 | train 1263 / val 218 / test 117 (원래 분할 유지) |
| test117 @960 (v6→후보) | mAP50 0.7686→0.9318, mAP50–95 0.4010→0.6109 |
| 착용 AP50 | 0.7524→0.9095 |
| 미착용 AP50 | 0.7848→0.9541 |
| 학습 기록 | `docs/checkpoints/2026-10-15/ppe-expanded1577-training.json` |
| Codex 보고서 | `/Users/sanghyeopkim/Documents/Codex/2026-10-14/new-chat/outputs/ppe1577_training_report.txt` |
| 로컬 커밋 | `2bb5584` (학습 완료 기록; 비교 실행 이전) |

보고서 한계: 머리 탐지 성능이지 CCTV 시간 판정/미확정 감소 검증이 아님. 공개출처·개발자료 분할.

---

## 2. 합의 PPE 설정 (잠금, 비교에만 적용)

파일: `configs/ppe-user-approved-policy-2026-10-15.json`  
SHA-256: `c4e33e527c120f424c6e1adab6eff517a624f1ad49560ff6493eb0258f7675ea`

| 키 | 값 |
|----|-----|
| head_proposal_confidence | 0.15 |
| helmet_evidence_confidence | 0.40 |
| no_helmet_evidence_confidence | 0.30 |
| window_seconds | 1.0 |
| minimum_valid_observations | 3 |
| minimum_class_fraction | 0.75 |
| reset_on_single_missed_head | false |
| maximum_state_hold_seconds | 0.6 |
| opposite_evidence | stop_hold_and_return_pending |
| reset_on | track_identity_change, scene_cut |

비교 실행 시 추가: `require_baseline_helmet_confirmation=True` (후보 추론의 `model_sources`에 `baseline` 태그 포함).

`runtime_implementation_status`는 기록상 여전히 `not_yet_applied_retraining_first`.  
기본 `handoff.py` / `run_demo_scenarios.py` / `run_intrusion_review.py`의 런타임 정책은 **이번 비교로 바꾸지 않음**.

구현 모듈(기존): `src/ppe_window_events.py` (WindowPPEEvents), `src/ppe_events.py`가 `window_seconds` 있으면 위임.

---

## 3. 무엇을 어떻게 적용했는지 (비교 방법)

### 실행기

- 스크립트: `scripts/compare_ppe_video1.py` (이름 유지, `--video 1..5` 지원으로 확장)
- 스크립트 SHA-256 (비교 시점): `5a940694f512bb230f8cd0af464fabf22645ea0c3c767e5e84d09d481c56d0c8`
- 환경: `safety` conda, CPU 추론
- 명령 예:
  ```sh
  /opt/anaconda3/envs/safety/bin/python scripts/compare_ppe_video1.py --video N
  ```
- 기본 출력 루트: `outputs/diagnostics/ppe_compare_expanded1577_2026-10-15/videoN/`

### 통제 조건 (모든 영상 공통)

1. **사람/객체 박스·트랙**: 기존 확정 diagnostics 캐시의 `object_detections` / `ppe_tracks`(또는 2번은 PPE 이벤트에서 복원) **재사용**
2. **원본 프레임**에서만 PPE 머리 재추론 (후보 모델)
3. **근접·ROI·zone** 등 비-PPE 이벤트: 캐시 값 **그대로 유지** (영상별 preserve 키)
4. 확정 정책으로 `PPEEvents`/`WindowPPEEvents` 재판정
5. 사람–머리 기하: 기존과 동일 (`head_owner`, upper_fraction 0.35). 근거 부족 인물만 person-context 재탐지
6. 설비 오탐 필터: 영상별 object-review 설정 사용 (2번 제외)
7. 차량 PPE 가드: 1·3·4·5번 `apply_ppe_vehicle_guard`

### Arm 정의

| arm | 의미 |
|-----|------|
| `original` | 캐시에 저장된 기존 PPE 이벤트 통계 (당시 정책·v6) |
| `old_model_new_policy` | 캐시된 **기존 머리 후보** + **합의 정책**만 재판정 |
| `expanded1577_new_policy` | **expanded1577**로 머리 새 추론 + **합의 정책** |

분모: **person-time 반복 관측 건수** (고유 인원·실제 위반 수 아님).

### 영상별 캐시·보존 기능

| 발표# | 캐시 | 보존(비-PPE) | 리뷰 프로필 |
|------|------|--------------|-------------|
| 1 | `outputs/diagnostics/presentation1_equipment_corrected_2026-10-14/video1` | proximity | `configs/video2-object-review.json` |
| 2 | `outputs/diagnostics/presentation2_intrusion_review_2026-10-14` | zone_access | 없음 (AI 시연) |
| 3 | `outputs/diagnostics/presentation3_ppe_review_2026-10-14/video3` | (객체만) | `configs/video5-object-review.json` |
| 4 | `outputs/diagnostics/presentation4_worker_corrected_final_2026-10-14/video4` | zone_access, zone_dwell | `configs/video4-object-review.json` |
| 5 | `outputs/diagnostics/presentation5_vehicle_rider_review_v2_2026-10-14/video5` | zone_access, zone_dwell, proximity | `configs/video7-object-review.json` |

2번 특이: 캐시에 `ppe_tracks` 없음 → PPE 이벤트의 `person_bbox_xyxy`/`head_candidates`로 트랙 복원.

---

## 4. 결과 요약 (미확정 비율 = unconfirmed / total)

동일 정책끼리 핵심 대조는 **old_model_new_policy vs expanded1577_new_policy**.

| 영상 | samples | original 미확정 | old+정책 | **expanded1577+정책** | 해석 (커버리지) |
|------|---------|-----------------|----------|----------------------|-----------------|
| 1 | 106 | 185/209 (88.5%) | 148/209 (70.8%) | **99/209 (47.4%)** | 새 모델 명확 개선 |
| 2 | 58 | 7/58 (12.1%) | 2/58 (3.4%) | **2/58 (3.4%)** | 거의 동일 (이미 SAFE 다수) |
| 3 | 58 | 78/246 (31.7%) | 65/246 (26.4%) | **72/246 (29.3%)** | 구모델+정책보다 미확정 소폭↑ / 에피소드·깜빡임↓ |
| 4 | 92 | 125/319 (39.2%) | 102/319 (32.0%) | **134/319 (42.0%)** | 새 모델 악화 |
| 5 | 870 | 3135/4241 (73.9%) | 2904/4241 (68.5%) | **2984/4241 (70.4%)** | 원본보다↓, 구모델+정책보다 소폭↑ |

### 상세 counts

#### Video 1
| arm | unconf | WARN | SAFE | episodes | state_changes | held |
|-----|--------|------|------|----------|---------------|------|
| original | 185 | 24 | 0 | 7 | 14 | 0 |
| old_model_new_policy | 148 | 61 | 0 | 8 | 16 | 29 |
| expanded1577_new_policy | 99 | 110 | 0 | 3 | 6 | 16 |

#### Video 2
| arm | unconf | WARN | SAFE | episodes | state_changes | held |
|-----|--------|------|------|----------|---------------|------|
| original | 7 | 0 | 51 | 0 | 3 | 0 |
| old_model_new_policy | 2 | 0 | 56 | 0 | 1 | 1 |
| expanded1577_new_policy | 2 | 0 | 56 | 0 | 1 | 0 |

#### Video 3
| arm | unconf | WARN | SAFE | episodes | state_changes | held |
|-----|--------|------|------|----------|---------------|------|
| original | 78 | 53 | 115 | 8 | 29 | 0 |
| old_model_new_policy | 65 | 57 | 124 | 7 | 23 | 6 |
| expanded1577_new_policy | 72 | 48 | 126 | 3 | 14 | 4 |

#### Video 4
| arm | unconf | WARN | SAFE | episodes | state_changes | held |
|-----|--------|------|------|----------|---------------|------|
| original | 125 | 194 | 0 | 14 | 23 | 0 |
| old_model_new_policy | 102 | 217 | 0 | 9 | 11 | 16 |
| expanded1577_new_policy | 134 | 185 | 0 | 9 | 12 | 28 |

#### Video 5
| arm | unconf | WARN | SAFE | episodes | state_changes | held |
|-----|--------|------|------|----------|---------------|------|
| original | 3135 | 1106 | 0 | 140 | 233 | 0 |
| old_model_new_policy | 2904 | 1337 | 0 | 116 | 166 | 194 |
| expanded1577_new_policy | 2984 | 1257 | 0 | 100 | 148 | 170 |

---

## 5. Video 4 미확정 증가 원인 (진단, 사용자 검수 예정)

동일 프레임·트랙 pairwise (old_model_new_policy → expanded1577):

- conf→unc: **40**, unc→conf: **8** (순증 ≈ +32 → 102→134와 정합)

conf→unc 40건 분해:

- **25** 새 모델 머리 0개 (구 캐시는 머리 있음)
- **5** 머리는 있으나 conf **&lt; 0.30** (미착용 근거 임곗값 미달)
- **10** pending_temporal_confirmation만

예시: 구 `no_helmet 0.51` → 신 `0.17` 또는 빈 후보.  
정책은 그대로인데 **4번 장면에서 후보 모델의 미착용 머리 recall/점수가 v6 캐시보다 약함**.  
test117 개선 ≠ 이 CCTV 장면 개선.

---

## 6. 산출물 경로·해시

루트: `outputs/diagnostics/ppe_compare_expanded1577_2026-10-15/`

각 `videoN/`:

- `comparison.json`
- `old_model_new_policy/review.mp4`, `detections.jsonl`, `ppe/events_v1.jsonl`, preview jpg
- `expanded1577_new_policy/` 동일 구조

| 영상 | comparison.json SHA-256 | expanded1577 review.mp4 SHA-256 |
|------|-------------------------|----------------------------------|
| 1 | `8fb956b10be3a904f55d920923481fe28201fa490f459c7ca66b691ba5545d12` | `fe5e416663304084958502ff61f40c7d18ff9c255634e03bfb6905bd9e175b29` |
| 2 | `1649a6835869f60bc1d67248ad4cebb8828fec1ce1763a9048f384d515be03f3` | `7c3ad7250b1c30aa599511ce5c2bd153cf4959f0ea98465c298ef0a1ecb88713` |
| 3 | `b005401e03624b5d15ab164f0e0b77dabd20a14bfb74ded0db39cdf6d5cab9dd` | `50c7882336c62111c7d42f7016166b8fa4a4acd6cbf7c0b3400833e8cae042c6` |
| 4 | `1f335c092c97127a7b250ca76abfbf7a6ff2aa2db090f5fc1f4b08d2c9ffc695` | `5c0f816751238c549b23d5a876e3216aa2bb2ddf697c46311611fd9f9caac173` |
| 5 | `10ba73b206ca02d6fce382ffb57fc91c1eb779a14b43792916c6c6fbc13d793e` | `3550fdcbfce68de382217c68374c1ed0159caa675288b8051fd9dcbcfb1c1243` |

기계 판독용 동봉 JSON: `docs/checkpoints/2026-10-15/ppe-expanded1577-videos-1-5-comparison.json`

---

## 7. 명시적으로 하지 않은 것

- `ppe_helmet_v6_960.pt` / team-runtime 기본 PPE 가중치 교체 안 함
- 합의 정책 임곗값 변경 안 함
- `outputs/reviews/` 확정 시연 영상 덮어쓰기 안 함
- GitHub push 안 함
- 영상별 착용/미착용 **정답 라벨 전수 검수** 안 함
- 단일 기능 시연(1번에 PPE 끄기)·이동방향 근접 필터는 **별도 논의만**, 이번 비교에 미포함

---

## 8. Codex 재개 시 권장 다음 단계

1. 사용자 영상 검수: 특히 **1번(개선)** vs **4·5번(악화/소폭 악화)** 장면 차이
2. 채택 여부 결정 전: expanded1577을 final로 승격하지 말 것
3. 채택 시: 정책 런타임 반영(`runtime_implementation_status`) + handoff/config 가중치 연결을 **사용자 승인 후** 진행
4. 미채택/보완 시: 4·5번 실패 구간(원거리·통로) hard example 재학습 후보 검토
5. 로컬 미커밋: `scripts/compare_ppe_video1.py` 확장 + 일부 스크립트 한글 주석 — 체크포인트 커밋은 사용자 요청 시

브랜치 참고: `data/hoodie-ppe-candidates` (학습 기록 커밋 `2bb5584` 기준 ahead; 비교 문서/스크립트는 추가 커밋 필요할 수 있음).

## 동일 추론 조건 재검증 완료 (2026-10-15)

캐시 저장 오류를 수정하고 기존 실험 폴더에서 구모델을 전 구간 재추론했다. 신모델은 기존 실제 신규 추론 캐시를 복구해 모든 1,184시점의 이벤트가 동일하게 재생되는지 확인했고, 각 영상 시작·중간·끝 15시점을 다시 추론해 머리 후보가 정확히 같은지 대조했다. 모델·정책·원본 해시를 검증했다.

- 1번: 구모델 미확정 148/209 (70.81%) → 신모델 99/209 (47.37%). 진단 전용: 현재 PPE 제외 영상.
- 2번: 구모델 미확정 2/58 (3.45%) → 신모델 2/58 (3.45%). 현재 PPE 사용 영상.
- 3번: 구모델 미확정 57/246 (23.17%) → 신모델 72/246 (29.27%). 현재 PPE 사용 영상.
- 4번: 구모델 미확정 105/319 (32.92%) → 신모델 134/319 (42.01%). 진단 전용: 현재 PPE 제외 영상.
- 5번: 구모델 미확정 2907/4241 (68.55%) → 신모델 2984/4241 (70.36%). 현재 PPE 사용 영상.

수정된 candidate 트랙 관측은 3,036건이다. 새 관측으로 판정한 뒤 이전 머리 후보를 저장하던 오류를 수정했다. 신모델 이벤트 집계와 기존 리뷰 영상은 바뀌지 않았고, 원본 후보·수정 트랙·이벤트를 모두 맞춰 저장했다. 회귀 테스트로 JSON 저장 후 동일한 PPE 이벤트 재생을 확인한다.

### 차이 장면 검수

3번에서는 구모델 확정→신모델 미확정 18건, 반대 개선 3건. 4번은 악화 39건·개선 10건이며 악화 중 연결 머리 후보 없음 25건, 신뢰도 부족 5건, 유효 머리는 있으나 시간 조건 미충족 9건이다.

5번은 악화 208건·개선 131건. 악화 208건의 원인은 임곗값 미달 91건, 연결 후보 없음 56건, 시간 조건 미충족 60건, 클래스 충돌 1건이다. 반복 사람-시점 기록이며 고유 사람/위반 건수가 아니다. 두 모델이 모두 확정한 1,126건은 판정 클래스가 같았다.

4번 8장과 5번 8장의 차이 장면을 원본에서 직접 확인했다. 작은 머리·측후면·가림·낮은 신뢰도·시간적 증거 끊김이 섞여 있다. 구모델에도 중복 머리 후보와 이전 증거 유지가 있어 구모델 확정을 정답으로 간주할 수 없다. 신모델이 머리를 더 잘 포착한 개선 장면도 포함했다. 이는 차이 기반 비무작위 샘플이고 정확도 평가 정답셋이 아니다.

비교 이미지와 시점 기록: outputs/diagnostics/ppe_compare_expanded1577_2026-10-15/video4/video4_regressions.jpg, video4/video4_cases.json, video5/video5_differences.jpg, video5/video5_cases.json. 같은 영상 폴더의 old_model_fresh_new_policy/에는 새 구모델 리뷰·JSONL·이벤트가 있다.

### 결론과 보존 범위

현재 발표 모델 v6와 사용자 확정 정책을 유지한다. 1577장 후보 전체 교체 근거는 부족하다. PPE를 사용하는 3·5번에서 실제로 약한 작은 머리·측후면·가림 사례를 검수한 뒤 추가 학습 자료로 보완하는 방향이 우선이다. 1번 개선은 현재 PPE 제외 영상이므로 발표 모델 교체 근거로 사용하지 않는다. 임곗값·시간 조건을 낮춰 미확정 숫자를 맞추지 않았다. 확정 리뷰·배포 파일·기본 모델·위험 규칙은 변경하지 않았고 GitHub에는 업로드하지 않았다.

## 상반신 확대·연결·ID 점검 (2026-10-15)

현재 v6를 유지하고 유효 머리 증거가 부족한 사람만 좁은 상반신으로 추가 추론했다. 검색 영역은 좌우0.4×사람폭, 위0.15×사람높이, 아래는 사람 상단부터0.6×높이이며 imgsz640이다. 제안0.15/착용0.4/미착용0.3, 1초·3관측·75%·hold0.6초, 사람–머리 연결 기준과 사람 ID를 변경하지 않았다.

- 3번: 미확정57/246(23.17%)→56/246(22.76%). 추가SAFE1건은 5.839초의 회색후드로, 외부 안전모 착용이 확인되지 않는 오착용 판정 위험이다. 실제 개선으로 채택하지 않는다.
- 5번: 미확정2907/4241(68.55%)→2572/4241(60.65%). 확정회복336/손실1, 순335건 감소. 새 SAFE·확정 클래스 반전은 없다. 추가 확정은 미착용 검수 경고이며 정확도 개선으로 단정하지 않는다.
- 3번 초기2회 관측 중 미확정40건/전체57건, 새ID28개, 인접 단일 박스 IoU>0.5인 ID전환가설2곳. 2.71초와9.80초 원본 대조에서 같은 작업자로 보이는 사례를 확인했으나 ID 자동 합치기는 하지 않았다. 정상 진입/장면 전환에 따른 초기 관측도 포함된다.
- 5번 초기2회 미확정867건/전체2907건, 새ID678개, ID전환가설152곳. ID 수는 고유 사람 수가 아니며 전환 가설은 검증된 ID switch 지표가 아니다.
- 머리 후보가 호환되는 다른 사람으로 선택되는 진단쌍은 3번0/5번208이다. 반복 후보-사람 호환쌍이며 오연결 확정 건수가 아니다. 강제로 주인을 바꾸면 다른 사람 머리가 잘못 연결될 수 있어 기준을 유지했다.

3번의 유일 변경1장·ID전환2장면, 5번 변경8장면(확정회복7/손실1)을 원본에서 검수했다. 차이 기반 비무작위 검수이며 독립 정답셋 평가가 아니다. 3번 후드 오착용 위험 때문에 공통 적용하지 않는다. 5번은 작은 머리 회복 가능성이 있지만 추가경고의 정답 검수가 필요하다. 현재 발표 모델·설정·리뷰·이벤트·Release는 그대로 유지한다.

결과는 각 video3/video5의 upper_body_recheck_v6/ 아래 comparison.json, changes.json, detections.jsonl, review_cases.json, review.mp4에 있다. 영상은 왼쪽 기존/오른쪽 확대 실험이다. 3번 ID검수는 video3_id_review.jpg다. 회귀254개 통과. 다음 단계는 추가 경고 정답검수·후드 오착용 회귀사례 확보·실제 ID교체 사례 추적 보완 검증이다. GitHub push 없음.

## 추적 연속성·확대 착용 보호장치 조합 검증 (2026-10-15)

동일 사람 검출 박스·신뢰도·머리 후보로 네 조건을 비교했다: 기존 score-fused 추적, geometry-only 추적, 기존추적+보수적확대, geometry-only추적+보수적확대. geometry-only는 기존 PersonTracker의 fuse_score=False 옵션만 사용하며 match/검출 임계값·장면 전환/누락 처리는 유지한다. ID를 수동 합치거나 PPE 상태를 다른 ID에 복사하지 않는다. 기존 추적의 PPE 통계가 이전 대조군과 정확히 재현되는지 확인했다.

확대 착용 보호: 추가 상반신 크롭에서만 나온 helmeted_head는 검수 후보로 남기고 착용 SAFE 생성에 사용하지 않는다. 기존 탐지의 착용 근거는 유지하고 추가 no_helmet_head를 검수 경고용 증거로 더한다. 후드 분류기를 만든 것이 아니며, 크롭만으로 회복 가능한 실제 안전모도 자동 확정하지 않는 보수적 제한이다. 확정 PPE 임곗값·시간·관측비율·hold는 그대로다.

- 3번 기존: 미확정57/246(23.17%), ID28개. 추적만:46/246(18.70%), ID17개. 보호확대만:57/246. 조합:46/246, SAFE126→137, WARNING63 유지. 새SAFE11건 전부 외부 안전모가 보이는 것을 원본에서 확인했다. 5.839초 후드 오착용 회귀 장면은 미확정 유지. 관측 손실·확정 클래스 반전0.
- 5번 기존: 미확정2907/4241(68.55%), ID678개. 추적만:2811/4241(66.28%), ID301개. 보호확대만:2572/4241(60.65%). 조합:2451/4241(57.79%), ID301개. 새WARNING471/확정→미확정15, 순456건 감소. 새SAFE·확정 클래스 반전0.
- 5번 손실15건 전부 원본·이벤트 대조:14건 시간 조건 미충족,1건 머리 증거 부족. 표본 경고회복3건도 검수했다. 낮은 ID 수는 연속성 진단이며 IDF1 개선·동일인 식별 보장이 아니다. 근접 사람 오연결은 별도 ID 정답 평가가 필요하다.

사람 관측 수는 모든 조건에서 3번246/5번4241로 같으며 미관측 위치에 박스를 남기지 않는다. 회귀258개 및 배포91개파일/원본5개 해시 검사 통과. 기본 실행·확정 리뷰·모델·설정·Release는 그대로다. 각 video3/video5/stability_guard_v6/의 comparison.json, 각arm/detections.jsonl, changes.json, id_associations.jsonl, review.mp4에 보존했다. 좌우 비교영상은 기존/조합 실험이다. GitHub push 없음.
