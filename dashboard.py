# dashboard.py — 시선 대시보드 실행 (브라우저)
# 구현은 dashboard/ 패키지. 데스크톱 창은 dashboard_desktop.py
# python dashboard.py

from dashboard.app import launch

if __name__ == "__main__":
    print("login  김상협·이수민·박회승·최인승 / 1234")
    print("open http://127.0.0.1:7860")
    launch()
