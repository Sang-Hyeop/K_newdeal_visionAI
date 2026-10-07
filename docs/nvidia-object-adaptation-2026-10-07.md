# Nvidia 자료로 지게차 추가 학습

52개 원본의 길이·해상도·해시를 확인하고 208개 후보 프레임을 추출했다. 그중 12개 영상의 24장을 직접 검수하여 사람·지게차 박스를 작성했다. 차량 주변 확대 33장과 배경 음성 예제20장을 만들었다. 기존 데이터와 합쳐 train201/val84/test42로 학습했다. 같은 원본 영상의 파생 이미지는 같은 분할에 유지했다. 수동 팔레트 잭은 지게차에서 제외했다.

기존 YOLO26n 기반 보완 가중치에서 8epoch 추가 학습했다. 새 아키텍처를 만들거나 추적 박스를 정답처럼 학습하지 않았다. 새 모델은 models/nvidia_object_adaptation_v1/best.pt 이다.

1번 영상 주요 지게차를 검수한 20장에서 동일한 conf0.25/IoU0.5/640+1280 기준으로 기존12/20 → 새20/20이다. 원본 확대 재검수로 f100·f125·f375 정답 박스를 바로잡았으며 최종 비교는 수정된 동일 정답에 양쪽 모델을 재평가했다. 이는 같은 카메라 적응 결과이고 독립 현장 성능이나 모든 프레임 미탐0의 증거가 아니다. 개발 test42장 지게차 recall은 기존0.860 → 새0.791로 회귀했다. 그래서 전체 카메라의 일반 모델을 교체하지 않고 1번 영상 전용 적응 모델로만 사용한다.

1번 카메라만 새 지게차 모델로 연결했다. 일반 모델의 선반 오탐이 다시 합쳐지지 않도록 해당 카메라에서 baseline 차량 제안은 제외했다. 사람은 기존 COCO 모델, PPE는 검증된 실제 추론 캐시를 사용한다. 근접은 고정 ROI 없이 사람 높이 정규화 화면상 거리로 계산한다. 경고1.6/위험0.8이며 미터가 아니다. 보이지 않는 객체의 박스를 만들어 채우지 않았다. UNKNOWN26/106은 차량 없는 마지막 장면이나 사람 검출·추적 등도 포함하므로 지게차 미탐26회로 해석하면 안 된다. 차량 박스 분할과 PPE 미확인은 남아 있다.

## 결과 위치

- outputs/diagnostics/video1_nvidia_adaptation_v1/video1/demo_h264.mp4
- outputs/diagnostics/video1_nvidia_adaptation_v1/video1/detections.jsonl
- outputs/diagnostics/nvidia_adaptation_comparison/comparison.json
- docs/checkpoints/2026-10-07/nvidia-object-adaptation-v1/result.json

## 재현

```sh
conda activate safety
python scripts/evaluate_nvidia_adaptation.py
# 캐시 폴더가 없을 때 생성한다. 원본/모델 해시를 기록한다.
python scripts/cache_nvidia_video1.py
python scripts/run_demo_scenarios.py --videos 1 --output outputs/diagnostics/video1_nvidia_adaptation_rerun --reuse-run outputs/diagnostics/scenario_ppe_contract_short --object-review-cache outputs/diagnostics/video1_nvidia_object_cache
```

모델·학습 이미지·생성 영상은 기존 gitignore대로 로컬 보존하며 체크포인트 해시로 식별한다. main 병합은 수행하지 않았다.
