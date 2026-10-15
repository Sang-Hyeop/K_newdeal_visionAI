# GitHub에서 최신 팀 실행 자료 사용하기

최신 배포는 `runtime-2026-10-15`입니다. 코드·설정·원본 영상은 Git 저장소, 현재 결과·모델·이벤트·캐시는 [GitHub Release](https://github.com/Sang-Hyeop/K_newdeal_visionAI/releases/tag/runtime-2026-10-15)에서 받습니다. 학습 이미지 데이터셋은 배포에 포함하지 않습니다.

## 기존 팀원 업데이트

이번 변경이 main에 병합된 뒤 저장소 루트에서 실행합니다. PR 병합 전 확인하려면 `git switch --track origin/data/hoodie-ppe-candidates`로 이번 작업 브랜치를 사용합니다. 이미 로컬 브랜치가 있으면 `git switch data/hoodie-ppe-candidates`를 사용합니다.

```sh
git fetch origin
git switch main
git pull --ff-only origin main
python scripts/setup_runtime.py
python handoff.py check
```

최초 업데이트 시 기존 공개 배포 파일과 해시가 같은 자료만 자동 교체·정리합니다. 개별 수정 파일은 보존하고 오류를 알립니다. 팀원이 의도적으로 기존 실행 자료를 최신 배포로 덮어쓰려는 경우에만 `python scripts/setup_runtime.py --replace`를 사용합니다. 자체 수정 데이터가 있으면 먼저 별도로 보관합니다.

## 처음 설치하는 팀원

Python 3.11과 Git을 준비하고 실행합니다. 다운로드는 약 125.6MB이며 압축 해제와 캐시에 여유 공간 2GB 이상을 권장합니다.

```sh
git clone https://github.com/Sang-Hyeop/K_newdeal_visionAI.git
cd K_newdeal_visionAI
python scripts/setup_runtime.py
python handoff.py check
```

위 명령은 PR 병합 후 main 기준입니다. 병합 전에는 앞 절의 작업 브랜치로 전환합니다. 직접 받은 ZIP도 `python scripts/setup_runtime.py --archive 받은파일.zip`로 설치할 수 있습니다. 설치기는 Python 표준 라이브러리만 사용합니다. 최신 ZIP은 처음부터 1~5번 경로와 기능별 결과를 포함하므로 `handoff.py refresh`를 추가 실행할 필요가 없습니다.

## 영상별 기능

- 1번: 사람·지게차 탐지와 충돌 근접 위험.
- 2번: 사람 탐지·위험구역 ROI 침범·안전모 PPE.
- 3번: 사람 탐지·안전모 PPE.
- 4번: 사람 탐지·위험구역 체류시간. 기존 차량 조건 판정은 내부 유지합니다.
- 5번: 근접·ROI 침범·체류시간·안전모 PPE 전체.

원본·설정·Python 실행 번호와 결과 번호는 모두 1~5입니다. 현재 리뷰는 outputs/reviews/의 5개이며 이벤트는 outputs/events/presentation1~5/입니다.

## 백엔드·대시보드 담당

모델 라이브러리를 설치하지 않고도 최신 배포 로그와 조회 API를 사용할 수 있습니다.

```sh
python handoff.py check
python handoff.py backend --import-only
python handoff.py backend --port 8010
```

현재 배포 DB에는 이벤트 5,876건, 관측 3,852건이 있습니다. 프레임/사람별 반복 기록을 포함하므로 사고나 위반의 고유 건수로 해석하지 않습니다. 같은 로그 재수입은 중복을 만들지 않습니다.

API: `http://127.0.0.1:8010/events?limit=5`, `/feature-status`, `/events/{event_id}`. 영상별 시간은 서로 다른 시계이므로 현재 영상을 선택해 조회합니다. 전환 기록은 events_v1.jsonl, 프레임 상태는 observations_v1.jsonl입니다. 출력 계약은 docs/detection-output-contract.md, API는 backend_v1/API_SPEC.md를 참고합니다. 현재 API는 조회용이며 라이브 CCTV 수신·푸시는 별도 작업입니다.

## 감지 담당

```sh
python -m venv .venv
```

Windows는 `.venv\Scripts\Activate.ps1`, macOS/Linux는 `source .venv/bin/activate`로 활성화하고 실행합니다.

```sh
python -m pip install -r requirements-runtime.txt
python handoff.py check --models
python handoff.py test
python handoff.py run --video 1
python handoff.py run --video 5
```

1·3·4·5번 기본 실행은 저장된 실제 관측을 재사용하며 2번은 전체 신규 추론입니다. `--fresh`는 원본 신규 추론입니다. 5번은 기본 추론→차량 복구→후보 검수→탑승자·거리 재평가가 이어집니다. 새 실행 결과는 outputs/handoff_runs/이며 확정 리뷰와 구분합니다.

## 모델과 변경 범위

현재 발표 모델 6개는 그대로 유지합니다. 1,577장으로 학습한 PPE 후보 모델과 학습 지표도 배포하지만 발표 모델로 자동 교체하지 않습니다. 후보 경로는 models/experiments/ppe_expanded_1577/weights/best.pt입니다. 확정 PPE 설정의 임곗값·시간·비율을 임의로 바꾸지 않습니다.

기존 검수 설정·중복 정리 기록·대체된 거리 비교 및 63장 PPE 실험 결과를 정리했습니다. 라벨링 원본·학습 데이터는 작업자 PC에 보존하며 Git/Release에 포함하지 않습니다. 후보 비교 보고서는 기능별 분리 이전의 기록이며 현재 발표 결과로 인용하지 않습니다.

## 검증과 한계

이번 코드의 회귀 검사는 248개, 백엔드 검사는 22개가 통과했습니다. 새 설치 검증 결과는 docs/progress-2026-10-14.md의 최신 배포 항목에 기록합니다. ZIP과 개별 파일 SHA-256을 검사합니다. Windows 전체 실행은 검증하지 않았으며 Python 의존성은 기존 macOS safety 환경에서 검증했습니다.

거리는 보정되지 않은 화면상 상대 거리로 실제 m가 아닙니다. 5번 차량·탑승자·밑면 중앙 거리는 실험적 경로이고 가림·최초 등장 미확인은 남습니다. 2번은 AI 생성 시연 영상입니다. 시연 적응 결과를 독립 현장 정확도로 설명하지 않습니다.
