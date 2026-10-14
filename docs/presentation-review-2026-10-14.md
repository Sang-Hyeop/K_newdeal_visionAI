# 최종 발표 영상 리뷰 진행 (2026-10-14)

## 1번: 사용자 리뷰 통과

사용자가 두 오탐 정정 후 최신 영상에 대해 "1번 영상 통과"라고 확인했다. 베타 테스트 후보 입력은 1_forklift_worker_collision_risk.mp4, 결과는 outputs/reviews/1_forklift_worker_collision_risk_latest.mp4다. 현장 일반화 검증 완료를 뜻하지 않는다.

## 2번: ROI 침범 리뷰 대기

입력: data/videos/2_restricted_zone_intrusion.mp4. 로봇팔 앞 빨간 바닥의 경계를 ROI 초안으로 지정했다. 작업자 발점(현재 사람 박스 아래 중앙)이 들어가면 즉시 CRITICAL이며 체류시간 조건은 없다. 경계 인근은 WARNING, 밖은 해당 ROI 규칙상 SAFE다. PPE는 별도 감지·판정한다.

사람: 기존 COCO yolo26n 1280 추론. PPE: 현재 선정 v6 960 + 사람 주변 확대 추론. 머리 가림·불확실 관측은 판정 불가로 남긴다. 모델 선택을 이 새 영상에서 모든 모델 비교를 마친 최고 성능으로 해석하지 않는다.

실행:

```bash
conda activate safety
python scripts/run_intrusion_review.py --output outputs/diagnostics/presentation2_new_run
```

코드: scripts/run_intrusion_review.py. 카메라 설정: configs/cameras/robot-intrusion.json. 기존 1~7번 실행 번호와 분리된 새 발표 2번 실행 진입점이다.

결과: outputs/reviews/2_restricted_zone_intrusion_latest.mp4. 로그: outputs/diagnostics/presentation2_intrusion_review_2026-10-14/{zone_access,ppe}/{events_v1,observations_v1}.jsonl. 공유 이벤트 계약과 상태/알림 분리 필드를 사용한다.

실제 58개 관측 샘플(4.8fps)을 처리했고 약 5.42초에 첫 위험이 관측됐다. 모든 확인된 ROI 내부 관측이 즉시 CRITICAL인지, 진입 전환 로그가 있는지 확인했다. MP4 전체 58프레임 디코딩, 기존 테스트 210개 통과. ROI는 사용자 경계 리뷰 전이며 AI 생성 영상의 시연 결과다. 평가 항목 3·4·8(규칙, 전체 처리 흐름, 시연·인계)에 기여한다.

## 2번 사용자 피드백

사용자가 결과가 잘 나온다고 확인하고 3번 리뷰로 진행했다.

## 3번: 안전모 리뷰 대기

현재 3_PPE_Helmet.mp4는 기존 5_PPE_Helmet.mp4와 SHA-256이 동일하다. 내부 시나리오 5의 현재 선정 v6 + 사람 주변 확대 추론 설정·모델 해시를 검증하고 실제 탐지 캐시를 재사용했다. 현재 상태 구분·이벤트 필드·화면을 다시 생성했다. 재학습은 없다.

결과: outputs/reviews/3_PPE_Helmet_latest.mp4. 로그: outputs/diagnostics/presentation3_ppe_review_2026-10-14/video5/ppe/. 약 12초 전체 58개 프레임 디코딩 확인. 58개 분석 프레임 중 PPE WARNING 36, SAFE 1, UNKNOWN 21. 이는 정확도나 사람 수가 아니며, 초반 가려진 작업자와 일부 머리 미확인이 남는다.

## 3번 사용자 피드백

사용자가 3번 확인 후 4번 리뷰로 진행했다.

## 4번: 위험구역 체류시간 리뷰 대기

입력은 확정한 4_hazard_zone_dwell.mp4. 기존 v9와 원본·모델·객체 검수 프로필 해시를 검증해 실제 탐지 캐시를 재사용하고, 현재 체류 규칙·상태 표시·이벤트를 재생성했다. PPE v6 + 사람 확대 추론을 유지한다.

