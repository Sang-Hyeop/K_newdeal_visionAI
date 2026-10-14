# GitHub만으로 팀 작업 시작하기

현재 코드는 Git 저장소, 모델·최신 리뷰·전체 로그는 GitHub Release `runtime-2026-10-14`에 있습니다. 설치 명령이 약179MB 자료를 다운로드해 연결하므로 ZIP을 직접 전달받지 않아도 됩니다. 실행은 handoff.py로 통일합니다.

## 공통 준비

Python 3.11과 Git을 준비한다. 아래 명령은 저장소 루트에서 실행한다. 설치에는 인터넷과 압축 해제용 여유 공간 약 1GB 이상이 필요하다.

```sh
git clone https://github.com/Sang-Hyeop/K_newdeal_visionAI.git
cd K_newdeal_visionAI
python scripts/setup_runtime.py
```

`setup_runtime.py`는 Python 표준 라이브러리만 사용한다. Release ZIP의 과거 내부 번호를 설치 시 현재 발표 번호(video1/video3/video4/video5)로 배치한다. 기존 설치는 setup_runtime.py를 다시 실행하면 되며, 이전 경로는 해시가 같은 복사본만 제거한다. 수정된 기존 파일은 보존한다. 약 179MB의 GitHub Release를 다운로드하고 ZIP·개별 파일 해시를 검사한 뒤, `models/`와 `outputs/`의 정해진 위치에 설치한다. 다른 내용의 기존 파일은 기본적으로 보존하고 오류로 알려준다. 의도적으로 기존 실행 자료를 교체할 때만 `--replace`를 사용한다.

직접 GitHub [Releases](https://github.com/Sang-Hyeop/K_newdeal_visionAI/releases/tag/runtime-2026-10-14)에서 ZIP을 받은 경우에도 `python scripts/setup_runtime.py --archive 받은파일.zip`로 설치할 수 있다.

## 백엔드·대시보드 담당

모델 라이브러리를 설치하지 않고도 실제 전달 로그를 가져와 API를 실행할 수 있다.

```sh
python handoff.py check
python handoff.py backend --import-only
python handoff.py backend --port 8010
```

API는 `http://127.0.0.1:8010`의 `/events?limit=5`, `/feature-status`, `/events/{event_id}`이다. 입력은 `outputs/events/presentation1~5/`, DB는 `outputs/backend/full_review.sqlite3`이다. 실제 이벤트 6,139건과 프레임별 관측 4,142건이 제공되며 재가져오기로 중복을 추가하지 않는다. 영상별 재생 시간은 서로 다른 시계이므로 대시보드에서 현재 영상을 선택해 조회한다.

- 전환 로그: `events_v1.jsonl`
- 프레임별 상태: `observations_v1.jsonl`
- 이벤트 계약: `docs/detection-output-contract.md`
- API 명세: `backend_v1/API_SPEC.md`
- 조회만 제공하며 라이브 CCTV의 새 이벤트 수신·푸시 연결은 별도 구현이다.

## 감지 담당

```sh
python -m venv .venv
```

Windows: `.venv\Scripts\Activate.ps1`, macOS/Linux: `source .venv/bin/activate`로 활성화한 뒤 실행한다.

```sh
python -m pip install -r requirements-runtime.txt
python handoff.py check --models
python handoff.py test
python handoff.py run --video 1
python handoff.py run --video 5
```

발표 번호 1~5로 지정한다. 1·3·4·5는 실제 관측 캐시를 재사용해 규칙·이벤트·화면을 다시 만들고, 2번은 원본에서 전체를 새로 추론한다. 원본부터 새 AI 추론은 `--fresh`를 추가한다. 5번은 기본 추론→확대 차량 복구→후보 검수→탑승자/거리 재평가가 이어져 CPU에서 오래 걸릴 수 있다. 새로운 출력은 `outputs/handoff_runs/`에 만든다.

## 발표·검수 담당

`outputs/reviews/`에 최신 결과 영상 5개가 있다. 위치는 `python handoff.py list`로 확인한다. Git의 `data/videos/`는 원본이고 Release의 `outputs/reviews/`는 분석 결과이므로 구분한다.

5번은 밑면 중앙 거리와 차량/탑승자 구분 실험이다. 최초 등장·가림의 미확인은 남고, 실제 미터 거리나 독립 현장 정확도를 보장하지 않는다. 2번은 AI 생성 시연 영상이다.

## 제공 범위

모델 6개, PPE 보조 코드, 결과 MP4 5개, 전체 이벤트·관측·진단 로그, 재현용 캐시와 조회 DB를 설치한다. 소스·설정·입력 MP4는 Git으로 받는다. 가상환경·재학습용 데이터셋·과거 실험 전체는 별도로 관리한다. requirements-runtime.txt는 macOS safety 환경에서 확인한 버전이며 Windows 전체 실행은 아직 검증하지 않았다.

## GitHub에서 새로 받은 폴더의 검증

GitHub에서 작업 브랜치를 새로 clone한 뒤 공개 Release 다운로드→111개 자료 설치→원본 5개 및 실행 자료 해시 검사→모델 6개 CPU 추론→검사 252+8개→실제 로그 재가져오기→5번 1샘플 재실행을 확인했다. DB는 이벤트 6,139건·관측 4,142건·영상 5개다. 검증 환경은 기존 safety Python 환경을 사용했으며 새 운영체제의 의존성 설치까지 검증한 것은 아니다. 근거는 docs/checkpoints/2026-10-14/github-runtime-verification.json이다.
