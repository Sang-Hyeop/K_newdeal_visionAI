# 시선 대시보드

`backend_v1/` 처럼 대시보드 구현·런타임·패키징을 이 폴더에 모았습니다.

| 경로 | 역할 |
|------|------|
| `app.py` | Gradio UI·탭 조립 |
| `config.py` | 경로·구역·로그인 |
| `events.py` / `api.py` | 이벤트 적재·API |
| `media.py` / `sound.py` / `ui.py` / `style.py` | 영상·알람·HTML·CSS |
| `desktop.py` | Chrome/Edge 앱 창 |
| `data/` | 로컬 캐시·로그 (Git 제외) |
| `packaging/` | macOS / Windows 설치·실행 |

## 실행 (저장소 루트)

```sh
python dashboard.py              # 브라우저
python dashboard_desktop.py      # 데스크톱 앱 창
```

ZIP/clone 후 설치: 루트 `macOS용_시선설치.command` / `Windows용_시선설치.vbs`  
안내는 `packaging/실행방법.md`.

## 실행 부담 정리

큰 통합 영상 진단 로그는 한 줄씩 읽고, 같은 새로고침에서 반복 사용하는 체류 로그만 잠시 재사용합니다. 재생성 자료를 장기 메모리 캐시에 쌓지 않습니다. 영상 변환은 같은 출력에 요청이 겹치면 한 번만 실행하며 성공한 임시 파일만 현재 영상으로 교체합니다. 영상 품질·감지·경보 기준은 유지합니다. 현재 브라우저 영상은 data/origin_*.mp4·detect_*.mp4이며 과거 demo_/raw_/main_ 미리보기는 삭제했습니다. 브라우저 사용자 프로필과 현재 실행 로그는 보존합니다.

전후 행 동일성·자원 측정·삭제 목록은 ../configs/review/runtime-cleanup.json에 기록했습니다. 화재 표시의 이전 임시 patch 기록은 Git 이력에 있고 실제 app/events/ui 코드에 통합했습니다.
