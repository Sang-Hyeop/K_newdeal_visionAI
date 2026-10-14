# 시선 팀 전달본 — 2026-10-14

먼저 이 파일을 읽어주세요. 압축은 모두 해제한 뒤 최상위 폴더에서 명령을 실행합니다. 기준 코드는 PR #11이 병합된 main입니다. 정확한 커밋은 HANDOFF_INDEX.json에 있습니다.

## 포함 자료

- src/, scripts/, handoff.py: 감지·추적·후처리·이벤트 출력·실행 Python 코드.
- configs/: 최종 영상 구성, 모델 설정, ROI, 설비 참고 이미지.
- models/: 최신 5개 영상 실행에 사용한 실제 모델 가중치 6개와 PPE 중복 제거 보조 코드.
- data/videos/: 최종 원본 영상 5개.
- outputs/reviews/: 사람이 확인한 최신 결과 영상 5개. 가장 먼저 재생해 확인할 수 있습니다.
- outputs/events/presentation1~5/: 각 영상 전체의 기능별 이벤트·프레임별 관측 JSONL.
- outputs/diagnostics/: 위 최신 결과의 검출·추적 원시 기록, 실행 요약, 검증, 5번 재현용 실제 추론 캐시.
- outputs/backend/full_review.sqlite3: 이번 전체 이벤트·관측 로그를 가져와 검증한 조회용 DB.
- backend_v1/: SQLite 가져오기·조회 API 코드, 규격 및 팀 전달 문서.
- docs/, tests/: 설계·작업 이력·이벤트 계약·검증 기록·회귀 검사.
- HANDOFF_INDEX.json, CHECKSUMS.json, HANDOFF_VALIDATION.json: 구성·출처·파일 무결성·검증 결과.

모델 재학습용 원본 데이터셋·과거 실험 전체·가상환경은 이 실행 전달본의 범위가 아닙니다. 실행 가중치와 현재 원본·결과·전체 이벤트 자료는 포함돼 있습니다.

## 1. 결과만 확인하기

Python 설치 없이 outputs/reviews/의 MP4 5개를 재생하면 됩니다.

- 1_forklift_worker_collision_risk_latest.mp4
- 2_restricted_zone_intrusion_latest.mp4
- 3_PPE_Helmet_latest.mp4
- 4_hazard_zone_dwell_worker_fixed.mp4
- 5_Logistics_Warehouse_vehicle_rider_review_v2.mp4

5번 결과는 밑면 중앙 거리·차량 복구·탑승자 구분의 최신 리뷰 실험입니다. 최초 등장·가림의 미확인이 남으며 거리 단위는 미터가 아닙니다.

## 2. 실행 환경 준비

Python 3.11을 준비하고 새 환경에서 설치합니다. 처음 의존성 설치에는 인터넷이 필요합니다. 모델을 따로 다운로드할 필요는 없습니다. 동봉 Python 코드는 소스 실행형이며 Windows .exe는 아닙니다.

```sh
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-runtime.txt
```

macOS/Linux:

```sh
source .venv/bin/activate
python -m pip install -r requirements-runtime.txt
```

requirements-runtime.txt는 전달본 검증 환경의 버전입니다. Python·PyTorch 설치가 지원되는 운영체제에서 사용하고, 팀원 환경 차이로 설치가 실패하면 오류와 HANDOFF_INDEX.json의 버전을 함께 전달해주세요. GPU 없이 CPU로 실행하도록 설정돼 있습니다.

## 3. 무결성 및 실행 검사

```sh
python handoff.py check
python handoff.py check --models
python handoff.py test
python handoff.py list
```

check는 포함 파일의 SHA-256을 검사합니다. --models는 실제 모델 로딩·첫 프레임 CPU 추론과 PPE 보조 코드까지 확인합니다. backend DB나 설정 파일을 수정한 이후의 해시 불일치는 원본 전달본과 달라졌다는 의미입니다.

## 4. 영상별 실행

발표 번호 1~5로 실행합니다. 파일명과 기존 내부 번호의 차이는 handoff.py가 처리합니다. 출력은 기존 전달 결과를 덮어쓰지 않고 outputs/handoff_runs/의 새 폴더에 생성합니다.

```sh
python handoff.py run --video 1
python handoff.py run --video 2
python handoff.py run --video 3
python handoff.py run --video 4
python handoff.py run --video 5
```

1·3·4·5는 기본적으로 동봉한 실제 관측 캐시를 검증해 재사용하고 규칙·이벤트·화면을 다시 생성합니다. 새 AI 추론으로 설명하지 않습니다. 2번은 별도 ROI 실행기로 12초 전체를 새로 추론합니다.

짧은 실행 검사(2번 제외):

```sh
python handoff.py run --video 5 --max-seconds 1
```

원본부터 새로 AI 추론하려면 --fresh를 추가합니다. 특히 5번은 기본 추론 → 확대 차량 재탐지 → 후보 검수 → 탑승자/거리 재평가를 차례로 실행하므로 CPU에서 오래 걸릴 수 있습니다. 캐시 기반 재현 결과와 새 추론 결과가 완전히 같다고 보장하지 않습니다.

```sh
python handoff.py run --video 1 --fresh
python handoff.py run --video 5 --fresh
```

## 5. 이벤트 로그와 백엔드

백엔드 담당자는 outputs/events/를 입력으로 사용합니다. 현재 발표 번호별로 폴더를 나눴으며 기능별 events_v1.jsonl(전환)과 observations_v1.jsonl(프레임별 상태)이 모두 들어 있습니다.

```sh
python handoff.py backend --import-only
python handoff.py backend --port 8010
```

서버 주소: http://127.0.0.1:8010

- GET /events?limit=5
- GET /feature-status
- GET /events/{event_id}

Python 표준 라이브러리만으로 백엔드를 실행할 수 있습니다. 재가져오기는 중복을 추가하지 않습니다. 이 DB는 현재 전달 로그의 조회용이며 라이브 CCTV에서 새 이벤트를 수신하는 기능은 별도 연동 작업입니다.

계약은 docs/detection-output-contract.md, docs/team-integration-pack-2026-10-07.md와 backend_v1/HANDOFF_KO.md를 확인합니다. 예전 문서의 영상 번호보다 HANDOFF_INDEX.json과 현재 outputs/events/의 번호를 우선합니다.

## 해석 시 유지할 기준

- 미확인은 안전이 아닙니다. 기능별 SAFE도 현장 전체 안전을 뜻하지 않습니다.
- 보정된 실제 길이 정보가 없어 distance_meters는 null입니다.
- PPE 미착용 표시는 영상 관측의 검토 후보이며 검증된 위반자 확정이 아닙니다.
- 2번 영상은 AI 생성 시연 자료입니다. 현재 시연 적응 결과를 다른 현장 정확도로 발표하지 않습니다.
- 요약에 보존한 original_source_location과 진단 JSON 안의 /Users/... 경로는 기존 실행 출처 기록입니다. 다른 PC에서 해당 절대 경로를 만들 필요는 없습니다. 실행은 이 폴더의 상대 경로를 사용합니다.
