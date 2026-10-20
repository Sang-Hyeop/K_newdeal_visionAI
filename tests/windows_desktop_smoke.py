# 역할: Windows 새 설치에서 실제 서버·앱 창의 종료·재실행·강제 종료 복구를 검증합니다.
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

import psutil

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SISUN_UI_PORT'] = '17860'
os.environ['SISUN_API_PORT'] = '18010'
os.environ['SISUN_NO_DIALOG'] = '1'
from dashboard import windows_desktop as desktop


def wait(predicate, description, seconds=180):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.5)
    raise RuntimeError('대기 실패: ' + description)


def start():
    process = subprocess.Popen([sys.executable, str(ROOT / 'dashboard_desktop.py')], cwd=ROOT)
    wait(lambda: desktop.healthy() or process.poll() is not None, '서버 기동')
    if process.poll() is not None:
        raise RuntimeError('서버 시작 실패: ' + (ROOT / 'dashboard/data/desktop.log').read_text(encoding='utf-8'))
    profile = ROOT / 'dashboard/data/sisun_chrome_profile'
    wait(lambda: bool(desktop.browser_processes(profile)), '실제 Edge/Chrome 앱 창', 40)
    with urllib.request.urlopen(desktop.URL + '/config') as response:
        config = json.load(response)
    videos = [c for c in config['components'] if c['type'] == 'video']
    assert len(videos) >= 6, '6개 영상 컴포넌트 누락'
    return process, profile


def verify_login_and_video():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(desktop.URL, timeout=60000)
        page.get_by_placeholder('아이디').fill('김상협')
        page.get_by_placeholder('비밀번호').fill('1234')
        page.get_by_role('button', name='로그인', exact=True).click()
        page.locator('#sisun-side').wait_for(state='visible', timeout=120000)
        page.wait_for_function("""() => {
            const panel = [...document.querySelectorAll('.sisun-panel')].find(p => p.offsetParent !== null);
            const videos = panel ? [...panel.querySelectorAll('video')] : [];
            return videos.length >= 6 && videos.every(v => v.readyState >= 2);
        }""", timeout=180000)
        wait(lambda: len(page.locator('.t2-kpi').all()) >= 6, 'KPI 표시')
        # 첫 영상 변환을 기다리는 동안 타임라인이 진행될 수 있으므로 준비 후 새로고침합니다.
        page.locator('.sisun-panel:visible').get_by_role('button', name='새로고침', exact=True).click()
        page.wait_for_timeout(1500)
        before = page.locator('.t2-kpi').first.inner_text()
        print('KPI before:', repr(before), flush=True)
        print('Video state:', page.locator('.sisun-panel:visible video').evaluate_all(
            'vs => vs.map(v => ({time:v.currentTime, paused:v.paused, ready:v.readyState, duration:v.duration}))'), flush=True)
        page.screenshot(path=str(ROOT / 'dashboard/data/windows-main.png'), full_page=True)
        wait(lambda: before != page.locator('.t2-kpi').first.inner_text(), '재생 중 KPI 갱신', 40)
        after = page.locator('.t2-kpi').first.inner_text()
        print('KPI after:', repr(after), flush=True)
        with urllib.request.urlopen('http://127.0.0.1:18010/events?limit=1') as response:
            assert json.load(response)['total'] > 0
        page.screenshot(path=str(ROOT / 'dashboard/data/windows-main.png'), full_page=True)
        assert not errors, errors
        browser.close()
    print('로그인·6영상 재생·KPI 갱신·이벤트 API 검증 통과', flush=True)


if __name__ == '__main__':
    parent = None
    try:
        for cycle in range(2):
            parent, profile = start()
            if cycle == 0:
                verify_login_and_video()
            # 같은 실행 중 다시 클릭해도 기존 서버는 유지합니다.
            duplicate = subprocess.run([sys.executable, str(desktop.ENTRY)], timeout=45)
            assert duplicate.returncode == 0 and desktop.healthy()
            for browser in desktop.browser_processes(profile):
                desktop.stop_tree(browser)
            assert parent.wait(timeout=30) == 0
            wait(lambda: not desktop.healthy(), '창 종료 후 서버 종료', 20)
            print('실제 앱 종료 및 재실행 검증:', cycle + 1, flush=True)
        parent, profile = start()
        parent.kill()
        parent.wait(timeout=10)
        wait(lambda: not desktop.healthy(), '강제 종료 후 고아 서버 종료', 20)
        for browser in desktop.browser_processes(profile):
            desktop.stop_tree(browser)
        parent, profile = start()
        for browser in desktop.browser_processes(profile):
            desktop.stop_tree(browser)
        assert parent.wait(timeout=30) == 0
        print('강제 종료 후 재실행 검증 통과', flush=True)
    finally:
        if parent and parent.poll() is None:
            desktop.stop_tree(psutil.Process(parent.pid))
