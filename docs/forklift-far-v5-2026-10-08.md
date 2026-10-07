# 지게차 원거리·회전 구간 보완 학습 v5

사용자 요청 이후 직전 miss audit에서 후진 영상의 원거리·방향전환 구간을 후보로 검수했다. 시연 영상에 인접한 7개 프레임을 whole loaded-vehicle 기준으로 승인해 21개 실제 context crop을 만들었다. 평가 기준점 원본 프레임 자체는 train에 넣지 않았지만 같은 영상 및 가까운 프레임의 노출은 남는다. 별도 신현장 성능으로 볼 수 없다.

학습은 `safe_carrying_envelope_v2/best.pt`에서 3 epochs, lr=0.0001, freeze=12로 끝냈다. 별도 로컬 가중치와 해시를 보관했다.

같은 72개 평가 표본에 v4 다중 모델 후보를 비교했다. conf .25 / IoU .5:
- test50: baseline TP44/FP10/FN7 → 후보 TP51/FP184/FN0.
- 후진 coarse reference22: baseline TP9/FP13/FN13 → 후보 TP21/FP86/FN1. 남은 미탐은 `frame500`.

평가 표본 미탐은 줄었지만 FP가 매우 늘었다. 따라서 “미탐 0”은 50개 정지 이미지 하위집합의 결과에만 해당하며, 후진 수동 기준점과 원본 전체 프레임에서는 달성하지 못했다. 신뢰도 .1 기준은 FP가 더 많다. 기본 파이프라인으로 승격하지 않는다.

`safe_3_tr9_f000162.jpg`의 기존 외곽 정답 박스는 빈 바닥·배경을 포함해 원본 이미지로 다시 검수한 경계 좌표를 비교 평가에 적용했다. 원본 이미지·원본 라벨 파일은 변경하지 않았으며 학습에 쓰지 않았다. 이 한 항목은 모델 개선으로 세지 않고, 수정 전후 참조 점수를 둘 다 평가 JSON에 남겼다.

재현 평가는 `python scripts/evaluate_forklift_recall_v4.py --specialist models/forklift_demo_far_v5/best.pt --reference-audit configs/review/forklift-reference-quality-v5.json --output outputs/diagnostics/forklift_recall_v5_evaluation`.

다음에는 frame500을 포함한 실패 유형을 검수하되 연속 프레임 복제만 늘리지 않는다. 새 학습보다 오탐의 위치/클래스와 단일 추론·결합 정책을 비교해 보정하는 것이 우선이다. 사용자가 요청한 GitHub main 업데이트는 별도 진행한다.
