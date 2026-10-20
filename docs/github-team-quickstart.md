# GitHub 팀 실행 자료 사용하기 — 최종 2026-10-20

코드·설정·원본 영상6개는 저장소에, 확정 모델7개·최신 리뷰6개·이벤트·진단 캐시·조회 DB는 [runtime-2026-10-20](https://github.com/Sang-Hyeop/K_newdeal_visionAI/releases/tag/runtime-2026-10-20)에 있습니다. 개인 조치 기록·접속키·브라우저 프로필·학습 원본은 실행 배포에 포함하지 않습니다.

## 받을 브랜치

PR 병합 전: `feat/sisun-dashboard-ops-alert-ux`를 선택합니다. PR이 main에 병합된 후에는 main을 받습니다. main ZIP은 병합 전까지 이번 변경이 포함되지 않습니다.

### Git을 사용하는 경우

```sh
git clone --branch feat/sisun-dashboard-ops-alert-ux https://github.com/Sang-Hyeop/K_newdeal_visionAI.git
cd K_newdeal_visionAI
```

기존 저장소라면 수정 내용을 보관한 다음 아래처럼 전환합니다. 같은 이름의 로컬 브랜치가 이미 있으면 두 번째 명령은 `git switch feat/sisun-dashboard-ops-alert-ux`로 실행합니다.

```sh
git fetch origin
git switch --track origin/feat/sisun-dashboard-ops-alert-ux
git pull --ff-only origin feat/sisun-dashboard-ops-alert-ux
```

### Download ZIP을 사용하는 경우

GitHub에서 위 브랜치 선택 → Code → Download ZIP → 새 폴더에 압축 해제합니다. 이전 폴더에 섞어 풀지 않습니다. 압축을 푼 프로젝트 루트에서 아래 명령을 실행합니다.

## 설치와 검증

Python3.11 이상의 가상환경을 사용합니다. 기존 safety 환경이 있으면 먼저 활성화합니다.

```sh
python --version
python scripts/setup_runtime.py
python -m pip install -r requirements-runtime.txt
python -m pip install gradio==6.28.0 pandas==3.0.5 imageio-ffmpeg
python handoff.py check
python dashboard.py
```

브라우저: http://127.0.0.1:7860 · 테스트 로그인: 김상협/이수민/박회승/최인승, 암호1234. 실제 운영 계정·권한 시스템으로 검증된 로그인은 아닙니다.

모델 로딩까지 추가 확인하려면 `python handoff.py check --models`를 실행합니다. 데스크톱 아이콘은 macOS의 `macOS용_시선설치.command`, Windows의 `Windows용_시선설치.vbs`로 설치합니다. 아이콘 설치는 모델·라이브러리 설치와 별도입니다.

이전 공식 배포와 해시가 일치하는 파일은 안전하게 최신 자료로 교체합니다. 직접 수정한 파일은 보존하며 오류를 표시합니다. 의도적으로 교체할 때만 백업 후 `python scripts/setup_runtime.py --replace`를 사용합니다. 직접 받은 실행 자료 ZIP은 `python scripts/setup_runtime.py --archive 경로.zip`으로 설치할 수 있습니다.

## 영상별 기능과 실행

- 1번: 사람·지게차 근접 위험
- 2번: 사람 탐지·ROI 침범·안전모
- 3번: 사람 탐지·안전모
- 4번: 사람 탐지·체류시간
- 5번: 네 기능 통합
- 6번: 불꽃 탐지·반복 관측 기반 화재 의심

최신 리뷰는 `outputs/reviews/`입니다. 이미 완성된 리뷰가 배포되므로 시연 전에 재추론할 필요는 없습니다. 다시 생성하려면 `python handoff.py run --video N`을 사용합니다. `--fresh`는 신규 AI 추론이며 시간이 더 걸립니다.

## 함께 확인할 동작

6개 영상 재생, 실시간 KPI·알림, 개별 카메라 확인 후 다른N 유지, 메인 복귀 시✓ 숨김, 경보·조치 관리, 이벤트 이력의 창고/유형 두 줄, 라이트/다크 가독성을 확인합니다. 사건 표시 시각은 로그인/메인 새로고침 시 현재 시각을 시작점으로 사용합니다. 기존 개인 기록은 새 설치로 옮겨지지 않습니다.

기본은 각 PC의 로컬 사건 상태입니다. 공용 사건 상태가 필요하면 [공용 사건 서버 연결](shared-case-server.md)을 따릅니다. N·✓는 기존 개인 브라우저 표시로 유지합니다. 공용 서버를 설정하지 않은 PC끼리는 조치 상태가 자동 공유되지 않습니다.

현재 거리는 화면상 상대 거리이며 실제m가 아닙니다.2번은 AI 생성 영상이고, 시연 성능은 독립 현장 일반화 정확도와 구분합니다.
