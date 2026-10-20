# 역할: 백엔드 전달 대상 이벤트·관측 로그의 목록과 수량을 읽기 전용으로 점검합니다.
"""백엔드 전달 대상 이벤트·관측 로그의 목록과 수량을 읽기 전용으로 점검합니다."""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def summarize(path: Path, kind: str) -> dict:
    n = 0
    cams = Counter()
    videos = Counter()
    types = Counter()
    timestamps = []
    with path.open(encoding="utf-8-sig") as source:
        for line in source:
            raw = line.rstrip("\r\n")
            if not raw.strip():
                continue
            record = json.loads(raw)
            n += 1
            cams[record.get("camera_id")] += 1
            videos[record.get("video")] += 1
            key = "event_type" if kind == "events" else "feature"
            types[record.get(key)] += 1
            value = record.get("timestamp_seconds")
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            ):
                timestamps.append(float(value))
    relative = path.relative_to(ROOT).as_posix()
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    return {
        "path": relative,
        "kind": kind,
        "records": n,
        "camera_id": dict(cams),
        "video": dict(videos),
        "types": dict(types),
        "timestamp_seconds_min": min(timestamps) if timestamps else None,
        "timestamp_seconds_max": max(timestamps) if timestamps else None,
        "sha256": digest,
        "bytes": path.stat().st_size,
    }


def main() -> int:
    rows = []
    for root_name in ("outputs/events", "backend_v1/samples"):
        root = ROOT / root_name
        if not root.is_dir():
            print("MISSING", root_name)
            continue
        for kind in ("events", "observations"):
            paths = sorted(
                set(root.rglob(f"{kind}_v1.jsonl"))
                | set(root.rglob(f"{kind}_v1.head.jsonl"))
            )
            for path in paths:
                rows.append(summarize(path, kind))
    out = ROOT / "outputs" / "backend" / "cursor_log_inventory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    presentation = [row for row in rows if row["path"].startswith("outputs/events/")]
    print("inventory_files", len(rows))
    print("presentation_files", len(presentation))
    print(
        "presentation_events",
        sum(row["records"] for row in presentation if row["kind"] == "events"),
    )
    print(
        "presentation_observations",
        sum(row["records"] for row in presentation if row["kind"] == "observations"),
    )
    print("wrote", out.relative_to(ROOT).as_posix())
    for row in rows:
        print(f"{row['kind']:13} {row['records']:6}  {row['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
