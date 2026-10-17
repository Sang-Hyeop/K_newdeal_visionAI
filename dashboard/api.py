# 이벤트 API 켜기·읽기
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import API_BASE, API_PORT, DATA_ROOT, LOCAL

API_PROC = None
_RUNTIME_CACHE = None
_RUNTIME_MTIME = None
_JSONL_COUNT_CACHE = None


def api_get(path, params=None):
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_up():
    try:
        api_get("/events", {"limit": 1})
        return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return False


def runtime_index():
    """team-runtime-index.json 캐시 (파일 mtime 바뀔 때만 다시 읽음)."""
    global _RUNTIME_CACHE, _RUNTIME_MTIME
    path = DATA_ROOT / "configs" / "team-runtime-index.json"
    try:
        mtime = path.stat().st_mtime if path.is_file() else None
    except OSError:
        mtime = None
    if _RUNTIME_CACHE is not None and mtime == _RUNTIME_MTIME:
        return _RUNTIME_CACHE
    if path.is_file():
        _RUNTIME_CACHE = json.loads(path.read_text(encoding="utf-8"))
    else:
        _RUNTIME_CACHE = {"videos": []}
    _RUNTIME_MTIME = mtime
    return _RUNTIME_CACHE


def presentation_row(num):
    want = int(num)
    for row in runtime_index().get("videos") or []:
        if int(row.get("presentation_video_number") or 0) == want:
            return row
    return None


def sample_root():
    """발표 1~5 이벤트만. backend_v1/samples 더미 40건은 쓰지 않음."""
    events = DATA_ROOT / "outputs" / "events"
    if events.is_dir() and any(events.rglob("events_v1.jsonl")):
        return events
    raise FileNotFoundError("GitHub 발표 이벤트 outputs/events 가 없습니다.")


def _jsonl_event_count():
    global _JSONL_COUNT_CACHE
    if _JSONL_COUNT_CACHE is not None:
        return _JSONL_COUNT_CACHE
    n = 0
    for path in sample_root().rglob("events_v1.jsonl"):
        with path.open(encoding="utf-8") as f:
            n += sum(1 for line in f if line.strip())
    _JSONL_COUNT_CACHE = n
    return n


def _stop_api(port):
    global API_PROC
    if API_PROC is not None:
        try:
            API_PROC.terminate()
        except OSError:
            pass
        API_PROC = None
    if os.name == "nt":
        cmd = (
            f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
            "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
        )
        ps = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            r"System32\WindowsPowerShell\v1.0\powershell.exe",
        )
        flags = subprocess.CREATE_NO_WINDOW
        subprocess.run(
            [ps, "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    else:
        subprocess.run(
            ["bash", "-c", f"lsof -ti tcp:{port} | xargs kill -9 2>/dev/null || true"],
            check=False,
            capture_output=True,
        )
    time.sleep(0.8)


def ensure_api():
    global API_PROC
    expected = _jsonl_event_count()
    if api_up():
        total = int((api_get("/events", {"limit": 1}) or {}).get("total") or 0)
        if expected and abs(total - expected) <= 5:
            print("API", API_BASE, "events", total)
            return
        print("API 로그가 예전입니다. 다시 시작합니다.", total, "->", expected)
        _stop_api(API_PORT)
    os.makedirs(LOCAL, exist_ok=True)
    backend = DATA_ROOT / "backend_v1" / "backend.py"
    if not backend.is_file():
        raise FileNotFoundError(f"백엔드가 없습니다: {backend}")
    log_path = os.path.join(LOCAL, "api.log")
    cmd = [
        sys.executable, str(backend),
        "--host", "127.0.0.1", "--port", str(API_PORT),
        "--samples", str(sample_root()),
        "--db", str(DATA_ROOT / "outputs" / "backend" / "full_review.sqlite3"),
    ]
    cwd = str(backend.parent)
    print("API 시작", " ".join(cmd))
    log = open(log_path, "w", encoding="utf-8")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    API_PROC = subprocess.Popen(
        cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, creationflags=flags,
    )
    for _ in range(80):
        time.sleep(0.5)
        if api_up():
            print("API", API_BASE)
            return
    raise RuntimeError(f"API 시작 실패 {API_BASE} · 로그 {log_path}")


def load_events():
    ensure_api()
    found = []
    offset = 0
    limit = 500
    while True:
        data = api_get("/events", {"limit": limit, "offset": offset})
        batch = data.get("events") or []
        found.extend(batch)
        total = int(data.get("total") or 0)
        offset += len(batch)
        if not batch or offset >= total:
            break
    return found
