# 작업자 확대 PPE 진단

72장 데이터의 라벨 오버레이를 12장씩 6개 시트로 다시 훑어봤다. 대체로 머리 범위이며 몸통 박스가 반복되는 변환 오류는 확인하지 못했다. 축소 시트 검수는 원본 정밀 재라벨링 완료를 뜻하지 않는다. 후드/작은 머리/가림의 불확실성은 남아 있다.

`src/ppe_person_crop.py`는 실제 검출된 사람 박스의 상단 55%와 주변 여백을 잘라 확대 추론한다. 원본 영상 좌표로 복원하고, 머리 중심이 사람 상단에 있는지와 박스 크기를 확인해 몸통 수준의 후보를 거부한다. 비율은 범용 초기 휴리스틱이며 구부린 자세/심한 가림에서는 놓칠 수 있다. 영상별 시간표나 지정 인원 수를 사용하지 않는다.

출력 상태는 helmet_detected / no_helmet_candidate / conflicting_evidence / unknown. 미검출을 미착용이나 안전으로 해석하지 않는다. 미착용은 후보이며 후드·가림을 자동 위반으로 확정하지 않는다. person_index는 해당 프레임의 검출 순번이며 추적 ID가 아니다. 겹친 작업자 사이 일대일 머리 연결은 아직 구현하지 않았다.

## 실행
conda safety에서:

```sh
python scripts/validate_ppe_person_crop.py --source data/videos/5_PPE_Helmet.mp4 --output outputs/video_validation/new_ppe_crop_run --objects-weights outputs/training/logistics_pilot_v4/weights/best.pt --ppe-weights models/pilot_v3_ppe_expansion/ppe.pt
```

## 개발 진단 결과
두 영상 모두 conf=0.25, 1fps 샘플링 12프레임 처리. walking: 사람 관측 38개 중 helmet_detected 8, unknown 30. forklift: 사람 관측 43개 중 helmet_detected 4, unknown 39. 누적 관측 횟수이며 인원 수/정확도가 아니다. 전체 정답 라벨은 없고 독립 평가도 아니다.

걷는 영상 약 5초에서는 전체 화면의 몸통까지 큰 안전모 박스 대신 확대 추론이 두 안전모의 머리 부근 박스를 출력한다. 후드 두 명은 unknown이며, 왼쪽에 구부린 작업자는 사람 검출에서 누락해 검사되지 않는다. 두 번째 영상에서 미확인 관측이 대부분이므로 최종 발표용 PPE 완료로 간주하지 않는다. 다음 보완은 실제 학습용 CCTV의 작은 머리/구부림/후드 사례 라벨과 작업자 검출·추적 안정화다.

비교 영상과 원시 기록은 outputs/video_validation/ppe_person_crop_v1에 보관한다. 위험 판단은 모두 not_evaluated.

## 전체 화면과 확대 검사 병행 보완(v2)
확대만 사용하는 v1은 두 번째 영상에서 원래 검출되던 안전모를 놓쳤다. v2는 전체 화면 후보와 확대 후보 모두에 머리 위치/크기 조건을 적용한다. 동일 조건으로 재실행: walking 사람 관측38 중 착용10/미확인28, forklift 관측43 중 착용16/미확인27. 횟수 증가는 정확도 향상 증명이 아니다. 두 번째 영상 5초에서는 착용4명이 연결되지만 후드 작업자는 사람 검출에서 누락한다. 선반의 사람 오탐도 남아 있다. 후드 작업자의 PPE 상태가 판단된 것이 아니다.

최신 비교 파일은 outputs/video_validation/ppe_person_crop_v2. 테스트는 전체 화면 증거 보존을 포함한 PPE6개 + 체류3개 총9개 통과. 아직 모델 기본값 교체/추적 결합/알림 적용은 하지 않았다.
