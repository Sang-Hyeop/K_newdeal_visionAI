# 역할: 안전관제 대시보드를 데스크톱 앱 창으로 실행합니다.
# dashboard_desktop.py — 시선 데스크톱 앱 창 실행 (루트 진입점)
# 구현: macOS는 dashboard/desktop.py, Windows는 dashboard/windows_desktop.py
# python dashboard_desktop.py

import os

if os.name == "nt":
    from dashboard.windows_desktop import main
else:
    from dashboard.desktop import main

if __name__ == "__main__":
    raise SystemExit(main())
