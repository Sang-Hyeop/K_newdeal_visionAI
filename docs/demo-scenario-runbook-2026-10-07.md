# 시연 시나리오 실행 런북 (2026-10-07)

1~7번 기능 시연을 **한 러너**로 돌리는 방법과 한계입니다.  
시연에서 무엇 켤지: `docs/demo-feature-show-plan-2026-10-07.md`  
팀 JSONL 연동: `docs/team-integration-pack-2026-10-07.md`

브랜치: `fix/proximity-detection-audit`  
환경: `conda activate safety`

---

## 1. 필요한 모델 (Git 제외 · 별도 공유)

| 용도 | 경로 | 비고 |
|---|---|---|
| 객체 baseline | `models/pilot_v16_related/person_forklift.pt` | 일반 개발 유지 |
| 객체 supplement | `models/demo_object_adaptation_v1/best.pt` | 후진 가림 시연 보완 |
| PPE baseline / supplement / helmet | `configs/demo-ppe-model.json` 참고 | ensemble, 단일 pt 아님 |
| 후드 보조 (5·6 옵션) | `models/hoodie_auxiliary_v1/hoodie.pt` | experimental |

설정 스냅샷:

- `configs/demo-scenarios.json`
- `configs/demo-object-model.json`
- `configs/demo-ppe-model.json`
- `configs/demo-hood-model.json`

---

## 2. 한 번에 1~7 (PPE ON)

```bash
cd ~/Desktop/workspace   # 또는 clone 경로
conda activate safety
git switch fix/proximity-detection-audit

python scripts/run_demo_scenarios.py \
  --videos 1 2 3 4 5 6 7 \
  --output outputs/diagnostics/scenario_plan_v2_team_$(date +%H%M%S) \
  --sample-fps 5
```

`--output`은 **없는 새 폴더**여야 합니다.

영상별 핵심:

| # | 기능 |
|---|---|
| 1 | 사람–지게차 근접 + PPE |
| 2 | 동일 + recall bundle 객체 |
| 3 | 지게차–지게차 근접 (`forklift_forklift_proximity`, 화면상 거리) |
| 4 | 통로 ROI 침범·체류 + PPE |
| 5·6 | PPE 중심 |
| 7 | 종합 (ROI + 조건부 근접 + PPE) |

---

## 3. 후드 보조 (5·6만, opt-in)

후드 근거가 있으면 PPE **SAFE를 UNKNOWN으로** 낮춥니다. 기존 WARNING은 보존합니다.  
Normal 클래스 = PPE 안전이 **아닙니다**.

```bash
python scripts/run_demo_scenarios.py \
  --videos 5 6 \
  --hood-auxiliary \
  --output outputs/diagnostics/scenario_plan_v2_hood_$(date +%H%M%S) \
  --sample-fps 5 \
  --ppe-search person_context
```

이미 검증된 샘플 결과(로컬):

- `outputs/diagnostics/scenario_plan_v2_hood_active/`
- 해시 목록: `outputs/checkpoints/scenario_plan_v2_hood_active/sha256.json`
- 기록: `docs/checkpoints/2026-10-07/hoodie-auxiliary-v1/activation.json`

캐시 재사용(개발용):

```bash
python scripts/run_demo_scenarios.py \
  --videos 5 6 \
  --hood-auxiliary \
  --reuse-run outputs/diagnostics/scenario_plan_v2_conservative_ppe \
  --reuse-hood-run outputs/checkpoints/hoodie_auxiliary_v1 \
  --output outputs/diagnostics/scenario_plan_v2_hood_reuse_$(date +%H%M%S) \
  --sample-fps 5 \
  --ppe-search person_context
```

---

## 4. 결과물

각 `videoN/` 아래:

- `demo.mp4`, `preview_*.jpg`
- `detections.jsonl`
- `summary.json`
- 기능별 `ppe/` · `proximity/` · `zone_*` / `forklift_proximity/` 의 `events_v1.jsonl`

상태 카운트는 **검수 recall이 아닙니다.**

---

## 5. 팀에 같이 말할 한계

- 시연 영상 적응 결과 ≠ 새 현장 미탐 0
- `distance_meters`는 보정 전 **null** (3번도 화면상)
- 후드 보조는 **experimental_not_promoted**
- 후드 full-frame만으로는 약하고, **사람 crop**이 필요
- 3번: 합쳐진/중복 차량 박스는 거리를 UNKNOWN으로 내림 (완전 해결은 검출 품질 후속)
- PPE–지게차 과겹침(≥80%)은 운전자/설비 오탐 후보로 UNKNOWN
- PPE WARNING은 검토 후보이지 확정 위반 증명 아님
- 공유할 pt 해시: `docs/checkpoints/2026-10-07/model-share-manifest.json`
- main 미병합 시 반드시 `fix/proximity-detection-audit` 사용

---

## 6. 자동 검사

```bash
conda activate safety
python -m unittest discover -s tests -p 'test_*.py' -q
```
