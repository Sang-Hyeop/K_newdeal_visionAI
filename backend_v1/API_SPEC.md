# Dashboard API v1

Base URL: `http://127.0.0.1:8010`. All responses are UTF-8 JSON.
Start with `python backend.py --port 8010`. No additional packages required.
The server listens on localhost by default. There is no authentication and no
CORS configuration; treat it as a local integration API only.

## GET /events

| Parameter | Type | Meaning |
| --- | --- | --- |
| limit | integer 1..500 | default 50, latest N |
| offset | nonnegative integer | default 0, pagination |
| event_type | string | proximity / zone_access / zone_dwell / ppe / status |
| severity | string | SAFE / WARNING / CRITICAL / null (SQL NULL) |
| camera_id | string | exact match |
| video | string | exact match |
| start_seconds | nonnegative finite number | inclusive video-relative start |
| end_seconds | nonnegative finite number | inclusive video-relative end |

Response: `{"events": [...], "total": 40, "count": 1, "limit": 1, "offset": 0}`.
`total` is the filtered count before pagination. Sort: timestamp_seconds DESC,
event_id ASC. No matches returns HTTP 200 with an empty events array.
Invalid parameters return HTTP 400 with `{"error": "..."}`.

## GET /events/{event_id}

Returns the complete event, including schema_version, event_id, camera_id,
video, source_sha256, timestamp_seconds, event_type, severity,
observation_status, track_ids, evidence, model_version, config_version, scope.
Additional audit strings: evidence_raw_json and source_raw_json.
Missing event: HTTP 404. Query parameters are not accepted.

## GET /feature-status

Optional exact-match filters: camera_id, feature, video.
Response: `{"count": 5, "feature_status": [...], "global_safety_status": "not_evaluated"}`.
Each array item is a latest observation, with camera_id, feature, video,
timestamp_seconds, events and nested feature_status. Read the banner from
`item.feature_status.display_state`: SAFE / WARNING / CRITICAL / UNKNOWN.
Never interpret the response as a declaration of site-wide safety.
No matching observations returns an empty array, not a synthesized SAFE.

Video-relative clocks are separate timelines. Latest is selected per
camera/feature/video, so pass the active video when a camera has multiple clips.
`/feature-status/latest` remains a compatibility alias.

## Evidence and ROI

Evidence is passed as a JSON object, without flattening or dropping ROI fields.
All display distance_meters values are null. Exact input evidence and source
line are preserved separately for auditing. Invalid source distances are
normalized only in display payloads.

The dashboard draws and fills ROI polygons itself using
`evidence.roi_polygon_normalized`, or separately supplied
`summary.json.camera_config`. For scenario 7 use monitor_floor_normalized and
safe_polygons_normalized when present. Do not invent polygons if samples lack
them. This backend does not ingest summary.json; provide its camera_config as
dashboard configuration when that is the polygon source.
Use supplied roi_alpha_safe / roi_alpha_alert; defaults are approximately
0.15 / 0.2. SAFE green, WARNING orange, CRITICAL red. Proximity has no fixed ROI.

The team's ROI wording document is included as `roi-wording-2026-10-07.md`.
Korean UI labels for codes (`event_type`, `severity`, `reason`, video titles)
are in `../docs/dashboard-ko-labels.md` with helpers in `dashboard_labels.py`.
Keep API field values in English; map only for display. Attach this spec, the
ROI wording doc, and the Korean label document when handing work to the
dashboard AI.

## Actual HTTP examples

`responses/proximity.json`, `responses/zone.json`, `responses/ppe.json` are
sample-based GET /events responses, one event each.
`responses/event_detail.json` is an actual detail response.
`responses/feature_status.json` is an actual latest-banner response.
Generate again with `python export_responses.py` (temporary local server).
Examples represent observed sample states, not fabricated warning cases.
