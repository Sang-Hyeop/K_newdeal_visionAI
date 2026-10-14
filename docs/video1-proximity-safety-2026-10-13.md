# 1번10.84초 위험 관계가 정상으로 가려진 오류 수정

이전 결과의10.84초에서 앞쪽 차량 bbox=[351,156,733,556], 작업자 bbox=[414,343,519,564]가 대부분 겹쳤다. Proximity는 겹침80% 이상을 possible_operator_or_occluded_person으로 미확인 처리했다. runner/render의 운전자 추정 필터가 그 관계를 삭제했고 뒤쪽 차량 SAFE 관계만 남아 화면과 저장 이벤트가 SAFE가 됐다. 실제 운전자라는 증거 없이 겹침만으로 관계를 제거한 것이 원인이다.

겹침만으로 관계를 삭제하지 않는다. operator_confirmed 명시 근거가 없는 가까운 미확인은 유지하고, 멀리 있는 SAFE가 가리지 않도록 집계/표시한다. 최초 겹침이나 오래된 근거는 UNKNOWN을 유지한다.
1번 설정에만 recent_pedestrian_overlap을 활성화한다. 같은 사람·같은 차량 쌍에서 최근1초 이내 관측한 낮은 겹침과 차량 박스 밖 발점 근거가 있으며, 현재도 발점이 차량 박스 밖일 때 최근 보행자 근거를 활용해 기존 화면상 거리 판정을 유지한다. 발점 여유는 max(2px,사람높이2%). ID/장면이 바뀌거나 근거가 오래되거나 발점이 내부면 보행자로 확정하지 않는다. 다른 카메라에는 이 보행자 보완 옵션을 자동 활성화하지 않는다. 이는 개발 카메라의 영상 기하 휴리스틱이며 실제 운전자 분류나 물리적 충돌 예측 검증이 아니다.

1번106표본 재실행: 이전 실행과 객체 검출·시점 전부 동일.10.84초에서 P0:5/F0:4의 거리비0.03 CRITICAL 유지, 뒤차 F0:6 SAFE는 위험을 덮지 않는다. 대상 프레임 육안 확인. 최초 겹침/만료 근거 UNKNOWN, 가까운 UNKNOWN+멀리 SAFE 집계 UNKNOWN 회귀 포함 총160개 자동 테스트 통과.
새 학습·고정 시각 위험 강제·좌표별 차량 숨김 없음. 이전 적재물 오탐 보완 유지. PPE 오류는 별도 리뷰가 필요하다.

영상: outputs/diagnostics/video1_proximity_safety_v4_verified/video1/demo.mp4
대표화면: outputs/diagnostics/video1_proximity_safety_v4_verified/video1/review_10.84s.jpg
검증/해시: docs/checkpoints/2026-10-13/video1-proximity-safety/verification.json
