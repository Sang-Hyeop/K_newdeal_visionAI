# 역할: Windows 앱의 단일 실행·창 수명·서버 종료와 응답 없는 이전 실행을 관리합니다.
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'dashboard/data'
ENTRY = ROOT / 'dashboard_desktop.py'
URL = 'http://127.0.0.1:' + os.environ.get('SISUN_UI_PORT', '7860')


def owned_launcher(process):
    """PID만 믿지 않고 실제 실행 파일의 프로젝트 경로까지 확인합니다."""
    try:
        return any(Path(arg).resolve() == ENTRY for arg in process.cmdline()[1:])
    except (psutil.Error, OSError, ValueError):
        return False


def stop_tree(process):
    """호출자가 소유권을 확인한 프로세스와 그 자식만 종료합니다."""
    try:
        children = process.children(recursive=True)
        targets = children + [process]
        for child in targets:
            try:
                child.terminate()
            except psutil.Error:
                pass
        _, alive = psutil.wait_procs(targets, timeout=5)
        for child in alive:
            try:
                child.kill()
            except psutil.Error:
                pass
    except psutil.Error:
        pass


class InstanceLock:
    """잠금 파일은 삭제하지 않고 OS 잠금과 PID 생성 시각을 함께 보관합니다."""
    def __init__(self, path):
        self.path = Path(path)
        self.stream = None

    def acquire(self):
        import msvcrt
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open('a+b')
        try:
            if self.path.stat().st_size == 0:
                stream.write(b' ')
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            stream.close()
            return False
        self.stream = stream
        metadata = {'pid': os.getpid(), 'created': psutil.Process().create_time()}
        stream.seek(1)
        stream.truncate()
        stream.write(json.dumps(metadata).encode('ascii'))
        stream.flush()
        return True

    def release(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None


def healthy():
    try:
        with urllib.request.urlopen(URL + '/config', timeout=1) as response:
            data = json.load(response)
        return 'components' in data
    except (OSError, ValueError):
        return False


def browser_path():
    for base in (os.environ.get('PROGRAMFILES'), os.environ.get('PROGRAMFILES(X86)'), os.environ.get('LOCALAPPDATA')):
        if not base:
            continue
        for name in ('Microsoft/Edge/Application/msedge.exe', 'Google/Chrome/Application/chrome.exe'):
            candidate = Path(base) / name
            if candidate.is_file():
                return candidate
    raise RuntimeError('Microsoft Edge 또는 Google Chrome이 필요합니다.')


def browser_processes(profile):
    marker = os.path.normcase(str(profile.resolve()))
    found = []
    for process in psutil.process_iter(['name', 'cmdline']):
        try:
            if (process.info['name'] or '').lower() not in ('chrome.exe', 'msedge.exe'):
                continue
            for arg in process.info['cmdline'] or []:
                if arg.startswith('--user-data-dir=') and os.path.normcase(arg.split('=', 1)[1].strip('"')) == marker:
                    found.append(process)
                    break
        except psutil.Error:
            continue
    return found


def open_window(profile):
    subprocess.Popen([str(browser_path()), '--app=' + URL, '--user-data-dir=' + str(profile),
                      '--no-first-run', '--no-default-browser-check', '--new-window'])


def recover_unresponsive():
    """기동 유예가 지난 같은 프로젝트 실행만 복구합니다. 다른 Python은 건드리지 않습니다."""
    for process in psutil.process_iter():
        try:
            if process.pid == os.getpid() or not owned_launcher(process):
                continue
            if '--server-worker' in process.cmdline():
                continue
            if time.time() - process.create_time() < 150:
                continue
            if healthy():
                return
            stop_tree(process)
        except psutil.Error:
            continue


def server_worker(parent_pid, parent_created):
    """부모가 강제 종료되어도 서버·이벤트 API가 고아 프로세스로 남지 않게 합니다."""
    def watch_parent():
        while True:
            try:
                parent = psutil.Process(parent_pid)
                if abs(parent.create_time() - parent_created) > 0.01:
                    break
            except psutil.Error:
                break
            time.sleep(1)
        for child in psutil.Process().children(recursive=True):
            stop_tree(child)
        os._exit(0)
    threading.Thread(target=watch_parent, daemon=True).start()
    from dashboard.app import launch
    launch()
    return 0


def run():
    DATA.mkdir(parents=True, exist_ok=True)
    profile = DATA / 'sisun_chrome_profile'
    lock = InstanceLock(DATA / 'desktop.lock')
    if not lock.acquire():
        deadline = time.monotonic() + 125
        while time.monotonic() < deadline:
            if healthy():
                open_window(profile)
                return 0
            if lock.acquire():
                break
            time.sleep(1)
        else:
            recover_unresponsive()
            if not lock.acquire():
                raise RuntimeError('기존 시선이 시작 중이거나 종료되지 않았습니다. 잠시 후 다시 실행해 주세요.')
    server = None
    try:
        if healthy():
            raise RuntimeError('7860 포트를 다른 대시보드가 사용 중입니다. 해당 프로그램을 먼저 종료해 주세요.')
        for process in browser_processes(profile):
            stop_tree(process)
        browser_path()  # 서버를 띄우기 전에 실행 가능 여부를 확인합니다.
        env = dict(os.environ, SISUN_DESKTOP='1')
        server = subprocess.Popen([sys.executable, str(ENTRY), '--server-worker', str(os.getpid()),
                                   str(psutil.Process().create_time())], cwd=ROOT, env=env,
                                  stdout=sys.stdout, stderr=sys.stderr,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 180
        while not healthy():
            if server.poll() is not None:
                raise RuntimeError('화면 서버 시작에 실패했습니다. dashboard/data/desktop.log를 확인해 주세요.')
            if time.monotonic() > deadline:
                raise RuntimeError('화면 서버 시작 대기 시간을 초과했습니다.')
            time.sleep(0.5)
        open_window(profile)
        deadline = time.monotonic() + 30
        while not browser_processes(profile):
            if time.monotonic() > deadline:
                raise RuntimeError('앱 창을 열지 못했습니다. Edge/Chrome 실행 상태를 확인해 주세요.')
            time.sleep(0.5)
        while browser_processes(profile):
            if server.poll() is not None:
                raise RuntimeError('화면 서버가 종료되었습니다. 로그를 확인해 주세요.')
            time.sleep(1)
        return 0
    finally:
        if server is not None:
            try:
                stop_tree(psutil.Process(server.pid))
            except psutil.Error:
                pass
        lock.release()


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / 'desktop.log').open('a', encoding='utf-8', buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            if '--server-worker' in sys.argv:
                return server_worker(int(sys.argv[-2]), float(sys.argv[-1]))
            return run()
        except Exception:
            import traceback
            traceback.print_exc()
            if '--server-worker' not in sys.argv:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, '시선 실행에 실패했습니다.\n' + str(DATA / 'desktop.log'), '시선', 16)
            return 1
