# 영상 체류 규칙 연결 완료 — 시연용 ROI

scripts/run_zone_dwell_video.py에서 검출 → 사람 추적 → ROI → 관측 체류시간 → 상태 변화 이벤트를 실제 영상에 연결했다. configs/cameras/dwell-demo.json의 정규화 좌표를 해상도에 맞춰 변환한다. 입력 영상 이름·해시가 바뀌면 ROI 재검토가 필요하다. 장면 전환을 감지하면 기존 ROI를 비활성화하며 새 장면에 그대로 사용하지 않는다.

구역은 왼쪽 설비 작업영역에 그린 시연용 ROI다. 해당 작업이 허가됐는지/실제 출입금지인지 확인하지 않았으므로 현장 위반으로 단정하지 않는다. 사람 박스 하단 중앙은 발 위치의 대용값이며 앉거나 가려진 사람의 실제 발 위치와 다를 수 있다.

## 실행
```sh
conda activate safety
python scripts/run_zone_dwell_video.py --source data/videos/4_hazard_zone_dwell.mp4 --config configs/cameras/dwell-demo.json --weights models/pilot_v8_preserved_head/person_forklift.pt --output outputs/video_validation/new_dwell_run
```

이 실행기는 v8을 이 영상의 실험 후보로 사용한다. v8은 작은 공통 객체 시험에서 퇴행했으며 프로젝트 기본 모델로 승격하지 않았다. 원래 사전학습 사람 모델도 동일 설정으로 비교했다. 학습/시연 자료의 같은 공장 환경 중복 및 반복 시험 때문에 독립 현장 평가가 아니다.

## 실제 실행 결과
19.06초 체류 영상에서 1280 입력 크기, 약4.795fps/92프레임 처리. 자체 v8의 앉은 작업자 ID0:9를 첫 관측 2.5025초부터 계산한다. 영상 시작부터 약2.5초는 놓쳤으며 그 시간을 소급해 더하지 않는다.

- 2.5025초: SAFE, 관측 체류0초.
- 5.6306초: WARNING, 관측 체류3.1281초.
- 11.4698초: CRITICAL, 관측 체류8.1331초.
- 검출이 빠진 8.7588/10.0100/13.5552/17.9346초 구간 등은 severity=null, unconfirmed. 누락 시간 및 복귀 직전 미관측 구간은 누적하지 않는다.
- 이 ID 최대 관측 체류14.5979초. 사전학습 비교도 약14.5979초이며 사람 ID는0:8로 별도 실행에 종속된다.

관측 누적 시간이지 누락 구간까지 증명된 연속 체류시간은 아니다. 검출 누락/ID 교체는 시간 과소계산·초기화를 일으킬 수 있다. v8에서 35개 상태 변화 이벤트가 기록됐고 CRITICAL ID는 하나다. 이는 이벤트 관측 개수이며 실제 인원·정확도가 아니다.

## 팀에 넘기는 출력
- zone_dwell.mp4: ROI·사람 ID·관측시간·상태를 표시한다.
- observations.jsonl: 매 처리 프레임의 현재/누락 트랙과 체류 이벤트.
- events.jsonl: 최초 관측, 상태/입출입/미확인 전환에만 이벤트를 기록한다.
- summary.json: 입력·가중치 SHA-256, ROI 설정, 처리 FPS/크기, 진단 요약.

event_type=zone_dwell, camera_id, roi_id, track_id, timestamp_seconds, inside, observed_dwell_seconds, observation_status, severity를 사용한다. severity는 SAFE/WARNING/CRITICAL 또는 미확인 null. scope=configured_demo_dwell_rule이며 화면 전체의 안전을 뜻하지 않는다. global_safety_status는 not_evaluated를 유지한다. 검출 없음은 빈 이벤트+unconfirmed이며 자동 SAFE가 아니다.

규칙은 관측 체류≤3초 SAFE, 3초 초과~8초 미만 WARNING, 8초 이상 CRITICAL. 실제 프레임 시간 간격 때문에 정확히3/8초에 프레임이 없으면 다음 관측에서 전환한다. 이 단계의 이벤트는 파일 기록이며 외부 메시지/사이렌 전송은 하지 않는다. 통합 경계·누락·장면 전환 테스트를 포함17개 테스트 통과.
