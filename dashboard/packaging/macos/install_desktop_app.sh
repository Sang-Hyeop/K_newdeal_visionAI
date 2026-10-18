#!/bin/bash
# (고급) 터미널 설치. 일반 사용자는 루트 macOS용_시선설치.command 더블클릭.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec bash "$ROOT/macOS용_시선설치.command"
