# 역할: 전달받은 접속 파일로 공용 사건 연결을 확인하고 다음 앱 실행에 적용합니다.
"""python 시선_공용연결.py 접속파일.json / --disconnect는 로컬 기록으로 복귀합니다."""
import argparse
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("connection_file", nargs="?")
    parser.add_argument("--disconnect", action="store_true")
    args = parser.parse_args()
    target = ROOT / ".sisun/shared-cases.json"
    if args.disconnect:
        target.unlink(missing_ok=True)
        print("로컬 기록 모드입니다. 시선 앱을 종료한 뒤 다시 실행하세요.")
        return
    supplied = ROOT / ".sisun/팀원_공용사건_접속.json"
    source = args.connection_file or (str(supplied) if supplied.is_file() else
             input("전달받은 접속 JSON 파일 경로: ").strip().strip('"'))
    data = json.loads(Path(source).expanduser().read_text(encoding="utf-8-sig"))
    base = str(data.get("server") or "").rstrip("/")
    token = str(data.get("token") or "")
    if not base.startswith(("http://", "https://")) or not token:
        raise ValueError("접속 파일의 서버 주소와 접속키를 확인하세요")
    request = urllib.request.Request(base + "/rpc", data=b'{"method":"snapshot","args":[]}',
                                    headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    with urllib.request.urlopen(request, timeout=5) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise ValueError("공용 사건 서버 확인 실패")
    target.parent.mkdir(exist_ok=True)
    temporary = target.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        os.chmod(temporary, 0o600)
        json.dump({"server": base, "token": token}, stream)
    temporary.replace(target)
    print("공용 사건 서버 연결 확인 완료. 시선 앱을 종료한 뒤 평소 방법으로 다시 실행하세요.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print("연결하지 못했습니다:", exc)
        raise SystemExit(1)
