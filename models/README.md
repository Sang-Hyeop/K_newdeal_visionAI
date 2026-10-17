# 기존 확정 모델 6개 + 추가 화재 모델 1개

현재 실행에 필요한 아래 모델만 유지합니다. 연결·해시는 configs/team-runtime-index.json이 기준입니다.

- pilot_v16_related/person_forklift.pt: 사람·지게차 기본.
- demo_object_adaptation_v1/best.pt: 시연 장면 보완.
- pretrained/yolo26n.pt: 사람 검출.
- ppe_final/ppe_helmet_v6_960.pt: 현재 PPE(800장 균형 보완학습, 영상 검증으로 선택한1회차; v6는 호환용 기존 파일명). 같은 폴더 config.json과 ppe_duplicate_filter.py도 필요합니다.
- experiments/forklift_real_context_v2/weights/best.pt: 현재 사용하는 차량 보완 모델. experiments라는 경로명과 달리 대체 후보가 아니라 기본 실행의 구성원입니다.
- nvidia_object_adaptation_v1/best.pt: 차량 교차 확인.

성능이 떨어졌던 1577장 PPE 후보는 채택하지 않고 삭제했습니다. 라벨·학습 데이터는 data/에 보존하며 실패 과정은 Git 이력에 있습니다. 현재 로컬 보완은 아직 공개 Release에 반영하지 않았습니다.


## 추가 화재 검수 모델 (2026-10-17)

기존 확정6개는 유지하며6번 전용 `fire_public/fire_detection.pt` 한 개를 추가합니다. 공개 YOLO26-S 가중치를 재학습 없이 사용합니다. 출처/게시자 MIT 선언/학습자료 CC BY4.0 선언/정확한revision·SHA 및 한계는 `configs/review/fire-current.json`과 동봉MODEL_CARD.md에 기록했습니다. Ultralytics 구현 라이선스는 별도로 적용됩니다. 불꽃 반복관측 기반 화재 의심이며 연기만으로 알리지 않습니다. 아직 기존 GitHub Release에는 포함하지 않았습니다.
