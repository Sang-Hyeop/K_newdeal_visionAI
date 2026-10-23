# 역할: 선택적 공용 사건 서버 통신과 짧은 조회 캐시를 관리합니다.
"""선택적 공용 사건 서버 통신과 짧은 조회 캐시를 관리합니다."""

import json
import os
import threading
import time
import urllib.error
import urllib.request

_CACHE = None
_CACHE_AT = 0.0
_CACHE_KEY = None
_LOCK = threading.Lock()


def load_local_config(path=None):
    """앱 실행 시 개인 연결 파일을 읽습니다. 명시적 환경 변수는 우선합니다."""
    from pathlib import Path
    if "SISUN_CASE_SERVER" in os.environ:
        return
    path = Path(path) if path else Path(__file__).resolve().parents[1] / ".sisun/shared-cases.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    server = str(data.get("server") or "").rstrip("/")
    token = str(data.get("token") or "")
    if not server.startswith(("http://", "https://")) or not token:
        raise ValueError("공용 사건 연결 파일의 주소와 접속키를 확인하세요")
    os.environ["SISUN_CASE_SERVER"] = server
    os.environ["SISUN_CASE_TOKEN"] = token


def enabled():
    return bool(os.environ.get("SISUN_CASE_SERVER", "").strip())


def call(method, *args):
    global _CACHE, _CACHE_AT
    base = os.environ.get("SISUN_CASE_SERVER", "").rstrip("/")
    token = os.environ.get("SISUN_CASE_TOKEN", "")
    if not base.startswith(("http://", "https://")) or not token:
        raise ValueError("공용 사건 서버 주소와 SISUN_CASE_TOKEN을 확인하세요")
    request = urllib.request.Request(
        base + "/rpc",
        data=json.dumps({"method": method, "args": args}, ensure_ascii=False).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            result = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise ValueError("공용 사건 서버 연결 실패 · 저장되지 않았습니다") from exc
    if not result.get("ok"):
        raise ValueError(result.get("error") or "공용 사건 서버 요청 실패")
    if method != "snapshot":
        with _LOCK:
            _CACHE = None
            _CACHE_AT = 0.0
    return result.get("result")


def snapshot(force=False):
    global _CACHE, _CACHE_AT, _CACHE_KEY
    key = (os.environ.get("SISUN_CASE_SERVER"), os.environ.get("SISUN_CASE_TOKEN"))
    with _LOCK:
        if (
            not force
            and _CACHE is not None
            and key == _CACHE_KEY
            and time.monotonic() - _CACHE_AT < 0.5
        ):
            return _CACHE
    result = call("snapshot")
    with _LOCK:
        _CACHE, _CACHE_AT, _CACHE_KEY = result, time.monotonic(), key
    return result
