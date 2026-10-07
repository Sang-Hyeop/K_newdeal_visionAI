# 시연 보완 학습 결정 (2026-10-07)

Codex 학습이 한도 제한으로 끊긴 뒤, 로컬 산출물로 결정을 마무리했다.

## 결정

1. **기본 개발 검출기: v16 유지** (`models/pilot_v16_related/person_forklift.pt`)
2. **시연용 근접(특히 후진 가림): v16 + demo adaptation supplement 번들**  
   - 설정: `configs/selected-demo-object-bundle.json`  
   - 라우팅: baseline conf≥0.25 박스 보존, 새 후보는 IoU≥0.5로 안 겹칠 때만 추가
3. **시연 적응 모델 단독 교체: 거부**  
   - 후진 8/8은 통과했지만 고정 평가 지게차 FN 2→5
4. **PPE: 기본 모델 유지** (`pilot_v3_ppe_expansion`)  
   - demo PPE는 experimental, 단독 교체 시 안전모 검출 악화

## 근거 요약

| 후보 | 후진 8장면 | 고정평가 미탐 게이트 | 채택 |
|---|---|---|---|
| v16 | (이전) 추적 약함 | 기준 | 기본 |
| demo best/last 단독 | 8/8 통과 | 지게차 미탐 악화 | 거부 |
| v16+demo bundle | 8/8 통과 | 통과 | **시연 근접 옵션** |

보고:

- `outputs/diagnostics/demo_object_adaptation_v1_best/report.json`
- `outputs/diagnostics/demo_object_adaptation_v1_last/report.json`
- `outputs/diagnostics/demo_object_recall_bundle_v1/report.json`

## 실행 (시연 번들)

```bash
conda activate safety
cd ~/Desktop/workspace   # 또는 clone 경로

python scripts/run_proximity_video.py \
  --source data/videos/2_forklift_back.mp4 \
  --config configs/cameras/reverse-proximity.json \
  --weights models/pilot_v16_related/person_forklift.pt \
  --supplement-object-weights models/demo_object_adaptation_v1/best.pt \
  --demo-adapted \
  --output outputs/demo/bundle_reverse_$(date +%H%M%S)
```

전진도 `--source data/videos/1_forklift_forward.mp4` + `forward-proximity.json`로 동일.

## 이미 만들어진 샘플 영상

- 전진: `outputs/diagnostics/demo_object_recall_bundle_v1/forward/proximity.mp4`
- 후진: `outputs/diagnostics/demo_object_recall_bundle_v1/reverse/proximity.mp4`
- 이벤트: 같은 폴더의 `events_v1.jsonl`, `observations_v1.jsonl`
- dense 후진(250–345): `outputs/diagnostics/demo_object_recall_bundle_dense_v1/`  
  → 목표 구간 36프레임 전부 차량 검출·추적·동일 ID, 작업자 추적 36/36 (보간 참조, 독립 정답 아님)

## 한계 (반드시 같이 말할 것)

- 시연 프레임을 train에 넣었으므로 **시연 환경 개선**이지 독립 현장 정확도가 아님
- 미터(m) 없음
- 검출 실패는 안전으로 표시하지 않음
- PPE 미착용 품질은 아직 미완성
