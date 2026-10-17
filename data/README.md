# 로컬 데이터

시연 입력은 videos/의 6개 MP4입니다. 최신 구성은 videos/README.md와 configs/team-runtime-index.json을 따릅니다. 학습 이미지·수동 라벨·출처·검수 분할은 모델 제작 및 선정 근거이므로 보존하며 실행에는 필요하지 않습니다. Git에서는 학습 데이터를 제외합니다.

- reviewed_pilot/: 최종 모델 학습 자료, 비교 후보 학습 자료, 수동 정답·선정 이력. 이름에 v1/v2/1200/1600이 있어도 실행 모델이라는 뜻은 아닙니다.
- pilot_v1/, training_review/, label_review/, annotation_candidates/, external/: 원천·라벨·검수·출처 자료. 파일 경로가 configs/review/의 선정 기록에서 참조되므로 일괄 삭제하지 않습니다.
- 현재 PPE 학습셋: reviewed_pilot/ppe_balanced_800/ (착용400장·미착용400장).
- 현재 지게차 주력 학습셋: reviewed_pilot/forklift_real_context_v2/ (690장). 마지막1000장 후보는 비채택.
- fire_current/: 화재 보완 검증390장. 추가 학습 후보는 비채택, 실행은 공개 모델 유지.

같은 이름·이미지 수와 같은 사진/라벨을 동일시하지 않습니다. 학습 자료 삭제는 최종 실행 파일 정리와 구분합니다.
