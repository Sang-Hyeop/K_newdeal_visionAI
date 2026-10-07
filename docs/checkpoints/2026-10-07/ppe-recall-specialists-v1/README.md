# 시연 감지 보완 결과 — 2026-10-07

후진 목표 구간 12.4~13.8초의 36개 전체 프레임에서 지게차와 작업자 실제 검출·추적을 확인했습니다. PPE 수동 검수 머리 관측 73건(서로 다른 73명이 아님)은 신뢰도 0.5/IoU 0.5에서 미탐 0건입니다.

5번 영상의 맨머리 두 사람에 대한 약 4.8 FPS 연속 평가에서는 39건 모두 검출됐고, 0.4초 확인 시간이 지난 35건 모두 WARNING이 이어졌습니다. 연속 평가 박스는 검수 키프레임 사이를 보간했으므로 전체 프레임 수동 정답 평가와 다릅니다. 73건과 39건은 중복이 있어 합산하지 않습니다.

이번 결과는 시연 영상으로 보완 학습한 결과입니다. 새로운 현장 및 모든 프레임의 미탐 0을 입증하지 않습니다. PPE는 기존 모델, 보완 모델, 안전모 전용 모델을 함께 사용하는 임시 시연 구성이며, 단일 pt로 통합하는 목표는 아직 남아 있습니다. 오탐이 늘 수 있고, 6번 영상 후드·가림은 확인이 필요합니다.

WARNING은 미착용 확정이 아닌 검토 후보입니다. 맨머리 후보 신뢰도 0.25 이상이 3회/0.4초 이어지면 경고하며, 안전모 SAFE는 0.5 이상을 요구합니다. 실제 머리 검출이 없으면 UNKNOWN입니다. 영상은 저장한 실제 추론 결과를 재생하며 실시간 CPU 성능을 뜻하지 않습니다.

## 파일

- reverse_dense_target_h264.mp4: 후진 목표 구간
- ppe5/ppe_events_h264.mp4: 안전모 착용·미착용 혼재
- ppe6/ppe_events_h264.mp4: 지게차 시점 안전모
- 각 폴더 events_v1.jsonl/observations_v1.jsonl: 팀 연동용 이벤트와 프레임 관측
- ppe_model_profile.json: 모델 경로·SHA·선택 설정
- ppe_continuous_review.json: 연속 평가 상세

## 새 영상 실행

프로젝트 루트 /Users/sanghyeopkim/Desktop/workspace 에서 safety 환경을 사용합니다. 기존 입력·출력은 덮어쓰지 말고 새 출력 폴더를 지정합니다.

```sh
conda activate safety
python scripts/validate_tracked_ppe.py \
 --source data/videos/5_PPE_Helmet.mp4 \
 --output outputs/validation/ppe_recall_new_run \
 --objects-weights models/pretrained/yolo26n.pt \
 --ppe-weights models/pilot_v3_ppe_expansion/ppe.pt \
 --supplement-ppe-weights models/demo_ppe_interpolated_v4/ppe.pt \
 --helmet-specialist-weights models/demo_ppe_failure_context_v3/last.pt \
 --ppe-preserve-union --object-imgsz 1280 --ppe-crop-height 1 \
 --tiled-head-search --unassigned-head-events --ppe-candidate-tracks \
 --weak-head-context-recheck --config configs/ppe-recall-review-policy.json
```

결과 영상은 실제 저장된 추론을 후보 사람 박스, 실제 머리 문맥 확대, 이벤트 재평가 단계로 처리했습니다. 위 통합 실행 경로의 새 실행 결과는 별도로 비교 검증해야 합니다. 일반 모델의 설정은 유지했습니다.
