# 첫 시험 학습과 실행

목적은 데이터 → 학습 → 가중치 → 영상·JSONL 출력 연결의 동작 확인이다. 최종 현장 모델 완성으로 해석하지 않는다.

## 이번 데이터
- PPE: 후보 66장 시각 검수 후 53장 채택 (train 37 / val 9 / test 7). P61의 안전모 없는 머리를 class 1로 수정. 누락·불명확·동일 장면 후보 13장은 보류.
- 물류: 446장 중 36장 개별 검수, 31장 채택 (train 22 / val 6 / test 3). 운전자 2개 추가 및 박스 수정. 나머지 410장은 아직 승인하지 않았다. 5장은 검토 후 보류.
- 두 자료 모두 원본은 유지하고 reviewed_pilot에 사본 생성. 개발용 test는 이미 열람되었으므로 최종 독립 성능 평가가 아니다.
- 검수 방법: PPE는 640px 이미지와 라벨 오버레이, 물류는 960px 전체 이미지와 수정 오버레이. 산업현장의 모든 작은 객체를 전문가 정답 수준으로 확인했다는 뜻은 아니다.
- 물류 v2는 L05의 돌출 포크 끝까지 박스에 포함한 버전이며 v1 파일은 유지한다. 직사각형 박스 안에 화물이 겹칠 수 있지만 화물을 독립 객체로 라벨링하지 않는다.

## 재현
safety 가상환경에서 프로젝트 루트 기준으로 실행한다. 생성 스크립트는 기존 출력이 있으면 중단한다.

```bash
conda activate safety
python scripts/prepare_reviewed_ppe.py
python scripts/prepare_reviewed_logistics.py
python scripts/prepare_reviewed_logistics.py --output data/reviewed_pilot/logistics_v2 --review-config configs/review/logistics-pilot-v2.json
python scripts/train_reviewed_pilot.py --dataset ppe --epochs 30 --run-name ppe_pilot_v2
python scripts/train_reviewed_pilot.py --dataset logistics --epochs 30 --run-name logistics_pilot_v2 --data-path data/reviewed_pilot/logistics_v2
```

로컬 사전학습 가중치는 models/pretrained/yolo26n.pt이며 원래 내려받은 일반 사전학습 모델을 복사했다. 이전 PPE 학습 모델은 사용하지 않았다. 설치 환경에서 MPS가 사용 불가로 보고되어 CPU 사용. 이미지 크기 640, batch 4, seed 20261006, workers 0. 실행 args.yaml과 results.csv는 각 학습 출력 폴더에 보존된다.

## 영상 실행

```bash
python scripts/run_pilot_videos.py --source data/videos --sample-fps 2 --objects-weights outputs/training/logistics_pilot_v2/weights/best.pt --ppe-weights outputs/training/ppe_pilot_v2/weights/best.pt --output outputs/pilot_video_v2
```

원본 FPS에 맞춰 약 2fps로 샘플링한다. 출력 재생 시간은 원본과 거의 같지만 움직임은 거칠다. 검출 결과에 원본 frame_index, timestamp_seconds, 클래스, confidence, bbox_xyxy를 기록한다. 영상별 detections.mp4와 detections.jsonl, 전체 summary.json 생성. 검출 횟수는 정확도가 아니며 영상 정답 라벨은 아직 없다.

현재 출력은 순수 검출이다. tracking, ROI, 거리 보정, 사람별 PPE 연결, 위험 이벤트는 아직 포함하지 않는다. risk_status는 not_evaluated이며 검출 실패를 안전으로 바꾸지 않는다. 반복 실행할 때 새 --output 경로를 사용한다.

## 판정
10회 시험 모델은 conf=0.25로 시연 6개 영상 약 2fps 적용 시 검출 0건이었다. 발표 모델로 채택하지 않는다. 학습 횟수를 늘린 두 번째 시험도 별도로 검증하며 충분한 신규 현장·거리·사람 표본 보강이 필요하다.

## 종합 영상 확인
Logistics Warehouse.mp4는 272초의 고정 CCTV로, 30초 간격 표본에서 지게차와 작업자가 함께 보인다. 높은 시점·멀리 있는 작은 작업자가 주요 조건이다. 학습 후보의 가까운 운전자 중심 구도와 차이가 크므로, 높은 시점의 작은 보행자/지게차 자료를 별도 촬영 그룹에서 보강해야 한다. 표본 확인은 전체 위험 발생 시점을 판정한 것이 아니다. 이 영상의 프레임을 학습에 넣지 않았다.

## 두 번째 시험 결과와 채택 여부
PPE는 최대 30회 설정에서 조기 종료로 25회, 물류는 30회 학습했다. 개발용 test mAP50은 PPE 0.7174, 물류 0.8483이다. test가 각각 7장/3장으로 매우 작으며 이 수치는 독립 현장 성능이 아니다.

conf 0.25 / IoU 0.5 고정 기준: 사람 TP0 FP1 FN4; 지게차 TP3 FP1 FN0; 착용 머리 TP3 FP1 FN4; 미착용 머리 TP3 FP4 FN0. mAP와 실제 출력 임계값의 결과가 다르므로 둘을 같이 보존했다.

6개 영상 720개 샘플 프레임을 처리했고 출력 영상 프레임 수와 JSONL 개수·시간 순서를 확인했다. 미리보기에서 작은 작업자 누락, 착용 머리를 몸통까지 잡는 박스, 지게차 박스가 주변 공간과 설비까지 포함하는 문제를 확인했다. 전체 영상 프레임의 정답 라벨은 없으며 전체 정확도나 충돌 감지 성공률은 계산하지 않았다.

models/pilot_v2에 두 가중치와 SHA256·평가·상태 manifest를 보존했다. status=development_only_not_approved_for_presentation. 이 두 모델을 최종 시연 모델로 채택하지 않는다.

val 전용 임계값 진단도 outputs/training/threshold_diagnostic.json에 보존했다. 후보는 사람 0.1 / 지게차 0.3 / 착용 머리 0.2 / 미착용 머리 0.4이며 작은 val 표본의 진단값이다. 이번 6개 영상 평가에는 적용하지 않았다. 임계값을 낮추는 것만으로 일반화 문제를 해결했다고 판단하지 않는다.

다음 필요 작업은 학습 규모·시점·배경 다양성 보강이다. 물류 446개 중 31개 승인 사본, 5개 검토 후 보류, 410개 개별 검수 대기 상태를 logistics-pool-disposition.json에 기록했다. 이 시험으로 446개 전체 라벨 수정이나 전문가 수준 최종 모델 완성이 끝난 것은 아니다. 높은 시점의 작은 보행자, 다양한 지게차 방향, 일반 상자·설비와 차량의 구분, 후드/작은 머리의 PPE 사례를 늘린 후 새 촬영 그룹으로 평가해야 한다.
