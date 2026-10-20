# 공용 사건 상태 연결 (선택 사항)

현재 실행 방식은 기본 로컬 모드 그대로다. 환경 변수를 설정한 대시보드만 공용 서버를 사용한다. 6개 영상/모델/감지 기준/영상 재생/메인 집계/경보음/N·✓/메뉴 구성은 변경하지 않는다. N·✓는 기존 브라우저 상태를 유지한다.

## 공유 범위

공유: 확인 전·확인함·조치 중·조치 완료, 담당자 배정, 처리 사용자·서버 처리 시각·메모·이력, 오늘 감지된 고유 사건. 원본 이벤트와 영상은 각 컴퓨터의 기존 자료를 사용한다. 같은 런타임 자료의 동일 사건 ID를 사용해야 같은 사건으로 연결된다. 영상이나 학습 자료를 네트워크로 전송하지 않는다.

서버 SQLite의 journal이 유일한 공유 기록이다. 기존 판정/전이 규칙을 그대로 사용하며 쓰기 트랜잭션에서 현재 상태를 다시 읽는다. 다른 작업자의 변경으로 이전 상태가 달라졌으면 저장을 거절하고 재조회를 안내한다. 동일 request_id 재시도는 중복 조치를 남기지 않는다. 다른 컴퓨터에서 같은 영상을 재생하는 것만으로 완료된 사건을 다시 열지 않는다(같은 이벤트 ID/중요도 재전송 방지).

연결 실패 시 로컬에 몰래 대체 저장하지 않는다. 조치 저장은 실패로 응답하고 사건/통계 화면에 연결 실패를 표시한다. 영상/감지/알림 처리는 계속 동작한다. 끊긴 동안 서버가 받지 못한 감지는 자동 소급 전송하지 않는다. 연결 복구 후 실제 재생에서 감지된 자료부터 반영한다.

## 서버 컴퓨터

기존 workspace와 runtime 자료가 설치된 컴퓨터 한 대를 서버로 선택한다. safety 환경에서 저장소 루트로 이동한다. 아래 토큰은 팀이 사용할 충분히 긴 임의 문자열로 정하고 명령 출력·Git에 올리지 않는다. 서버와 모든 클라이언트는 같은 토큰을 사용한다. 토큰은 대시보드 Python 프로세스에만 있으며 브라우저 JS에는 전달하지 않는다.

macOS/Linux:

```sh
export SISUN_CASE_TOKEN='팀에서_정한_긴_임의_접속키'
unset SISUN_CASE_SERVER
python -m dashboard.case_server --host 0.0.0.0 --port 8020 --db outputs/backend/shared_cases.sqlite3
```

Windows PowerShell:

```powershell
$env:SISUN_CASE_TOKEN='팀에서_정한_긴_임의_접속키'
Remove-Item Env:SISUN_CASE_SERVER -ErrorAction SilentlyContinue
python -m dashboard.case_server --host 0.0.0.0 --port 8020 --db outputs/backend/shared_cases.sqlite3
```

공용 사건 서버는 대시보드(7860)와 영상 이벤트 API(8010)와 별도 프로세스다. 다른 컴퓨터가 접속 가능한 서버 IP와 8020 포트가 필요하다. 기본 HTTP는 신뢰 가능한 사내망 시험용이며 인터넷으로 공개하지 않는다. 다른 네트워크 연결은 HTTPS 프록시/VPN을 구성한 뒤 사용한다. 서버 시간대를 한국 시간으로 맞춘다.

## 기존 기록 최초 가져오기 (선택·한 번만)

먼저 서버를 종료하고 원본 JSONL과 DB를 백업한다. 비어 있는 새 DB에만 가져올 수 있으며 이미 기록이 있는 DB에는 명령이 실패한다. 원본 파일은 변경하지 않는다. 여러 PC의 기록을 자동 병합하지 않고 기준 PC 한 곳의 기록만 최초 자료로 선택한다.

```sh
python -m dashboard.case_server --db outputs/backend/shared_cases.sqlite3 --import-log dashboard/data/alert_response_log.jsonl --import-only
```

서버 컴퓨터에 위 SISUN_CASE_TOKEN을 설정한 상태에서 실행한다. 이후 `--import-log` 없이 서버를 실행한다. SQLite DB를 복사할 때는 서버를 종료한다.

## 각 작업자 컴퓨터

서버 IP 예: 192.168.0.10. 실제 서버 IP로 바꾼다. 서버 컴퓨터에서 대시보드도 실행하면 그 대시보드에도 클라이언트 변수를 설정한다.

macOS/Linux:

```sh
export SISUN_CASE_SERVER='http://192.168.0.10:8020'
export SISUN_CASE_TOKEN='서버와_동일한_접속키'
python dashboard.py
```

Windows PowerShell:

```powershell
$env:SISUN_CASE_SERVER='http://192.168.0.10:8020'
$env:SISUN_CASE_TOKEN='서버와_동일한_접속키'
python dashboard.py
```

기존 실행 프로세스를 종료하고 같은 터미널에서 실행한다. 앱 창은 같은 변수 설정 후 `python dashboard_desktop.py`로 실행한다. 바탕화면 아이콘에 환경 변수가 자동 전달된다고 가정하지 않는다.

A가 확인하면 B의 기존 사건 화면 주기 조회에 반영된다(네트워크 상태와 기존 폴링 주기에 따라 수 초). 통계는 기존 새로고침 버튼으로 조회한다. 기존 로그인 사용자명이 실제 처리자로 기록되며 A~D 배정 담당자는 공유 상태로 한 번만 배정한다. 접속키는 컴퓨터의 서버 접근 권한이며 별도 계정별 권한/SSO 시스템을 추가한 것은 아니다.

## 로컬 모드 복귀

서버를 끄기만 하면 로컬로 전환되는 방식이 아니다. 아래 변수들을 지운 뒤 대시보드를 완전히 종료/재실행한다. 기존 로컬 파일은 그대로 남아 있으며 공용 DB의 변경은 자동으로 로컬에 복사하지 않는다.

```sh
unset SISUN_CASE_SERVER SISUN_CASE_TOKEN
python dashboard.py
```

PowerShell: `Remove-Item Env:SISUN_CASE_SERVER,Env:SISUN_CASE_TOKEN -ErrorAction SilentlyContinue` 후 재실행.

## 구현 및 한계

`dashboard/case_server.py`는 공용 API/SQLite 트랜잭션, `dashboard/shared_cases.py`는 선택적 서버 연결이다. 기존 `alert_response`는 같은 전이/표시 로직을 유지하고 공유 스냅샷을 읽는다. 기본 로컬 JSONL은 그대로다. SQLite 파일을 네트워크 폴더에서 여러 클라이언트가 직접 열지 않고 한 서버의 HTTP API로만 접근한다. 서버 장비 장애 대비 백업/상시 운영은 별도 운영 작업이다. 현재 컴퓨터의 기본 모드는 자동으로 변경하지 않았다.