결과: outputs/reviews/4_hazard_zone_dwell_latest.mp4. 이벤트는 outputs/diagnostics/presentation4_dwell_review_2026-10-14/video4/{zone_access,zone_dwell,ppe}/에 저장했다. 실제 지게차 없는 영상이므로 통로 체류 3초부터 최대 WARNING이며 체류만으로 CRITICAL을 만들지 않는다. 전기 제어실의 허가 ON/OFF 및 3초 주의·6초 위험 규칙을 이 영상에 적용하지 않았다.

전체 92개 분석 프레임 디코딩 확인. 지게차 검출 0, 체류 WARNING 표시, 체류 CRITICAL 0을 검증했다. 일부 가림·화면 아래로 잘린 발점은 미확인으로 남는다. 결과 해시는 실행 폴더 review_verification.json에 기록했다.

## 4번 추가 보완: 왼쪽 위 가장자리 기계

사용자가 약 3.34초 왼쪽 위 가장자리 PERSON 0.42를 실제 기계라고 확인했다. 기존 제외 영역과 별도 위치여서 새 카메라별 고정 설비 영역을 configs/video4-object-review.json에 추가했다. 해당 설비에 대부분 포함되는 사람·머리 후보를 추적·PPE 연결 이전에 제외하고 진단 사유를 남긴다. 시간 지정 규칙 없이 영상 전체에 적용한다. 바로 오른쪽 작업자와 부분적으로 걸친 일반 작업자는 제외하지 않는 회귀 검사를 추가했다.

이 보완은 해당 고정 카메라 후처리이며 재학습은 아니다. 카메라나 설비 위치가 바뀌거나 사람이 설비 앞을 가리는 경우 영역 재검수가 필요하다. 기존 통로 ROI와 3초 주의 기준은 유지한다. 검증 결과는 outputs/diagnostics/presentation4_equipment_corrected_2026-10-14/video4/review_verification.json에 기록한다. 평가 항목 3·6·8에 기여한다.

4번 보완 검증: 기계 PERSON 오탐 6개 제거, 그 외 객체 검출 339개는 이전과 전부 일치. 3.34초 오른쪽 실제 작업자 유지 확인. 지게차 검출 0, 체류 CRITICAL 0 유지. 테스트 212개·전체 92프레임 디코딩 통과. 최신 재생 경로 outputs/reviews/4_hazard_zone_dwell_latest.mp4를 새 결과로 교체했다.

## 4번 중복 사람 및 표시 정리

사용자 승인 범위: 4번에서 같은 작업자의 중복 검출을 정리하고 몸 박스 하나에 통로·체류·PPE 상태를 문구로 표시한다.

카메라 프로필의 deduplicate_person_containment를 켜고, 서로 다른 모델의 사람 후보가 작은 박스 면적의 85% 이상 겹치며 가로 중심·발점이 가까울 때만 낮은 신뢰도 후보를 제외한다. 추적 전에 적용하고 제외 후보의 출처와 사유는 진단 로그에 남긴다. 인접 작업자와 발점이 다른 겹친 사람을 보존하는 회귀 검사를 포함한다. 과밀·완전 가림 장면의 일반 해법으로 보장하지 않으며 해당 카메라의 리뷰용 설정이다.

dwell-demo의 compact_person_display 옵션으로 사람별 몸 박스를 한 번만 그린다. 기존 사람·구역·머리 박스를 중복해서 그리지 않고 PERSON, LANE IN/OUT·체류초·판정, PPE 상태를 문구로 묶는다. 위험·검토 후보·판정 불가는 구분하며 이벤트 로그의 기능별 근거는 유지한다. 다른 영상 설정은 변경하지 않았다. 모델 재학습과 위험 임계값 변경은 없다.

평가 항목 3·5·6·8(중복 집계, 화면 이해, 회귀 검증, 인계)에 기여한다. 실행 결과·해시는 outputs/diagnostics/presentation4_compact_review_2026-10-14/video4/review_verification.json에 기록한다.

4번 중복 정리 검증: 전체 92개 분석 프레임에서 중복 사람 후보 17건 제외, 나머지 사람 후보 322건은 정리 규칙 적용 전후와 일치. 지적된 8.76초 작업자의 사람·PPE 추적은 각 1개로 확인했다. 지게차 검출 0·체류 CRITICAL 0 유지. 테스트 217개 및 결과 전체 92프레임 디코딩 통과. 최신 MP4 경로를 새 결과로 교체했다.
