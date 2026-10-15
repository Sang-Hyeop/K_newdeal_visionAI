# 시선 — 현재 발표 영상 1~5 실행 안내

**현재 실행 입구는 `handoff.py` 하나입니다.** 과거 실험 실행기와 이전 리뷰 결과는 2026-10-14 정리에서 삭제했습니다. 아래 명령은 프로젝트 최상위 폴더에서 실행합니다.

## 실행

```sh
python handoff.py list
python handoff.py check --models
python handoff.py run --video 1
```

`--video`를 1~5로 바꿉니다. `list`는 영상별 원본·모델·설정·구현 코드·최신 결과·이벤트 경로를 출력합니다. 개발은 safety 환경을 사용합니다.

- 1: 지게차–작업자 충돌 위험
- 2: 위험구역 ROI 침범
- 3: 안전모 착용/미착용
- 4: 위험구역 체류
- 5: 물류창고 통합 시연 — 차량 복구·탑승자 분리·밑면 중앙 거리 실험

1·3·4·5의 기본 실행은 저장된 실제 관측을 재사용합니다. 원본부터 새 추론하려면 `python handoff.py run --video 5 --fresh`처럼 실행합니다. 2번은 항상 원본 전체를 새로 추론합니다. 새 결과는 `outputs/handoff_runs/`에 생성되며 확정 리뷰를 덮어쓰지 않습니다. 이 폴더의 결과는 검수 전 결과입니다.

## 최신 확정 결과

`outputs/reviews/`에는 영상별 결과 1개씩, 총 5개만 있습니다. `outputs/events/presentation1`~`presentation5`에는 같은 버전의 전체 이벤트·관측 기록이 있습니다. `outputs/diagnostics/`는 기본 실행의 재현 캐시이므로 임의로 삭제하지 않습니다.

실제 모델 6개와 영상별 연결 관계는 `configs/team-runtime-index.json`이 기준입니다. 파일명에서 v16/v2 같은 이름을 보고 최신 여부를 판단하지 않습니다. 기존 학습 데이터와 수동 라벨은 `data/`에 보존했습니다. `src/`는 공통 모듈, `tests/`는 회귀 검증 코드이며 개별 실행 대상이 아닙니다.

## 백엔드·검증

```sh
python handoff.py backend --port 8010
python handoff.py test
```

이벤트 API는 `http://127.0.0.1:8010/events?limit=5`입니다. API·대시보드 연결은 `docs/github-team-quickstart.md`와 `backend_v1/API_SPEC.md`를 참조합니다.

## 새 PC 설치

Python 3.11 준비 후 `python scripts/setup_runtime.py`, `python -m pip install -r requirements-runtime.txt`, `python handoff.py refresh`를 순서대로 실행합니다. refresh는 기존 리뷰와 이벤트를 현재 영상별 기능 구성으로 수정합니다. 모델·리뷰·로그는 GitHub Release에서 설치합니다. Git clone만으로 모델이 포함되지는 않습니다.

## 한계와 과거 기록

거리 값은 보정되지 않은 화면상 상대 거리이며 실제 m가 아닙니다. 가림·최초 등장·미탐은 미확인으로 남습니다. 2번은 AI 생성 시연 영상입니다. 시연 적응 결과를 독립 현장 정확도로 설명하지 않습니다.

현재 문서는 `docs/README.md`에서 시작합니다. 과거 리뷰·학습 실험·초안은 docs에서 삭제했고 Git 이력에서 확인합니다. 현재 사용자는 발표 번호1~5와 handoff.py를 사용합니다. 파일 정리·실행 검증 기록은 `docs/checkpoints/2026-10-14/five-video-cleanup/`에 있습니다.
