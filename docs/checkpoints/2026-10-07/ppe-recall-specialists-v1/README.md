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

5번·6번 원본 영상 모두 위 통합 실행 경로로 처음부터 다시 처리했습니다. 5번 연속 검출 39/39, 확인 시간 이후 경고 35/35 결과를 재현했습니다. 일반 모델의 설정은 유지했습니다.


## 마지막 고정 평가 추가 점검 — 중지 시점

객체 입력을 1280으로만 바꾸면 기존 640보다 성능이 떨어졌습니다. 이를 기본 실행으로 승격하지 않았습니다.

여러 실제 모델·해상도의 검출을 중복 제거 없이 합친 실험에서는 40장 평가의 사람 40/40·지게차 40/40이 검출됐습니다. 하지만 중복 박스까지 포함한 FP가 사람 200·지게차 158로 크게 늘었습니다. 이 실험은 실제 이벤트 파이프라인에 적용하지 않았습니다. 오래된 11장 평가에서는 사람 17/18·지게차 11/11로, 가린 작업자 1건의 미탐이 남았습니다. 이 1건은 전체 화면 균일 타일 확대 검사에서도 검출되지 않았습니다. 따라서 전체 모델의 미탐 0을 달성했다고 주장하지 않습니다. 선택한 기존 객체 시연 구성의 별도 고정 평가는 사람·지게차 미탐이 각각 2건 남아 있습니다.

사용자의 중지 요청에 따라 새 학습·새 데이터 수집·기능 추가는 시작하지 않고 여기서 저장 후 대기합니다. 이어갈 때는 남은 가림 작업자 분석, 중복을 줄이면서 정검출을 보존하는 검증, 단일 pt 통합, 모든 영상 PPE 연동·검증이 남아 있습니다. 3번 지게차–지게차 이벤트는 별도 구현 과제입니다.

코드는 작업 브랜치에 저장하며 새 PR·main 병합은 진행하지 않습니다. 모델과 결과 영상은 로컬 백업이며 GitHub 코드 업로드와 구분합니다. `demo_model_weights.zip`에는 선택한 모델 6개와 설정을 담았습니다.
