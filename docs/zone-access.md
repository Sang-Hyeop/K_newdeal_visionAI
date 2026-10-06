# 위험구역 접근·침범 규칙 연결

src/zone_access.py와 TrackedZone의 선택 기능을 연결했다. configs/cameras/zone-access-demo.json은 기존 설비 ROI에 접근 여유영역을 추가한다. 체류와 접근은 zone_dwell/zone_access 두 종류의 이벤트로 구분한다. SAFE는 해당 규칙에서의 상태이며 현장 전체 안전을 뜻하지 않는다.

## 규칙
- 사람 박스 하단 중앙의 대용 발점이 ROI 밖이고 경계에서 충분히 멀면 SAFE.
- ROI 밖에서 경계 거리 54px 이하이면 WARNING. 기준은 min(1920,1080)×0.05이며 실제 미터 거리가 아니다. 이동 방향을 추론한 것이 아니라 가까움의 관측이다.
- ROI 경계/안쪽은 CRITICAL. 처음 관측부터 안에 있으면 구역 내 존재이고 entry_observed=false다.
- 같은 ID로 누락 없이 외부→내부가 관측됐을 때만 entry_observed=true. 누락 후 내부에서 복귀하면 진입 과정을 증명하지 못하므로 false.
- 판단할 수 없으면 severity=null/unconfirmed. authorization_status=not_assessed이며 무단 출입 권한을 판단하지 않는다.

## 영상 검증
기존 체류 영상 92프레임, v8 실험 모델, 입력1280, 처리 약4.795fps로 실행. 걸어오는 작업자 ID0:6의 시연 ROI 접근은 약15.8492초 WARNING, 약16.0577초 CRITICAL/진입 관측. 이후 화면 아래로 잘린 구간은 발 위치를 미확인으로 처리해 이탈 이벤트를 만들지 않는다. 전체 접근 관측은 SAFE190/WARNING2/CRITICAL83/UNKNOWN82, 진입1/이탈0. 관측 개수는 실제 인원이나 정확도가 아니다.

초기 구현에서 화면 경계로 잘린 사람의 박스 끝을 사용해 이탈 오기록이 발생했다. 회귀 테스트와 입력 보완으로 해결했다. ROI 판단은 추적기의 보정 박스 대신 현재 검출 박스를 사용하며, 하단이 높이-1 이상으로 잘리면 규칙 입력에서 제외한다. 실제 발이 가려진 경우의 다른 오차는 여전히 가능하다.

체류는 별도 규칙이므로 내부 진입 직후 zone_access=CRITICAL이어도 zone_dwell=SAFE일 수 있다. 영상은 각 규칙 이름을 표시하고 박스 색은 두 규칙 중 높은 상태를 사용한다. ROI가 실제 금지구역으로 확인된 것은 아니며 authorized 작업자와 무단 진입을 구별하지 않는다. 현재 성공은 시연용 구역 규칙의 동작이다.

## 실행과 저장
```sh
conda activate safety
python scripts/run_zone_dwell_video.py --source data/videos/4_hazard_zone_dwell.mp4 --config configs/cameras/zone-access-demo.json --weights models/pilot_v8_preserved_head/person_forklift.pt --output outputs/video_validation/new_access_run
```

최신 결과는 outputs/video_validation/zone_access_v4/trained_v8. events.jsonl은 규칙별 상태 변화, observations.jsonl은 프레임별 전체 관측, summary.json은 설정/해시/집계다. 23개 테스트 통과. 모델은 승격하지 않았으며 PPE/지게차–사람 충돌 위험 모듈 완료를 뜻하지 않는다.
