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
