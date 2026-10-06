# 기존 train 자료 활용 — 2026-10-06

## 실제 확인 범위
접근 가능한 사용자 폴더와 연결된 볼륨의 파일 목록을 재검색했다. 파일 493,464개, 압축 경로 744개, 영상 경로 959개가 검색되었으며 접근 오류 출력은 499줄이다. 중복 파일 경로가 있을 수 있다. 전체 파일의 내용을 읽거나 전체 압축을 해제한 결과가 아니다. 관련 압축 내부 목록은 outputs/data_audit/train_source_reaudit/archives.json에 기록했다. ZIP 목록 확인만으로 전체 CRC나 라벨 정확성이 검증되지는 않는다.

## 추가 학습 자료
logistics_v5_train_sources: 학습 146 / 검증 8 / 테스트 11장. 기존 v4의 58장에 TS_04 원본 train 이미지 100장과 Safe and Unsafe Behaviours의 train 영상 7개에서 추출한 사람 크롭 7장을 추가했다. 원본 이미지 100장은 좌표·클래스·해상도 자동 검사 및 7장 표본 시각 검수를 통과했으며, 100장 전체 수동 검수 완료로 주장하지 않는다. 영상 크롭은 보이는 사람 몸의 박스를 수동 작성했다. 애매한 크롭 5는 제외했다. TS_07 후보 64장은 지게차에 화물을 포함하는 라벨이 발견되어 추가하지 않았다.

검증·테스트 이미지와 라벨은 v4와 바이트 단위로 동일하다. 시연 mp4 7개의 SHA-256과 추가 train 원본 영상의 SHA-256은 겹치지 않는다. 단, 일부 train 영상은 시연과 동일 공장 카메라 환경이므로 시연 성공을 새로운 현장 일반화로 해석하지 않는다. 크롭 감지와 전체 CCTV 감지의 난이도도 다르다.

## 실행 및 재현
safety Python으로 scripts/prepare_train_source_expansion.py를 실행한다. 원본 ZIP과 data/training_review/train_archives_v1/candidates.json 및 train_videos_v1 검수 크롭이 필요하다. 기존 데이터 보호를 위해 대상 폴더가 있으면 중단한다. configs/review/train-sources-v1.json에 원본 위치, 좌표, 검수 수준, 영상 해시를 남겼다.

추가 학습은 기존 logistics_pilot_v4 best.pt를 초기값으로 10 epoch 진행한다. 모델과 결과는 outputs/training/logistics_pilot_v5_train_sources에 저장되며 개발 단계 모델이다. 안전·주의·위험 판단은 이 모델의 클래스가 아니라 추적·ROI·거리·체류 후처리에서 구현한다.

## 완료 결과
10 epoch 학습 및 고정 임계값(confidence 0.25, IoU 0.5) 비교 완료. v4 → v5: 사람 TP 12→9 / FP 5→5 / FN 6→9; 지게차 TP 9→7 / FP 5→2 / FN 2→4. 누락 증가로 v5를 기본 모델로 승격하지 않는다. 기존 v4를 개발 기준으로 유지한다. 체류 영상 15초의 보행자는 v5가 검출했으나 앉은 작업자는 계속 누락된다. 일반화와 전체 화면 감지가 해결된 상태는 아니다. 새 가중치는 models/pilot_v5_train_sources/person_forklift.pt 및 status.json에 보존했다.
