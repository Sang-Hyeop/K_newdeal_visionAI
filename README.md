# 시선 — 확정 영상 1~6

Windows 앱은 `시선_실행.py`, 바탕화면 아이콘 생성은 `시선_바로가기_만들기.py`, 설치 준비는 `시선_설치.cmd`를 사용합니다. 감지 재실행·자료 점검 입구는 `handoff.py`입니다. 최신 결과는 `outputs/reviews/`의 영상 6개입니다. 좋은 보완은 기본 실행에 반영하고, 실패하거나 대체된 실험 결과는 삭제합니다.

```sh
python handoff.py list
python handoff.py run --video 3
python handoff.py check
```

전체 실행이 성공하면 해당 영상의 기존 최신 MP4·이벤트·캐시·조회 DB를 갱신합니다. 날짜별/실험별 결과 폴더를 계속 만들지 않습니다. 원본부터 신규 AI 추론은 `--fresh`를 붙입니다. `--max-seconds`는 짧은 확인용으로, outputs/runtime/preview_videoN.mp4 하나만 갱신하고 전체 최신 결과는 보존합니다.

- 1번: 사람·지게차 충돌 근접 위험만.
- 2번: 사람 탐지·ROI 침범·안전모 PPE.
- 3번: 사람 탐지·안전모 PPE만.
- 4번: 사람 탐지·체류시간만. 기존 차량 조건은 내부 판정에 유지.
- 5번: 근접·ROI 침범·체류시간·PPE 전체.
- 6번: 주차장 불꽃 감지·반복 관측 기반 화재 의심만.

2026-10-17 모델 작업을 종료했습니다. [최종 모델·선정 이유](models/README.md), [확정 해시 목록](configs/final-model-lock.json)을 기준으로 시스템 완성에 집중합니다. 최신 실행 자료는 `runtime-2026-10-20`이며 6번 화재와 확정 모델 7개를 포함합니다.

현재 확정 모델 7개와 원본·코드·결과 연결은 configs/team-runtime-index.json이 기준입니다. PPE는 착용400장·미착용400장(총800장) 보완학습 중 실제 영상 비교로 선택한1회차 가중치에 사용자 확정 1초/3관측/75%·착용0.4/미착용0.3·hold0.6초를 적용했습니다. 사람 ID는 위치 중심 추적으로 연결하며, 5번에서만 추가 상반신 탐지를 사용하며, 그래도 증거가 부족한 사람은 320px 주변 문맥으로 작은 머리를 다시 찾습니다. 그래도 낮은 신뢰도의 머리 후보가 남으면 480px 문맥으로 한 번 더 확인합니다. 추가 크롭 단독의 안전모 후보로 착용 SAFE를 만들지 않습니다.

```sh
python handoff.py backend --import-only
python handoff.py backend --port 8010
python handoff.py test
```

대시보드는 `python dashboard.py`로 실행합니다. 현재 safety 환경에서 Gradio 6.28.0·pandas 3.0.5를 확인했습니다. 신규 환경은 감지 의존성 외에 `python -m pip install gradio==6.28.0 pandas==3.0.5`가 필요합니다. 브라우저 영상 변환에는 ffmpeg 또는 imageio-ffmpeg가 필요합니다. 대시보드는 현재 runtime index의 최신 리뷰 6개와 outputs/events를 읽고 로컬 API를 자동 시작합니다.

## 시선 대시보드

발표 이벤트 API 위에 로그인·구역 CCTV·알람을 띄웁니다.

```sh
python dashboard.py
```

브라우저 `http://127.0.0.1:7860` · 로그인 `김상협`·`이수민`·`박회승`·`최인승` / `1234`.
ZIP/clone 후 **한 번만** 설치(어느 PC든 동일): macOS는 `macOS용_시선설치.command` → 바탕화면 `시선.app`, Windows는 `시선_설치.cmd` → 바탕화면 「시선」.
그다음 바탕화면 아이콘으로 실행. 구현은 `dashboard/` · 안내는 `dashboard/packaging/실행방법.md`.

