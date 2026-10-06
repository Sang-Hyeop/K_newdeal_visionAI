# 작업자 추적 연결 — 개발 진단

src/person_tracker.py는 설치된 Ultralytics 8.4.153 ByteTrack API를 감싼다. 사람 검출만 입력하며 낮은 신뢰도 0.1 초과 검출은 기존 ID 연결에 활용하고 신규 ID는 0.25 이상에서 시작한다. 실제 처리 FPS에 맞춰 1초 누락 버퍼를 지정한다. 추적 ID는 장면번호:지역ID 형태이며 장면 변경·1초 초과 입력 시간 공백에는 초기화한다. 타임스탬프는 영상 프레임/FPS이며 엄격히 증가해야 한다.

추적기가 반환한 현재 관측만 PPE 검사한다. 누락된 ID는 bbox를 지어내지 않고 observation_status=unconfirmed, ppe_state=unknown으로 기록한다. 이전 안전모 상태를 누락 구간에 복사하지 않는다. 각 ID는 실제 신원이 아니라 추적 가설이다.

scripts/validate_tracked_ppe.py는 사람 추적, 전체화면+확대 PPE, 영상/JSONL을 연결한다. 평균 축소 영상 색 차이 0.18을 장면 전환 초기 기준으로 사용한다. 자동 전환 감지는 휴리스틱이며 같은 배경 컷/움직이는 카메라에 대한 보장이 없다. 최초 0.22는 걷는 영상 전환을 놓쳤고 0.18로 수정했다. 두 영상 모두 첫 전환을 약 6.048초에서 기록했다. 위험 알림 시간표를 지정한 것이 아니다.

```sh
conda activate safety
python scripts/validate_tracked_ppe.py --source data/videos/6_Helmet_forklift.mp4 --output outputs/video_validation/new_tracked_run --objects-weights outputs/training/logistics_pilot_v4/weights/best.pt --ppe-weights models/pilot_v3_ppe_expansion/ppe.pt
```

## 실제 영상 검증
두 PPE 영상 각각 58프레임, 처리 FPS 약 4.795. 자체 모델 v4를 쓴 결과는 outputs/video_validation/tracked_ppe_v3_trained, 원래 사전학습 사람 모델과 같은 코드의 비교는 tracked_ppe_v3. 최종 모델 교체는 아니다. 반복 진단에 사용한 시연이며 독립 평가가 아니다. ID 정답이 없어 ID 정확도/실제 인원 수를 측정하지 않았다.

6_Helmet_forklift의 약 10.4초 장면에서 사전학습 사람 모델은 후드 작업자를 포함해 5명의 박스를 검출했고 v4는 다수를 누락했다. 사전학습 비교의 두 번째 장면에서 5개 ID가 약 5.84초/29관측 동안 유지됐지만, 같은 사람이라는 정답 매칭이 없어 전체 추적 성능 수치로 해석할 수 없다. 자체 모델의 검출 누락이 추적 불안정에 영향을 준다.

머리 후보가 여러 사람의 상단 영역에 걸리면 가장 가까운 머리 기준점의 사람에게 배정하고 동률은 미배정한다. 겹침으로 이웃의 안전모를 연결하는 문제를 줄이는 위치 휴리스틱이며 머리 식별을 보장하지 않는다. 추가 회귀 테스트로 이웃 안전모가 전경 사람을 착용으로 표시하는 입력을 거부함을 확인했다. 실제 영상에는 후드를 helmeted_head로 오탐하는 경우가 여전히 있다. helmet_detected는 모델의 검출 관측이지 착용이 확인된 사실이나 SAFE 판정이 아니다. 모든 risk_status는 not_evaluated다.

추적 4개, PPE 7개, 체류 3개 합계 14개 테스트 통과. 현재 병목은 자체 사람 모델의 퇴행과 후드/작은 머리 PPE 오탐이다. 추적 ID를 위험구역 체류에 연결하려면 카메라 ROI를 정하고 실제 입출입·누락 동작을 검증해야 한다. 현재 체류 모듈은 아직 이 실행기에 연결하지 않았다.
