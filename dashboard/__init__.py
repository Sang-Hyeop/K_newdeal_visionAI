# 시선 대시보드 패키지 (backend_v1 과 같이 폴더에 모음)
# 실행: 저장소 루트 dashboard.py / dashboard_desktop.py
#
# config  경로·구역·탭·로그인
# style   CSS·시계 JS·테마
# api     이벤트 서버
# media   발표 영상·H.264
# events  로그 표
# sound   알람
# ui      로그인·KPI HTML
# app     탭 조립
# desktop Chrome/Edge 앱 창


def launch(*args, **kwargs):
    """지연 import — desktop 등 가벼운 진입이 app 전체를 안 끌어오게."""
    from .app import launch as _launch
    return _launch(*args, **kwargs)
