# Dashboard Backend v1

Python 3.11+ standard library only. No YOLO, model weights, training, or video inference.
Source contract: team-integration-pack-2026-10-07.md and its five sample directories.

## Run

From this directory:

```powershell
python backend.py --import-only
python -m unittest -v test_backend
python backend.py --port 8010
```

The default input is `samples/`. SQLite is created at `data/backend.sqlite3`.
Override inputs with `--samples PATH --db PATH`. Both `*_v1.jsonl` and the
team sample filenames `*_v1.head.jsonl` are accepted recursively.
Reimporting the same samples inserts no duplicates. A malformed import rolls
back the whole transaction and reports the filename and line number.

## Three GET APIs

| Endpoint | Result | Query parameters |
| --- | --- | --- |
| `/events` | events, total, count, limit, offset | event_type, severity, camera_id, video, start_seconds, end_seconds, limit, offset |
| `/events/{event_id}` | full event and original JSON evidence | none |
| `/feature-status` | latest observation for each camera/feature/video stream | camera_id, feature, video |

`severity=null` selects SQL NULL. Limit defaults to 50 (1..500).
Times are inclusive video-relative seconds, not wall-clock dates. Event order
is timestamp descending with event_id as a stable tie-breaker. Different videos
do not have comparable playback clocks, so latest status is separated by video;
the dashboard should select its active video. Missing event returns 404;
invalid query returns 400. No observations returns an empty list, not SAFE.

```powershell
Invoke-RestMethod 'http://127.0.0.1:8010/events?severity=null&limit=5'
Invoke-RestMethod 'http://127.0.0.1:8010/feature-status?feature=ppe'
```

## Storage and safety rules

The SQL schema is in `backend.py` as `SCHEMA`.
`events.event_id` is a primary key (UNIQUE), severity is nullable, and a CHECK
constraint prevents non-null severity on unconfirmed events.
`evidence` is JSON text containing the exact original JSON value; `raw_json`
preserves the complete source line, including formatting. `payload` holds the
normalized dashboard representation. Detail returns `evidence_raw_json` and
`source_raw_json` for auditing. Original evidence may contain invalid source
values; display the normalized `evidence`, not the raw audit fields.

Unconfirmed events always have null severity. All normalized distance_meters
fields are null. Empty observations never produce SAFE. CRITICAL and WARNING
remain visible when mixed with unknown subjects. Otherwise mixed unconfirmed
subjects prevent SAFE. Each feature has its own stream. global_safety_status
is always not_evaluated. PPE classification_status=unconfirmed does not erase
a confirmed WARNING review candidate; its evidence is preserved.

Observations are not inserted into the transition-event table. Their embedded
events remain available in the feature-status response. This avoids treating
every frame as a state transition. Conflicting duplicate event IDs retain the
first event. The API binds localhost by default and is a local integration
server; it does not implement authentication or cross-origin browser access.
