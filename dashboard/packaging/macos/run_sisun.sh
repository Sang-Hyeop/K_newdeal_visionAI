#!/bin/bash
# 시선 실행기 (공용) — 프로젝트 루트 또는 앱 안 sisun_root 기준으로 동작
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HERE=""

# 1) 바탕화면 시선.app 에 심어진 경우: Resources/sisun_root
if [ -f "$SCRIPT_DIR/sisun_root" ]; then
  HERE="$(tr -d '\r\n' < "$SCRIPT_DIR/sisun_root")"
fi

# 2) 저장소 packaging/macos 에서 직접 실행
if [ -z "${HERE}" ] && [ -f "$SCRIPT_DIR/../../../dashboard_desktop.py" ]; then
  HERE="$(cd "$SCRIPT_DIR/../../../" && pwd)"
fi

# 3) 상위로 탐색
if [ -z "${HERE}" ] || [ ! -f "$HERE/dashboard_desktop.py" ]; then
  HERE=""
  DIR="$SCRIPT_DIR"
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
    DIR="$(cd "$DIR/.." && pwd)"
    if [ -f "$DIR/dashboard_desktop.py" ]; then
      HERE="$DIR"
      break
    fi
  done
fi

if [ -z "${HERE}" ] || [ ! -f "$HERE/dashboard_desktop.py" ]; then
  osascript -e 'display alert "시선" message "dashboard_desktop.py 를 찾지 못했습니다.\nmacOS용_시선설치.command 로 다시 설치하세요."' 2>/dev/null || true
  exit 1
fi

cd "$HERE"
export SISUN_DESKTOP=1
export PATH="${HOME}/anaconda3/envs/safety/bin:${HOME}/miniconda3/envs/safety/bin:${HOME}/miniforge3/envs/safety/bin:${HOME}/mambaforge/envs/safety/bin:/opt/anaconda3/envs/safety/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

find_python() {
  local cand
  for cand in \
    "${HOME}/anaconda3/envs/safety/bin/python" \
    "${HOME}/miniconda3/envs/safety/bin/python" \
    "${HOME}/miniforge3/envs/safety/bin/python" \
    "${HOME}/mambaforge/envs/safety/bin/python" \
    "${HOME}/opt/anaconda3/envs/safety/bin/python" \
    "/opt/anaconda3/envs/safety/bin/python" \
    "/opt/miniconda3/envs/safety/bin/python" \
    "/usr/local/anaconda3/envs/safety/bin/python" \
    "/usr/local/Caskroom/miniconda/base/envs/safety/bin/python"
  do
    if [ -x "$cand" ]; then
      echo "$cand"
      return 0
    fi
  done
  if command -v python3 >/dev/null 2>&1; then command -v python3; return 0; fi
  if command -v python >/dev/null 2>&1; then command -v python; return 0; fi
  return 1
}

PY="$(find_python || true)"
if [ -z "${PY}" ]; then
  osascript -e 'display alert "시선" message "Python 을 찾지 못했습니다.\nPython 3.10+ 또는 Anaconda safety 환경과\npip install gradio pandas 가 필요합니다."' 2>/dev/null || true
  exit 1
fi

mkdir -p "$HERE/dashboard/data"
LOG="$HERE/dashboard/data/desktop.log"
{
  echo "---- $(date '+%Y-%m-%d %H:%M:%S') app launch ----"
  echo "HERE=$HERE"
  echo "PY=$PY"
} >>"$LOG" 2>&1

nohup "$PY" "$HERE/dashboard_desktop.py" >>"$LOG" 2>&1 &
exit 0
