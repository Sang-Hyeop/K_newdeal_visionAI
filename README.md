# 시선 — 기존 CCTV 기반 AI 안전관제

중소기업·협력업체의 기존 CCTV 영상에서 위험을 감지하고 이벤트 로그·관제 화면·알림으로 연결하는 팀 프로젝트입니다.

## 기능 목표

- 지게차와 보행 작업자의 근접 위험
- 위험구역 접근·침범
- 작업자별 위험구역 체류시간
- 안전모 착용·미착용
- 위험·주의·안전 상태 및 이벤트 전달

현재는 협업 기본 구조를 준비한 상태입니다. 기존 감지 코드의 이관과 실행 명령은 후속 작업에서 추가합니다.

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

`docs/CONTRIBUTING.md`에 따라 작업 브랜치 → PR → 리뷰 → 병합 순서로 진행합니다. 데이터·영상·모델·실행 결과는 별도 공유하며 Git에서 제외됩니다.
