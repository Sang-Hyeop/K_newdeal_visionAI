# 기능별 이벤트 감지 연결 v1

근접은 `src/tracked_proximity.py`, 구역은 `src/tracked_zone.py`로 분리한다. 선택모델은v16이다. 근접은 화면 전체의 검출·추적 결과로 화면상 근접을 판단한다. 구역은 카메라별 다각형ROI와 발점 대리 좌표로 접근/내부 관측 및 체류시간을 판단한다. 실제 출입 권한·충돌 발생을 판정하는 기능은 아니다.

`scripts/run_proximity_video.py`는 전진/후진 설정의 full_frame 및 image_plane 모드를 요구한다. 과거 바닥ROI 필드가 포함된 근접 설정은 명시적으로 거부한다. 장면 전환은 추적·쌍 상태만 초기화하고 새 장면에서 판단을 이어간다. 구역 영상은 장면 전환 시 고정ROI를 비활성화한다.

실행 예시(저장소 루트, safety 환경):

```sh
conda activate safety
python scripts/run_proximity_video.py --source data/videos/1_forklift_forward.mp4 --weights models/pilot_v16_related/person_forklift.pt --config configs/cameras/forward-proximity.json --output outputs/demo/new_forward
python scripts/run_zone_dwell_video.py --source data/videos/4_hazard_zone_dwell.mp4 --weights models/pilot_v16_related/person_forklift.pt --config configs/cameras/zone-access-demo.json --output outputs/demo/new_zone --imgsz 1280
```

출력 폴더는 새 경로를 지정한다. 거리 단위는 사람 높이로 정규화한 영상 거리이며 distance_meters는null이다. 확인된 실제 길이·카메라 보정이 없는 m 표시는 지원하지 않는다. 구역의 3/8초 경계와 접근/내부 기준은 구역 설정에만 적용한다.

팀 전달 형식은 `docs/detection-output-contract.md`를 참고한다. `events_v1.jsonl`은 로그 저장, `observations_v1.jsonl`은 최신 프레임 상태 배너에 사용한다. SAFE는 해당 관측 대상·기능의 규칙 결과이며 전체 현장 안전이 아니다. 침범CRITICAL을 짧은 체류SAFE가 덮어쓰면 안 된다.

검증 결과는 `docs/checkpoints/2026-10-07/event-module-v1.json`에 기록했다. 36개 테스트와3개 실제 영상 실행/공통출력 검사를 통과했지만, 후진 차량 미탐·설비의 사람 오탐·임시ROI 문제는 남아 있다. 현재 구역 영상에는 실제 금지표지와 권한 규칙이 확인되지 않아 불법/무단 침범의 정답 데이터로 사용할 수 없다. PPE 공통 이벤트 연결은 아직 수행하지 않았다.
