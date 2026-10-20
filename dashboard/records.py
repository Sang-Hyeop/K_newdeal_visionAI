# 역할: 한 번의 갱신 안에서 필요한 JSONL만 재사용하고 대용량 로그를 순차 읽습니다.
"""한 번의 갱신 안에서 필요한 JSONL만 재사용하고 대용량 로그를 순차 읽습니다."""

import json
from contextlib import contextmanager
from contextvars import ContextVar

_snapshot = ContextVar("dashboard_jsonl_snapshot", default=None)


@contextmanager
def jsonl_snapshot(reuse_paths):
    token = _snapshot.set(
        {path.resolve(): None for path in reuse_paths if path is not None}
    )
    try:
        yield
    finally:
        _snapshot.reset(token)


def read_jsonl(path):
    cache = _snapshot.get()
    key = path.resolve()
    if cache is not None and cache.get(key) is not None:
        return cache[key]
    records = list(iter_jsonl(path))
    if cache is not None and key in cache:
        cache[key] = records
    return records


def iter_jsonl(path):
    """Stream large single-pass logs instead of holding every frame in memory."""
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)
