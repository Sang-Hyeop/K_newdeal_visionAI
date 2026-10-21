# GitHub 팀 실행 자료 사용하기 — 최종 2026-10-20

코드·설정·원본 영상6개는 저장소에, 확정 모델7개·최신 리뷰6개·이벤트·진단 캐시·조회 DB는 [runtime-2026-10-20](https://github.com/Sang-Hyeop/K_newdeal_visionAI/releases/tag/runtime-2026-10-20)에 있습니다. 개인 조치 기록·접속키·브라우저 프로필·학습 원본은 실행 배포에 포함하지 않습니다.

## 받을 브랜치

Windows 설치·재실행 보완 PR #23 병합 전에는 `fix/windows-first-run-and-restart`, 병합 후에는 `main`을 받습니다. GitHub Code → Download ZIP으로 받고 새 폴더에 ZIP 전체를 압축 해제합니다.

## Windows 자동 설치·실행

Windows 10/11 x64와 Edge 또는 Chrome, 인터넷 연결이 필요합니다. 프로젝트 루트의 **`시선_설치.cmd`**를 더블클릭합니다. 기존 **`Windows용_시선설치.vbs`**도 같은 작업을 합니다. 먼저 Conda 등록 목록에서 `safety` 환경을 찾아 Python 3.11 x64·확정 패키지 버전·의존성과 import를 검사합니다. 호환되면 기존 환경을 그대로 사용합니다. 없거나 호환되지 않으면 기존 safety를 변경하지 않고 사용 가능한 Python 3.11로 프로젝트 전용 환경을 준비하며, 해당 Python도 없을 때만 자동 설치합니다. 확정 모델과 최신 리뷰·이벤트 자료를 준비하고 모델 검증 후 바탕화면 바로가기를 만듭니다. 처음에는 내려받을 자료가 많아 시간이 걸립니다. 성공 메시지가 나올 때까지 창을 닫지 않습니다.

설치 완료 후 바탕화면 **시선**으로 실행합니다. 실행 시 프로젝트 안의 `.sisun/venv`만 사용하므로 다른 Python 설치와 섞이지 않습니다. `시선.vbs`를 먼저 실행한 경우에도 환경이 없으면 설치부터 진행합니다. 프로젝트 폴더는 유지합니다. 오류는 `.sisun/install.log`와 `dashboard/data/desktop.log`에 기록됩니다. 창을 닫으면 해당 실행의 서버·이벤트 API가 종료되고 다시 실행할 수 있습니다. 정상 실행 중 다시 클릭하면 창을 다시 엽니다. 오래된 응답 없는 동일 프로젝트 실행만 복구하며 다른 Python을 일괄 종료하지 않습니다.

아래 명령은 macOS 또는 개발자가 수동으로 환경을 준비할 때 사용합니다.

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

모델 로딩까지 추가 확인하려면 `python handoff.py check --models`를 실행합니다. 데스크톱 아이콘은 macOS의 `macOS용_시선설치.command`, Windows의 `Windows용_시선설치.vbs`로 설치합니다. Windows 설치기는 모델·라이브러리·영상 준비까지 포함합니다. macOS 아이콘 설치는 실행 환경·자료 설치와 별도입니다.

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

## Windows 바로가기 설치 오류

`dashboard/packaging/icons/sisun.ico`는 main에 포함된 파일입니다. 아이콘 폴더가 없다면 새 폴더에 ZIP 전체를 압축 해제했는지 확인합니다. 바로가기 아이콘은 감지 실행에 필수인 파일이 아니므로, 누락 시 Windows 기본 아이콘으로 설치를 계속하도록 수정했습니다. 기존 ZIP의 설치기를 사용 중이라면 의존성과 실행 자료 설치 후 프로젝트 루트에서 `python dashboard.py`로 먼저 실행할 수 있습니다. 실제 Windows에서 바로가기 더블클릭은 별도 확인이 필요합니다.

Windows 설치 파일 인코딩: `make_shortcut.ps1`은 UTF-8 BOM, 루트의 설치/실행 VBS 두 파일은 UTF-16 LE BOM을 유지해야 합니다. 파일을 메모장에 복사해서 재작성하지 말고 최신 ZIP 전체를 새 폴더에 풉니다. 바로가기 설치는 Python·라이브러리·실행 자료 설치를 대신하지 않습니다.

실제 선택한 pythonw 경로는 `.sisun/runtime-pythonw.txt`, 환경 검사 및 설치 결과는 `.sisun/install.log`에 남습니다. 기존 설치를 갱신하려면 `시선_설치.cmd`를 다시 실행하세요. 환경 이름이 같아도 버전이 다르면 재사용하지 않습니다.

### Python 파일로 직접 실행
프로젝트 ZIP 전체를 압축 해제한 폴더에서 **`시선_실행.py`**를 더블클릭할 수도 있습니다. `.py` 파일이 Python에 연결되어 있어야 합니다. 편집기가 열리면 우클릭 → 연결 프로그램 → Python으로 실행하거나 터미널에서 `python 시선_실행.py`를 사용합니다. 기존 safety 환경과 저장된 환경을 검사하고 필요한 자료를 준비한 뒤 기존 앱 진입점을 실행합니다. 호환 환경이 없으면 기존 Windows 설치기로 전용 환경을 준비합니다. 초기 설치에는 인터넷이 필요하며, 진행·오류 메시지는 실행 창, 오류 기록은 `.sisun/python-launch-error.log`에서 확인합니다. 이 Python 파일만 별도로 복사해서 실행할 수는 없습니다.
