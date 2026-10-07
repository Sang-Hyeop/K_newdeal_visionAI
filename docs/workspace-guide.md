# workspace 사용 안내 — 2026-10-07 정리

## 먼저 볼 것

1. 프로젝트 루트 README.md: 시작점.
2. docs/demo-feature-show-plan-2026-10-07.md: 사용자가 확정한 영상별 기능과 규칙. 과거 이력 문장이 섞여 있어 마지막 확정 절과 현재 검증 기록을 함께 읽는다.
3. docs/demo-scenario-runbook-2026-10-07.md: 감지 실행 방법.
4. docs/team-integration-pack-2026-10-07.md: 백엔드·대시보드 연동 계약과 최신 검증.
5. docs/remaining-gaps-2026-10-07.md: 남은 품질 문제.

## 폴더별 역할

- src/: 현재 감지·추적·후처리·이벤트·시연 렌더 코드. 실제 구현은 src/*.py에 있다. detection/events/dashboard 하위 폴더는 초기 분업용 빈 자리이며 구현 완료를 뜻하지 않는다.
- scripts/: 시연 실행과 개발 도구. README.md에서 시연/학습/데이터/평가/렌더 도구를 구분한다. 모든 스크립트가 최종 실행에 필요한 것은 아니다.
- configs/: 현재 모델 선택, 카메라 ROI, 판정 규칙. review/는 라벨·실험 프로토콜이며 전체 시연 실행에 전부 필요하지 않다.
- tests/: 판정·이벤트·추적 회귀 테스트. 배포 영상 실행과 별개지만 변경 검증에 필요하다.
- docs/: 최신 기준·팀 안내·설계. history/training/은 이동한 과거 학습 문서. checkpoints/는 불변 실험 증거와 저장 기록, team-samples/는 연동 예시.
- data/: 원본 시연 영상·학습 데이터·라벨. 동일 원본과 파생 crop이 있어 단순 중복 삭제 금지.
- models/: 현재 채택 가중치 + 이전 실험 가중치. 여러 모델이 있어도 모두 현재 사용되는 것은 아니다. 미채택 모델은 되돌리기·비교에 필요해 보존했다.
- outputs/: 생성 영상·이벤트·학습·평가 결과·추론 캐시. 코드를 실행하면 새로 생성되는 영역이지만 일부 캐시는 현재 재처리 실행에도 쓰이므로 일괄 삭제 금지.
- _local_archive/: 로컬 보관. 이번 cleanup-2026-10-07/에는 재생성 가능한 Python 캐시와 Finder 메타데이터만 이동했다. Git에서 제외된다. 같은 디스크 보관은 외부 백업이 아니다.
- runs/: Ultralytics 임시 결과 위치. 현재 파일 없음. 재생성될 수 있다.

## 현재 채택된 실행 기준

- 기본 진입점: scripts/run_demo_scenarios.py
- 영상 매핑: configs/demo-scenarios.json
- 객체 모델 구성: configs/demo-object-model.json
- PPE 모델 구성: configs/demo-ppe-model.json
- PPE 후보 판정: configs/ppe-recall-review-policy.json
- 후드 보조: configs/demo-hood-model.json — v1 채택, v2 experimental_not_promoted
- 카메라별 설정: configs/cameras/forward-proximity.json, reverse-proximity.json, dwell-demo.json, warehouse-summary.json
- 모델 실파일·해시: docs/checkpoints/2026-10-07/model-share-manifest.json

## 최신 결과 위치

프로젝트 루트: /Users/sanghyeopkim/Desktop/workspace

- 영상 1~4: outputs/diagnostics/scenario_ppe_contract_short/video번호/
- 영상 5~6: outputs/diagnostics/scenario_ppe_contract_hood/video번호/
- 영상 7: outputs/diagnostics/scenario_ppe_contract_verified/video7/
- demo.mp4: 시연 영상.
- summary.json: 모델·입력·설정·상태 집계.
- detections.jsonl: 검출·추적·판정 근거.
- 기능별 events_v1.jsonl: 상태 전환 로그.
- 기능별 observations_v1.jsonl: 최신 상태 스트림.

## 이번에 실제 정리한 내용

- Git 내부를 제외한 전체 파일 목록과 크기를 확인하고, 프로젝트 코드·설정·문서 432개를 읽어 참조 관계를 점검했다. 영상·이미지·가중치는 파일 목록·크기를 확인했으며 이번 폴더 정리에서 모든 내용을 재검수한 것은 아니다.
- 다른 프로젝트 텍스트에서 파일명·경로 참조가 확인되지 않은 과거 학습 문서/결과 JSON 15개를 docs/history/training/으로 이동했다. 이동 전후 SHA-256을 확인했다.
- Python 캐시와 Finder 메타데이터 25개 경로를 로컬 보관 폴더로 이동했다. 실제 Python 코드·모델·영상·라벨은 삭제하지 않았다. Python 실행으로 캐시는 다시 생길 수 있다.
- 최상위 README의 오래된 구조 설명을 현재 코드 구조에 맞추고, docs/scripts/configs 진입 안내를 추가했다.
- 코드 이동은 하지 않았다. scripts의 ROOT=Path(__file__).resolve().parents[1] 경로 계산과 과거 실행 명령을 유지했다.

## 앞으로 파일을 추가할 때

- 현재 실행 설정은 configs/, 검수 프로토콜은 configs/review/에 둔다.
- 과거 학습 해설은 docs/history/training/, 새 검증 증거는 docs/checkpoints/날짜/에 둔다.
- 중간 결과는 outputs/ 새 폴더에 생성하며 기존 결과를 덮어쓰지 않는다.
- 시연 실행 진입점은 run_demo_scenarios.py로 유지하고, 새 도구는 scripts/README.md에 용도를 기록한다.
- pt/영상/학습 데이터 삭제는 채택 상태·참조·외부 백업을 확인한 후 별도 정리한다.

main 병합은 사용자의 요청대로 내일 진행한다.
