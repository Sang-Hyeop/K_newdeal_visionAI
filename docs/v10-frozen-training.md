# v10 특징층 고정 비교 결과

v6 초기 모델·동일85장·640·AdamW0.0001·12epoch·seed20261006, 앞10층 고정으로 학습 완료. v9와 데이터85장의 이미지/라벨SHA 및 초기가중치SHA가 같음을 확인했다. 모델 앞10층의99개 parameter tensor가 원본과 동일하다. BatchNorm의 running buffer나 전체 모델 고정을 뜻하지 않는다. 이 비교는 전체학습 방식을 고정하는 효과이며 epoch별 best 선택 결과를 비교한다.

동일 개발시험11장 conf0.25/IoU0.5: v6 사람TP12/FP5/FN6·지게차TP10/FP2/FN1; v9 사람TP8/FP3/FN10·지게차TP9/FP2/FN2; v10 사람TP11/FP6/FN7·지게차TP8/FP3/FN3. 직전v9의 사람 누락은 줄었지만 v6를 전반적으로 넘지 못해 experimental_not_promoted 유지.

전진·후진 각0/5/10/15/20초 대표 프레임의 v6/v10 비교와 각106샘플프레임 전체 구간 근접 모듈 실행을 마쳤다. 전진 확인가능쌍 없는 프레임106/106, 상태변화이벤트0. 화면변화12.095/16.058초에서기존ROI비활성화. 후진 SAFE48/WARNING2/UNKNOWN12 쌍관측, 확인가능쌍없는프레임56/106, CRITICAL0. 관측수는 인원/정확도/안전 여부가 아니다. 후진12.6초에서는 설비를지게차로오탐하여SAFE후보가생성됐음을눈으로확인했다. 실제지게차는그장면에있지만놓쳤다. 바닥ROI안에서도설비오탐이남아ROI만으로검출오류를해결하지못한다. 로그의 confirmed는기하규칙계산가능상태이며객체종류의정답검증이아니다. 전역안전은not_evaluated로유지.

신뢰도기준/거리규칙/ROI는결과에맞춰변경하지않았다. 시연프레임은학습에넣지않았으나개발확인에반복사용했으므로최종독립평가가아니다. 실제거리/앞뒤/충돌가능성은검증되지않았다.

재현: safety환경에서 scripts/train_reviewed_pilot.py에 --dataset logistics --data-path data/reviewed_pilot/logistics_v9_hard_examples --weights models/pilot_v6_corrected_forklift/person_forklift.pt --epochs 12 --learning-rate 0.0001 --freeze 10 --run-name logistics_pilot_v10_frozen_backbone. 원본/결과경로는덮어쓰지않는다. 같은조건고정임계값평가는 scripts/audit_pilot_predictions.py,대표프레임비교는 scripts/probe_forklift_v9.py의 --candidate-weights/--candidate-label/--output으로실행한다.

모델과생성영상포함16파일SHA복구사본저장,동일디스크백업이며외부백업아님. 로컬Git체크포인트, 이번단계GitHub push/main병합없음. 기존모델을자동교체하지않았다.

다음우선순위는소량자료에서epoch/고정범위반복탐색보다이미받은여러현장자료의검수학습규모확대이다. 산업설비/적재물배경,가려진작업자·운전자,전진방향지게차사례를균형있게추가하고그룹/현장분리를유지한다. 현재객체모델은안정적인전체시연수준에못미친다.
