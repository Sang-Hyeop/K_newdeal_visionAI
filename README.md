# 시선 — 기존 CCTV 기반 AI 안전관제

중소기업·협력업체의 기존 CCTV 영상에서 위험을 감지하고 이벤트 로그·관제 화면·알림으로 연결하는 팀 프로젝트입니다.

## 기능 목표

- 지게차와 보행 작업자의 근접 위험
- 위험구역 접근·침범
- 작업자별 위험구역 체류시간
- 안전모 착용·미착용
- 위험·주의·안전 상태 및 이벤트 전달

현재는 데이터 검수·YOLO 추가 학습·저장 영상 검출 시험과 체류 상태 계산 모듈까지 진행했습니다. 최종 발표 모델은 아직 확정하지 않았으며 추적·ROI·위험 판정 연결은 남아 있습니다. 자세한 현황과 성능 한계는 [진행 기록](docs/progress-2026-10-06.md), 학습 지표와 해시 기록은 [중간 저장](docs/checkpoints/2026-10-06/)을 참고합니다.

## 폴더 구조

- `src/detection/`: YOLO·추적·ROI·후처리
- `src/events/`: 이벤트·로그·알림
- `src/dashboard/`: 관제 화면 연동; 프론트엔드 구조는 팀 합의 후 조정
- `configs/`: 카메라·ROI·판정 설정
- `docs/`: 설계와 협업 문서
- `data/`: 로컬 영상·데이터셋
- `models/`: 로컬 모델 가중치
- `outputs/`: 생성 결과·로그

## 환경 준비

팀원은 원격 저장소를 복제합니다. 이미 clone한 폴더에서는 다시 clone하지 않습니다.

```bash
git clone https://github.com/Sang-Hyeop/K_newdeal_visionAI.git
cd K_newdeal_visionAI
conda activate safety
python -m pip install -r requirements.txt
```

`safety`가 없는 팀원은 Python 버전을 팀과 합의한 후 환경을 생성합니다. 패키지 목록은 초기안이며 실행 검증 후 버전을 고정합니다.

## 협업

`docs/CONTRIBUTING.md`에 따라 작업 브랜치 → PR → 리뷰 → 병합 순서로 진행합니다. `data/videos`의 시연 MP4 7개는 Git으로 공유합니다. 나머지 학습 데이터·모델 가중치·실행 결과는 별도로 공유하며 Git에서 제외됩니다.
