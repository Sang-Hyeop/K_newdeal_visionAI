# 역할: 이 컴퓨터의 공용 사건 서버를 시작하고 최초 실행에 기존 조치 이력을 가져옵니다.
"""접속키는 .sisun/shared-server.json에 보관하며 외부에 자동 공개하지 않습니다."""
import json
import os
from pathlib import Path
import secrets
import sqlite3

ROOT = Path(__file__).resolve().parent


def main():
    os.environ["SISUN_CASE_SERVER"] = ""
    from dashboard.case_server import make_server
    state = ROOT / ".sisun"
    state.mkdir(exist_ok=True)
    secret = state / "shared-server.json"
    if secret.exists():
        token = json.loads(secret.read_text(encoding="utf-8"))["token"]
    else:
        token = secrets.token_urlsafe(32)
        with secret.open("x", encoding="utf-8") as stream:
            os.chmod(secret, 0o600)
            json.dump({"token": token}, stream)
    db = ROOT / "outputs/backend/shared_cases.sqlite3"
    server = make_server("0.0.0.0", 8020, db, token)
    with sqlite3.connect(db) as connection:
        empty = connection.execute("SELECT COUNT(*) FROM journal").fetchone()[0] == 0
    source = ROOT / "dashboard/data/alert_response_log.jsonl"
    if empty and source.is_file():
        server.service.import_log(source)
    print("공용 사건 서버 실행 중: 포트 8020. 종료하려면 Ctrl+C", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