## 새 PC 설치

Windows 10/11 x64에서는 ZIP 전체를 새 폴더에 압축 해제한 뒤 **`시선_설치.cmd`**를 더블클릭합니다. 기존 Python 3.11 64비트가 필요합니다. safety 환경을 먼저 검사하며, 호환되지 않으면 기존 Python으로 전용 가상환경을 준비합니다. 필요한 Python이 없으면 설치 안내만 표시하고 종료하며 Python 자체를 자동 설치하지 않습니다. 첫 준비에 라이브러리·모델·리뷰 자료를 내려받으므로 인터넷 연결이 필요합니다. 설치 완료 후 바탕화면 **시선**으로 실행합니다. 프로젝트 폴더는 삭제하거나 옮기지 않습니다. 기존 `Windows용_시선설치.vbs`도 같은 설치를 실행합니다.


- 앱 실행: **`시선_실행.py`** — 환경 확인·필요한 준비 후 시선 실행.
- 바로가기 생성: **`시선_바로가기_만들기.py`** — 바탕화면에 시선 아이콘 생성.
- 처음 실행 환경 준비: **`시선_설치.cmd`** — safety 검사·필요한 새 가상환경 준비·실행 자료 설치·아이콘 생성.

`.py` 파일은 Python으로 실행합니다. Python 자체는 자동 설치하지 않으며 기존 safety는 보존합니다.

backend_v1/API_SPEC.md와 docs/github-team-quickstart.md가 팀원 연동 안내입니다. 신규 PC의 모델 설치는 `python scripts/setup_runtime.py`, 감지 라이브러리는 `python -m pip install -r requirements-runtime.txt`입니다.

2026-10-20 최종 팀 실행 자료는 [runtime-2026-10-20](https://github.com/Sang-Hyeop/K_newdeal_visionAI/releases/tag/runtime-2026-10-20)입니다. 10월 23일 최종 관제·공용 사건 수정본은 `fix/final-monitoring-shared-cases`에서 받고, 최종 PR 병합 후에는 `main`에서 받습니다. Code → Download ZIP도 같은 브랜치를 선택합니다. 압축 해제 후 `python scripts/setup_runtime.py`로 확정 모델7개·최신 리뷰6개·이벤트를 설치하고 `python handoff.py check`로 확인합니다. 과거 Release만 다시 받으면 최신화되지 않습니다. 자세한 명령은 [팀원 실행 안내](docs/github-team-quickstart.md)를 따릅니다.

학습 데이터·수동 라벨은 data/에 보존했습니다. 채택하지 않은 1577장 후보 모델과 비교/실험 출력은 삭제했습니다. 변경·실패 과정은 Git 이력, 현재 상태는 docs/progress-2026-10-14.md를 참고합니다. 거리는 실제 m가 아닌 화면상 상대 거리이며, 2번은 AI 생성 영상입니다. 시연 성과가 독립 현장 정확도를 보장하지 않습니다.

## 10월 23일 최종 관제 정리

다른 탭에서도 메인 집계·경보를 진행하며, 메인 복귀 시 영상은 세션 진행 위치로 복원합니다. ‘소리 끄기’는 음향만 끄고 목록·배지·기록은 유지합니다. 이벤트 표시 시각은 앱 실행 시각에 영상 경과초를 더하며 과거 조치 이력은 보존합니다. 운영 통계의 평균 최초 확인·완료 카드는 제거했습니다.

공용 사건 모드는 선택 사항입니다. 서버 PC에서 `python 시선_공용서버.py`, 팀원 PC에서 `python 시선_공용연결.py 접속파일.json`을 실행한 뒤 앱을 재시작합니다. 접속 파일은 공개 저장소에 포함하지 않습니다. [공용 사건 연결·시간 표시 안내](docs/shared-case-update-2026-10-23.md)를 참고하세요.
