# 역할: 브라우저 앱 창과 대시보드 프로세스의 시작·종료를 관리합니다.
# 시선 데스크톱 창. 브라우저 탭이 아니라 Chrome/Edge 앱 창으로 연다.
# 창을 닫으면 Gradio·이벤트 API도 같이 끈다.
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

DASHBOARD_DIR = Path(__file__).resolve().parent
ROOT = DASHBOARD_DIR.parent  # 저장소 루트
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ["SISUN_DESKTOP"] = "1"
os.environ.setdefault("SISUN_UI_PORT", "7860")

UI_PORT = int(os.environ["SISUN_UI_PORT"])
UI_URL = f"http://127.0.0.1:{UI_PORT}"
LOG = DASHBOARD_DIR / "data" / "desktop.log"
os.makedirs(LOG.parent, exist_ok=True)
# 로그가 너무 커지면 잘라 둠 (반복 실행 시 디스크·열기 지연 방지)
try:
    if LOG.is_file() and LOG.stat().st_size > 2_000_000:
        LOG.write_text("", encoding="utf-8")
except OSError:
    pass
_LOGF = open(LOG, "a", encoding="utf-8", buffering=1)


def _stdout_is_our_log():
    """pythonw / nohup >> desktop.log 등으로 stdout 이 이미 로그인 경우."""
    if sys.stdout is None:
        return True
    try:
        name = getattr(sys.stdout, "name", None)
        if name and name not in ("<stdout>", "<stderr>"):
            return Path(name).resolve() == LOG.resolve()
    except OSError:
        pass
    return False


_STDOUT_IS_LOG = _stdout_is_our_log()
if sys.stdout is None:
    sys.stdout = _LOGF
    _STDOUT_IS_LOG = True
if sys.stderr is None:
    sys.stderr = _LOGF


def log(msg):
    line = time.strftime("%H:%M:%S ") + str(msg)
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    # stdout 이 이미 로그면 print 로 한 번 더 쓰지 않음
    if _STDOUT_IS_LOG:
        return
    try:
        print(line, flush=True)
    except OSError:
        pass


def wait_ui(tries=240):
    for _ in range(tries):
        try:
            urllib.request.urlopen(UI_URL, timeout=1)
            return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.5)
    return False


def find_browser():
    home = Path.home()
    if os.name == "nt":
        pf = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        pf86 = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        local = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData/Local")))
        cands = [
            pf / "Google/Chrome/Application/chrome.exe",
            pf86 / "Google/Chrome/Application/chrome.exe",
            local / "Google/Chrome/Application/chrome.exe",
            pf / "Microsoft/Edge/Application/msedge.exe",
            pf86 / "Microsoft/Edge/Application/msedge.exe",
            local / "Microsoft/Edge/Application/msedge.exe",
        ]
    else:
        cands = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    for path in cands:
        if path.is_file():
            return path
    return None


def start_ui():
    try:
        from dashboard.app import launch

        launch()
    except Exception as e:
        log("ui 오류 " + repr(e))
        raise


_LOCK_FP = None


def _hidden_run(args, **kw):
    """Windows에서 검은 콘솔이 깜빡이지 않게 실행."""
    kw.setdefault("capture_output", True)
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        kw["startupinfo"] = si
        kw["creationflags"] = kw.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
    return subprocess.run(args, **kw)


