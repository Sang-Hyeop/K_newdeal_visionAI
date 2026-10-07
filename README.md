# 시선 — 기존 CCTV 기반 AI 안전관제

사람·지게차·안전모를 검출하고, 근접 위험·구역 침범·체류를 판정해 이벤트와 관제 화면으로 연결하는 팀 프로젝트입니다. 현재 저장 영상 7개를 기능별로 시연합니다. 독립 현장 성능과 전 프레임 미탐 0은 아직 증명하지 않았습니다.

## 시작하기

- [폴더·현재 모델·최신 결과 안내](docs/workspace-guide.md)
- [영상별 시연 기준](docs/demo-feature-show-plan-2026-10-07.md)
- [실행 방법](docs/demo-scenario-runbook-2026-10-07.md)
- [백엔드·대시보드 연동](docs/team-integration-pack-2026-10-07.md)
- [남은 과제](docs/remaining-gaps-2026-10-07.md)
- [개발 도구 용도별 목록](scripts/README.md)

## 실행

```bash
conda activate safety
python -m pip install -r requirements.txt
python scripts/run_demo_scenarios.py --videos 1 --output outputs/diagnostics/my_video1 --sample-fps 5 --ppe-search full_recall
```

출력은 없는 새 폴더를 사용합니다. 모델은 Git에 없으므로 별도 가중치 패키지를 models/ 경로에 설치해야 합니다. 모델 위치·해시는 docs/checkpoints/2026-10-07/model-share-manifest.json을 확인합니다. 기본 객체 모델과 시연 보완 모델을 함께 쓰며, 후드 보조 v1은 5·6번에서 --hood-auxiliary 옵션으로 켭니다. v2는 미채택 실험입니다.

## 구조

- src/: 감지·추적·판정·이벤트·시연 표시 구현.
- scripts/: 실행 및 학습·데이터·평가 도구. 전체를 매번 실행하지 않습니다.
- configs/: 현재 실행 설정과 카메라별 ROI; review/는 검수 프로토콜.
- tests/: 회귀 검사.
- docs/: 기준·인계·설계; history/는 과거 해설, checkpoints/는 검증 증거.
- data/: 원본 영상·데이터·라벨.
- models/: 채택·실험 가중치.
- outputs/: 생성 영상·이벤트·추론 캐시·학습 결과.
- _local_archive/: Git 제외 로컬 보관.

src/detection, src/events, src/dashboard는 초기 분업용 빈 폴더입니다. 현재 감지 구현은 src/*.py이며 이 저장소에서 전체 백엔드·대시보드 완성을 확인한 상태는 아닙니다.

## 협업·검증

작업 브랜치 → PR → 리뷰 → 병합은 [협업 안내](docs/CONTRIBUTING.md)를 따릅니다. Git에는 7개 시연 MP4가 포함됩니다. 학습 데이터·가중치·생성 결과는 별도 공유합니다. main 병합은 현재 보류 중입니다.

```bash
python -m unittest discover -s tests -q
```

시연 학습에 노출된 결과는 시연 환경 적응 성능입니다. 화면상 거리를 미터로 표시하지 않으며, 불확실한 관측을 현장 전체 안전으로 해석하지 않습니다.
