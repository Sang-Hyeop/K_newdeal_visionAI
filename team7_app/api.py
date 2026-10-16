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
    path = DATA_ROOT / "configs" / "team-runtime-index.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"videos": []}


def presentation_row(num):
    for row in runtime_index().get("videos") or []:
        if int(row.get("presentation_video_number") or 0) == int(num):
            return row
    return None


def sample_root():
    """발표 1~5 이벤트만. backend_v1/samples 더미 40건은 쓰지 않음."""
    events = DATA_ROOT / "outputs" / "events"
    if events.is_dir() and list(events.rglob("events_v1.jsonl")):
        return events
    raise FileNotFoundError("GitHub 발표 이벤트 outputs/events 가 없습니다.")


def _jsonl_event_count():
    n = 0
    for path in sample_root().rglob("events_v1.jsonl"):
        with path.open(encoding="utf-8") as f:
            n += sum(1 for line in f if line.strip())
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
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.run(
            [ps, "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    time.sleep(1)


def find_demo(num):
    """확정 리뷰(선·상자)를 먼저 쓰고, 없을 때만 handoff 임시 결과를 쓴다."""
    row = presentation_row(num)
    if row and row.get("review_video"):
        review = DATA_ROOT / row["review_video"]
        if review.is_file() and review.stat().st_size > 0:
            return review
    found = []
    runs = DATA_ROOT / "outputs" / "handoff_runs"
    if runs.is_dir():
        found += [p for p in runs.glob(f"presentation{num}_*/**/demo.mp4") if p.is_file() and p.stat().st_size > 0]
        found += [p for p in runs.glob(f"presentation{num}_*/*.mp4") if p.is_file() and p.stat().st_size > 0]
    if not found:
        return None
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found[0]


def ensure_repo_demos():
    """발표 1~4 결과 영상이 없으면 handoff.py run 으로 만든다."""
    handoff = DATA_ROOT / "handoff.py"
    if not handoff.is_file():
        print("handoff.py 가 없습니다.", DATA_ROOT)
        return
    for n in NEEDED_VIDEOS:
        if find_demo(n) is not None:
            continue
        cmd = [sys.executable, str(handoff), "run", "--video", str(n)]
        print("handoff 생성", " ".join(cmd))
        subprocess.run(cmd, cwd=str(DATA_ROOT), check=False)


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
