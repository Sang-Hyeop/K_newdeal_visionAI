# 지게차 라벨 보완 실험

2026-10-06. v5에서 데이터 추가 후 고정 테스트의 누락이 증가했다. 변경 영향을 분리하기 위해 v4를 기준으로 TS07 train 후보 8장을 수동 검수하고 추가했다. v5의 새 이미지 107장은 이번 데이터에 포함하지 않는다.

검수 ID: 101, 105, 109, 113, 117, 129, 145, 161. 사람 박스는 보이는 작업자와 대조했다. 지게차 박스는 차량·마스트·보이는 포크를 포함하되, 차량 밖으로 뻗은 화물 때문에 확장하지 않았다. 사각형 내부에 겹쳐 보이는 화물은 사각형 라벨에서 제거할 수 없다. 화면 경계로 잘린 마스트는 경계까지 포함했다. 수정 좌표와 원본 출처는 configs/review/corrected-forklift-v1.json에 기록한다. 모든 후보 64장이 검수된 것은 아니다.

구성: train 47 / val 8 / test 11장. 원본 영상 그룹과 정확한 이미지 해시 중복 검사, 좌표 범위 검사 통과. 검증·테스트 파일은 v4와 바이트 단위로 동일하다. 시연 영상은 추가하지 않았다. 작은 개발용 테스트이며 최종 독립 평가가 아니다.

실행: safety 환경에서 scripts/prepare_corrected_forklift_expansion.py로 데이터 생성. scripts/train_reviewed_pilot.py에 dataset logistics, data-path data/reviewed_pilot/logistics_v6_corrected_forklift, weights outputs/training/logistics_pilot_v4/weights/best.pt, learning-rate 0.0001, epochs 8, run-name logistics_pilot_v6_corrected_forklift를 지정한다. optimizer는 AdamW, warmup은 1 epoch다. 가중치 교체 여부는 학습 완료 후 진단 결과와 영상 확인을 거쳐 기록한다.

## 완료 결과
8 epoch 학습 및 test 감사 완료(conf=0.25, IoU=0.5). 사람 TP 12 / FP 5 / FN 6으로 v4와 동일. 지게차 TP 10 / FP 2 / FN 1로 v4의 TP 9 / FP 5 / FN 2보다 개선. 하지만 체류 영상 및 전진 영상의 0·7.5·15초 표본에서 전체 화면 감지 문제가 지속되고 일부 사람 감지도 퇴행했다. 전진 영상의 표본 3프레임에서 두 모델 모두 지게차를 검출하지 못했다. v6는 기본 모델로 승격하지 않고 실험 가중치와 상태를 models/pilot_v6_corrected_forklift에 보존한다. 다음은 유사 카메라 각도의 train 장면과 전체 화면 사람 누락 라벨 보완이다. 검증에 쓴 시연 프레임은 train에 넣지 않는다.
