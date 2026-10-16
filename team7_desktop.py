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

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ["SISUN_DESKTOP"] = "1"
os.environ.setdefault("SISUN_UI_PORT", "7860")

UI_PORT = int(os.environ["SISUN_UI_PORT"])
UI_URL = f"http://127.0.0.1:{UI_PORT}"
LOG = ROOT / "team7_data" / "desktop.log"
os.makedirs(LOG.parent, exist_ok=True)
_LOGF = open(LOG, "a", encoding="utf-8", buffering=1)
if sys.stdout is None:
    sys.stdout = _LOGF
if sys.stderr is None:
    sys.stderr = _LOGF


def log(msg):
    os.makedirs(LOG.parent, exist_ok=True)
    line = time.strftime("%H:%M:%S ") + str(msg)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
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
        from team7_app.app import launch
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
    return _hidden_run([ps, "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd], text=True)


def kill_port(port):
    log("포트 정리 " + str(port))
    if os.name == "nt":
        _ps(
            f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
            "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
        )
    time.sleep(0.8)


def kill_app_chrome():
    marker = "sisun_chrome_profile"
    if os.name != "nt":
        return
    _ps(
        "Get-CimInstance Win32_Process | Where-Object { "
        "($_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe') -and "
        "($_.CommandLine -like '*" + marker + "*') } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )


def acquire_lock():
    global _LOCK_FP
    path = ROOT / "team7_data" / "desktop.lock"
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
    _LOCK_FP = fp
    return True


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
        from team7_app.api import API_PORT, _stop_api
        _stop_api(API_PORT)
    except Exception as e:
        log("api stop " + str(e))


def main():
    log("시선 데스크톱 시작 " + sys.executable + " pid=" + str(os.getpid()))
    kill_app_chrome()
    kill_port(UI_PORT)
    if not acquire_lock():
        log("이미 실행 중. 창만 다시 엽니다.")
        if wait_ui(tries=30):
            browser = find_browser()
            if browser:
                profile = ROOT / "team7_data" / "sisun_chrome_profile"
                subprocess.Popen([
                    str(browser), f"--app={UI_URL}",
                    f"--user-data-dir={profile}",
                    "--no-first-run", "--no-default-browser-check", "--new-window",
                ])
            return 0
        return 1
    threading.Thread(target=start_ui, daemon=True).start()
    if not wait_ui():
        log("화면 서버가 안 켜졌습니다. " + str(LOG))
        stop_backend()
        return 1
    browser = find_browser()
    profile = ROOT / "team7_data" / "sisun_chrome_profile"
    marker = "sisun_chrome_profile"
    os.makedirs(profile, exist_ok=True)
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
    cmd = [
        str(browser),
        f"--app={UI_URL}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
    ]
    log("앱 창 " + str(browser))
    subprocess.Popen(cmd)
    for _ in range(20):
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
