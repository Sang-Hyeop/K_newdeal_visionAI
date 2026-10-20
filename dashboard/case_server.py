# 역할: 공용 사건 상태를 SQLite에 저장하고 기존 조치 규칙으로 공유합니다.
"""공용 사건 상태를 SQLite에 저장하고 기존 조치 규칙으로 공유합니다."""

import argparse
import hmac
import json
import os
from pathlib import Path
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import alert_response as ar
from . import shared_cases

METHODS = {
    "ensure_case",
    "touch_case_observation",
    "record_observation_day",
    "reopen_case",
    "apply_transition",
}


class Journal:
    def __init__(self, connection):
        self.connection = connection

    def rows(self):
        return [
            json.loads(row[0])
            for row in self.connection.execute(
                "SELECT payload FROM journal ORDER BY seq"
            )
        ]

    def append(self, row):
        self.connection.execute(
            "INSERT INTO journal(payload) VALUES (?)",
            (json.dumps(row, ensure_ascii=False),),
        )


class CaseService:
    def __init__(self, db):
        self.db = str(db)
        Path(self.db).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        with sqlite3.connect(self.db) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS journal (seq INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
            )

    def execute(self, method, args):
        if method not in METHODS | {"snapshot", "observations"}:
            raise ValueError("지원하지 않는 요청")
        # A single writer transaction covers load, validation, append and commit.
        # Independent server processes sharing this DB also serialize via SQLite.
        with self.lock, sqlite3.connect(self.db, timeout=10) as connection:
            connection.execute("BEGIN IMMEDIATE")
            old_store = ar._STORE
            try:
                ar._STORE = Journal(connection)
                ar.reset_response_memory()
                ar.load_logs_into_memory()
                ar.migrate_missing_assignees()
                if method == "observations":
                    result = {}
                    for hop, meta in args[0]:
                        link = str(meta.get("link_key") or "")
                        known = ar.get_state_by_link(link).get("state") or {}
                        if not known:
                            ar.ensure_case(meta)
                        elif hop == "upgrade" and set(
                            meta.get("event_ids") or []
                        ) - set(known.get("event_ids") or []):
                            ar.reopen_case(meta)
                        ar.touch_case_observation(meta)
                        ar.record_observation_day(link)
                        result[link] = ar.get_state_by_link(link).get("state") or {}
                elif method == "snapshot":
                    result = {"rows": ar._STORE.rows()}
                else:
                    if method == "apply_transition":
                        data = args[0]
                        link = ar.resolve_link_key(data)
                        current = ar.get_state_by_link(link or "").get("state") or {}
                        if data.get("request_id") not in ar._SEEN_REQUESTS and str(
                            current.get("status") or "new"
                        ) != str(data.get("prev_status") or "new"):
                            raise ValueError(
                                "다른 작업자가 상태를 변경했습니다. 다시 조회한 뒤 처리하세요"
                            )
                    result = getattr(ar, method)(*args)
                    if method == "apply_transition" and result.get("duplicate"):
                        result["state"] = ar.get_state_by_link(
                            ar.resolve_link_key(args[0]) or ""
                        ).get("state")
                connection.commit()
                return result
            except Exception:
                connection.rollback()
                raise
            finally:
                ar._STORE = old_store
                ar.reset_response_memory()

    def import_log(self, path):
        # Explicit one-time import into an empty DB; never overwrite shared work.
        rows = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict) or not row.get("link_key"):
                    raise ValueError("잘못된 원본 기록")
                rows.append(row)
        with sqlite3.connect(self.db) as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT COUNT(*) FROM journal").fetchone()[0]:
                raise ValueError("비어 있는 DB에만 최초 기록을 가져올 수 있습니다")
            for row in rows:
                Journal(connection).append(row)
        return len(rows)


def make_server(host, port, db, token):
    if not token:
        raise ValueError("SISUN_CASE_TOKEN이 필요합니다")
    if shared_cases.enabled():
        raise ValueError("공용 서버 프로세스에는 SISUN_CASE_SERVER를 설정하지 마세요")
    service = CaseService(db)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.path != "/rpc":
                self.send_error(404)
                return
            auth = self.headers.get("Authorization", "")
            if not hmac.compare_digest(auth, "Bearer " + token):
                self.send_error(401)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 262144:
                    raise ValueError("잘못된 요청 크기")
                payload = json.loads(self.rfile.read(size))
                args = payload.get("args", [])
                if not isinstance(args, list):
                    raise ValueError("잘못된 인수")
                result = service.execute(payload.get("method"), args)
                data = {"ok": True, "result": result}
            except (ValueError, TypeError, KeyError) as exc:
                data = {"ok": False, "error": str(exc)}
            except Exception:
                data = {
                    "ok": False,
                    "error": "공용 저장 실패 · 저장 결과를 다시 조회하세요",
                }
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), Handler)
    server.service = service
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--db", default="outputs/backend/shared_cases.sqlite3")
    parser.add_argument("--import-log")
    parser.add_argument("--import-only", action="store_true")
    args = parser.parse_args()
    server = make_server(
        args.host, args.port, args.db, os.environ.get("SISUN_CASE_TOKEN", "")
    )
    if args.import_log:
        print("Imported rows:", server.service.import_log(args.import_log))
    if args.import_only:
        server.server_close()
        return
    print(f"Case server: http://{args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
