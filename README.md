# 시선 — 기존 CCTV 기반 AI 안전관제

작업자·지게차·안전모를 검출하고, 근접 위험·구역 침범·체류를 판정해 이벤트와 관제 화면으로 연결하는 팀 프로젝트입니다. 최종 발표는 기능별 4개와 종합 1개, 총 5개 영상 구성입니다. 화면상 거리는 미터 거리가 아니며 독립 현장 정확도와 전 프레임 미탐 0을 증명한 상태는 아닙니다.

## 시작하기

- [10/14 작업 정리·최신 결과·발표 번호별 실행](docs/progress-2026-10-14.md)
- [폴더·현재 모델·결과 위치](docs/workspace-guide.md)
- [최종 원본 영상 구성](data/videos/README.md)
- [감지 담당 목표](docs/detection-goal.md)
- [영상별 기준과 변경 이력](docs/demo-feature-show-plan-2026-10-07.md)
- [백엔드·대시보드 공통 이벤트 계약](docs/team-integration-pack-2026-10-07.md)
- [샘플 기반 백엔드 API 및 대시보드 전달물](backend_v1/HANDOFF_KO.md)
- [개발 도구 안내](scripts/README.md)

## 감지 실행

```sh
conda activate safety
python -m pip install -r requirements.txt
python scripts/run_demo_scenarios.py --videos 2 --ppe-final --sample-fps 5 --output outputs/diagnostics/beta_presentation1
```

위 명령은 최종 발표 1번 영상을 기존 내부 시나리오 2로 실행합니다. 발표 3/4/5는 내부 5/4/7이며 발표 2번 ROI는 `scripts/run_intrusion_review.py`를 사용합니다. 필요한 모델은 별도 가중치 패키지로 `models/`에 준비하고, 출력은 아직 없는 새 디렉터리를 지정합니다. [현재 5번 차량 복구·탑승자 실험 재현](docs/video5-vehicle-rider-recovery-2026-10-14.md)은 별도 추가 추론과 명시적 실험 옵션을 사용합니다.

최종 PPE는 `models/ppe_final/ppe_helmet_v6_960.pt`입니다. 객체 기본 모델과 카메라별 보완 모델은 `configs/`에 정의돼 있습니다. 여러 모델을 연결하는 구조이며 단일 `.pt` 통합이 완료된 상태는 아닙니다.

## 백엔드

`backend_v1/`에는 공통 이벤트 계약의 샘플 JSONL을 SQLite로 가져와 조회하는 API가 있습니다. 실행·검증은 [백엔드 README](backend_v1/README.md)를 따릅니다. 오늘 새 감지 결과의 실시간 연결까지 완료했다고 의미하지는 않습니다.

## 구조와 결과 보관

- `src/`, `scripts/`, `configs/`: 감지·후처리·실행·설정.
- `tests/`, `docs/`: 회귀 검사·기준·검증·인계 기록.
- `data/videos/`: Git으로 공유하는 최종 원본 MP4 5개.
- `models/`: Git 제외 가중치.
- `outputs/reviews/`: workspace에 보관하는 최신 재생 결과.
- `outputs/diagnostics/`: 이벤트 로그·추론 캐시·검증 결과.
- `outputs/handoff/`: 팀 연동 전달자료.
- `docs/history/`, `docs/checkpoints/`: 과거 해설·작은 검증 증거.

생성 영상·대용량 로그·학습 데이터·가중치는 Git과 별도로 공유합니다. 최신 파일명은 [작업 정리](docs/progress-2026-10-14.md)를 확인합니다.

## 검증과 협업

```sh
python -m unittest discover -s tests -q
python -m unittest discover -s backend_v1 -p 'test_*.py' -q
```

작업 브랜치 → PR → 리뷰 → 병합은 [협업 안내](docs/CONTRIBUTING.md)를 따릅니다. 시연에 노출된 결과는 시연 환경 적응 성능이며 미확인을 현장 전체 안전으로 해석하지 않습니다.