def _ps(cmd):
    ps = os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"),
        r"System32\WindowsPowerShell\v1.0\powershell.exe",
    )
    return _hidden_run(
        [ps, "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd], text=True
    )


def kill_port(port):
    log("포트 정리 " + str(port))
    if os.name == "nt":
        _ps(
            f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
            "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
        )
    else:
        subprocess.run(
            ["bash", "-c", f"lsof -ti tcp:{port} | xargs kill -9 2>/dev/null || true"],
            capture_output=True,
        )
    time.sleep(0.8)


def kill_app_chrome():
    marker = "sisun_chrome_profile"
    if os.name == "nt":
        _ps(
            "Get-CimInstance Win32_Process | Where-Object { "
            "($_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe') -and "
            "($_.CommandLine -like '*" + marker + "*') } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        return
    subprocess.run(
        ["pkill", "-f", marker],
        capture_output=True,
    )


def acquire_lock():
    global _LOCK_FP
    path = DASHBOARD_DIR / "data" / "desktop.lock"
    os.makedirs(path.parent, exist_ok=True)
    fp = open(path, "a+")
    if os.name == "nt":
        import msvcrt

        try:
            fp.seek(0)
            msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            fp.close()
            return False
    else:
        import fcntl

        try:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fp.close()
            return False
    _LOCK_FP = fp
    return True


def open_app_window(browser, url, profile):
    """Chrome/Edge 앱 창. macOS는 open 으로 띄워 .app 샌드박스 권한 문제를 피한다."""
    profile = str(profile)
    if sys.platform == "darwin":
        name = "Microsoft Edge" if "Edge" in str(browser) else "Google Chrome"
        subprocess.Popen(
            [
                "open",
                "-na",
                name,
                "--args",
                f"--app={url}",
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--no-default-browser-check",
                "--new-window",
            ]
        )
        return
    subprocess.Popen(
        [
            str(browser),
            f"--app={url}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
        ]
    )


def browser_using_profile(marker):
    marker = str(marker).replace("'", "")
    if os.name == "nt":
        cmd = (
            "$n = @(Get-CimInstance Win32_Process | Where-Object { "
            "($_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe') -and "
            "($_.CommandLine -like '*" + marker + "*') }).Count; Write-Output $n"
        )
        ps = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            r"System32\WindowsPowerShell\v1.0\powershell.exe",
        )
        r = _hidden_run(
            [ps, "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd],
            text=True,
        )
        try:
            return int((r.stdout or "0").strip().split()[-1]) > 0
        except (ValueError, IndexError):
            return False
    r = subprocess.run(["pgrep", "-f", marker], capture_output=True)
    return r.returncode == 0


def stop_backend():
    try:
        from dashboard.api import API_PORT, _stop_api

        _stop_api(API_PORT)
    except Exception as e:
        log("api stop " + str(e))


def _reopen_window():
    browser = find_browser()
    if browser is None:
        return False
    profile = DASHBOARD_DIR / "data" / "sisun_chrome_profile"
    open_app_window(browser, UI_URL, profile)
    return True


def main():
    log("시선 데스크톱 시작 " + sys.executable + " pid=" + str(os.getpid()))
    profile = DASHBOARD_DIR / "data" / "sisun_chrome_profile"
    marker = "sisun_chrome_profile"
    os.makedirs(profile, exist_ok=True)

    # 잠금을 먼저 잡는다. (예전엔 포트부터 죽여서 살아 있던 서버를 끊고 실패했음)
    if not acquire_lock():
        log("이미 실행 중. 창만 다시 엽니다.")
        if wait_ui(tries=30):
            _reopen_window()
            return 0
        log("잠금만 남고 서버가 없습니다. 정리 후 다시 시작합니다.")
        try:
            (DASHBOARD_DIR / "data" / "desktop.lock").unlink(missing_ok=True)
        except OSError:
            pass
        if not acquire_lock():
            log("잠금을 얻지 못했습니다.")
            return 1

    kill_app_chrome()
    kill_port(UI_PORT)
    threading.Thread(target=start_ui, daemon=True).start()
    if not wait_ui():
        log("화면 서버가 안 켜졌습니다. " + str(LOG))
        stop_backend()
        return 1
    browser = find_browser()
    if browser is None:
        log("Chrome/Edge 없음. 기본 브라우저로 엽니다.")
        import webbrowser

        webbrowser.open(UI_URL)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        stop_backend()
        return 0
    log("앱 창 " + str(browser))
    open_app_window(browser, UI_URL, profile)
    for _ in range(40):
        time.sleep(0.5)
        if browser_using_profile(marker):
            break
    if not browser_using_profile(marker):
        log("앱 창 프로세스 없음. 서버는 유지합니다.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        stop_backend()
        return 0
    while browser_using_profile(marker):
        time.sleep(1)
    log("창 닫힘. 서버 종료")
    stop_backend()
    os._exit(0)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        log("오류 " + repr(e))
        stop_backend()
        raise
