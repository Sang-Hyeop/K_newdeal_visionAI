"""Sample-only v1 ingestion, SQLite storage and dashboard HTTP API."""
import argparse
import copy
import hashlib
import json
import math
import sqlite3
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
 event_id TEXT PRIMARY KEY,
 camera_id TEXT NOT NULL, video TEXT NOT NULL, event_type TEXT NOT NULL,
 timestamp_seconds REAL NOT NULL,
 severity TEXT CHECK(severity IS NULL OR severity IN ('SAFE','WARNING','CRITICAL')),
 observation_status TEXT NOT NULL,
 evidence JSON NOT NULL CHECK(json_valid(evidence)),
 raw_json TEXT NOT NULL CHECK(json_valid(raw_json)),
 payload JSON NOT NULL CHECK(json_valid(payload)),
 CHECK(observation_status != 'unconfirmed' OR severity IS NULL)
);
CREATE INDEX IF NOT EXISTS event_lookup ON events(camera_id,event_type,timestamp_seconds);
CREATE TABLE IF NOT EXISTS observations (
 observation_id TEXT PRIMARY KEY,
 camera_id TEXT NOT NULL, feature TEXT NOT NULL, video TEXT NOT NULL,
 timestamp_seconds REAL NOT NULL,
 frame_index INTEGER NOT NULL,
 raw_json TEXT NOT NULL CHECK(json_valid(raw_json)),
 payload JSON NOT NULL CHECK(json_valid(payload))
);
CREATE INDEX IF NOT EXISTS observation_lookup
 ON observations(camera_id,feature,video,timestamp_seconds DESC,frame_index DESC);
"""


def dumps(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def evidence_source(raw):
    """Extract the original top-level JSON value with the standard decoder."""
    decoder = json.JSONDecoder()
    index = raw.index('{') + 1
    while True:
        while raw[index].isspace() or raw[index] == ',':
            index += 1
        if raw[index] == '}':
            return '{}'
        key, index = decoder.raw_decode(raw, index)
        while raw[index].isspace() or raw[index] == ':':
            index += 1
        start = index
        _, index = decoder.raw_decode(raw, index)
        if key == 'evidence':
            return raw[start:index]


def validate_base(record):
    if not isinstance(record, dict) or record.get('schema_version') != '1.0':
        raise ValueError('Expected a schema_version=1.0 object')
    for key in ('camera_id', 'video', 'observation_status'):
        if not isinstance(record.get(key), str) or not record[key]:
            raise ValueError(f'Missing or invalid {key}')
    timestamp = record.get('timestamp_seconds')
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
        raise ValueError('Invalid timestamp_seconds')
    if not math.isfinite(timestamp) or timestamp < 0:
        raise ValueError('timestamp_seconds must be finite and nonnegative')


def null_distances(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'distance_meters':
                value[key] = None
            else:
                null_distances(item)
    elif isinstance(value, list):
        for item in value:
            null_distances(item)


def normalize_event(record):
    validate_base(record)
    for key in ('event_id', 'event_type'):
        if not isinstance(record.get(key), str) or not record[key]:
            raise ValueError(f'Missing or invalid {key}')
    if record['event_type'] not in ('proximity', 'zone_access', 'zone_dwell', 'ppe', 'status'):
        raise ValueError('Invalid event_type')
    if not isinstance(record.get('evidence'), dict):
        raise ValueError('evidence must be an object')
    result = copy.deepcopy(record)
    if result['observation_status'] == 'unconfirmed':
        result['severity'] = None
    if result.get('severity') not in (None, 'SAFE', 'WARNING', 'CRITICAL'):
        raise ValueError('Invalid severity')
    null_distances(result)
    result['distance_meters'] = None
    return result


def normalize_observation(record):
    validate_base(record)
    if not isinstance(record.get('feature'), str) or not record['feature']:
        raise ValueError('Missing feature')
    if not isinstance(record.get('feature_status'), dict):
        raise ValueError('Missing feature_status')
    if not isinstance(record.get('events'), list):
        raise ValueError('events must be an array')
    frame = record.get('frame_index', 0)
    if isinstance(frame, bool) or not isinstance(frame, int) or frame < 0:
        raise ValueError('Invalid frame_index')
    result = copy.deepcopy(record)
    result['events'] = [normalize_event(event) for event in record['events']]
    status = result['feature_status']
    severities = [event.get('severity') for event in result['events']]
    # Warnings remain visible even when another subject is unconfirmed.
    candidates = severities + [status.get('severity'), status.get('display_state')]
    if 'CRITICAL' in candidates:
        display = 'CRITICAL'
    elif 'WARNING' in candidates:
        display = 'WARNING'
    elif (not severities or None in severities
          or record['observation_status'] != 'confirmed'
          or status.get('unknown_event_count', 0) > 0
          or status.get('display_state') == 'UNKNOWN'):
        display = 'UNKNOWN'
    elif all(value == 'SAFE' for value in severities):
        display = 'SAFE'
    else:
        display = 'UNKNOWN'
    status['display_state'] = display
    status['severity'] = None if display == 'UNKNOWN' else display
    if record['observation_status'] == 'unconfirmed':
        status['severity'] = None
    status['global_safety_status'] = 'not_evaluated'
    result['global_safety_status'] = 'not_evaluated'
    null_distances(result)
    result['distance_meters'] = None
    return result


def parse_jsonl(path, kind):
    normalize = {'events': normalize_event, 'observations': normalize_observation}[kind]
    with Path(path).open(encoding='utf-8-sig') as source:
        for number, line in enumerate(source, 1):
            raw = line.rstrip('\r\n')
            if not raw.strip():
                continue
            try:
                record = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
                yield normalize(record), raw
            except (ValueError, TypeError, KeyError) as error:
                raise ValueError(f'{path}:{number}: {error}') from error


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def ingest(self, root):
        counts = {'events': 0, 'observations': 0}
        with self.connect() as db:
            for kind in counts:
                paths = sorted(set(Path(root).rglob(f'{kind}_v1.jsonl')) |
                               set(Path(root).rglob(f'{kind}_v1.head.jsonl')))
                if not paths:
                    raise ValueError(f'No {kind}_v1 JSONL files in {root}')
                for path in paths:
                    for record, raw in parse_jsonl(path, kind):
                        if kind == 'events':
                            cursor = db.execute(
                                'INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(event_id) DO NOTHING',
                                (record['event_id'], record['camera_id'], record['video'],
                                 record['event_type'], record['timestamp_seconds'], record.get('severity'),
                                 record['observation_status'], evidence_source(raw), raw, dumps(record)))
                        else:
                            identity = hashlib.sha256(raw.encode('utf-8')).hexdigest()
                            cursor = db.execute(
                                'INSERT INTO observations VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(observation_id) DO NOTHING',
                                (identity, record['camera_id'], record['feature'], record['video'],
                                 record['timestamp_seconds'], record.get('frame_index', 0), raw, dumps(record)))
                        counts[kind] += cursor.rowcount
        return counts

    def events(self, filters):
        clauses, values = [], []
        allowed = {'event_type', 'severity', 'camera_id', 'video', 'start_seconds', 'end_seconds', 'limit', 'offset'}
        if set(filters) - allowed:
            raise ValueError('Unknown filter')
        for key in ('event_type', 'severity', 'camera_id', 'video'):
            if key in filters:
                if key == 'severity' and filters[key] == 'null':
                    clauses.append('severity IS NULL')
                else:
                    if key == 'severity' and filters[key] not in ('SAFE', 'WARNING', 'CRITICAL'):
                        raise ValueError('Invalid severity')
                    clauses.append(f'{key} = ?')
                    values.append(filters[key])
        for key, operator in (('start_seconds', '>='), ('end_seconds', '<=')):
            if key in filters:
                number = float(filters[key])
                if not math.isfinite(number) or number < 0:
                    raise ValueError('Invalid time filter')
                clauses.append(f'timestamp_seconds {operator} ?')
                values.append(number)
        if float(filters.get('start_seconds', 0)) > float(filters.get('end_seconds', 'inf')):
            raise ValueError('start_seconds exceeds end_seconds')
        limit, offset = int(filters.get('limit', 50)), int(filters.get('offset', 0))
        if not 1 <= limit <= 500 or offset < 0:
            raise ValueError('limit must be 1..500; offset must be nonnegative')
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        with self.connect() as db:
            total = db.execute('SELECT count(*) FROM events' + where, values).fetchone()[0]
            rows = db.execute('SELECT payload FROM events' + where +
                              ' ORDER BY timestamp_seconds DESC,event_id ASC LIMIT ? OFFSET ?',
                              values + [limit, offset]).fetchall()
        return {'events': [json.loads(row[0]) for row in rows], 'total': total,
                'count': len(rows), 'limit': limit, 'offset': offset}

    def detail(self, event_id):
        with self.connect() as db:
            row = db.execute('SELECT payload,evidence,raw_json FROM events WHERE event_id=?', (event_id,)).fetchone()
        if row is None:
            return None
        result = json.loads(row['payload'])
        result['evidence_raw_json'] = row['evidence']
        result['source_raw_json'] = row['raw_json']
        return result

    def latest(self, filters):
        if set(filters) - {'camera_id', 'feature', 'video'}:
            raise ValueError('Unknown filter')
        clauses = [f'{key}=?' for key in filters]
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        # Video is part of the stream key: playback clocks cannot order different videos.
        with self.connect() as db:
            rows = db.execute('SELECT payload FROM (SELECT *, ROW_NUMBER() OVER ('
                              'PARTITION BY camera_id,feature,video ORDER BY timestamp_seconds DESC,'
                              'frame_index DESC,rowid DESC) AS rank FROM observations' + where +
                              ') WHERE rank=1 ORDER BY camera_id,feature,video', list(filters.values())).fetchall()
        result = [json.loads(row[0]) for row in rows]
        return {'count': len(result), 'feature_status': result, 'global_safety_status': 'not_evaluated'}


def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            try:
                query = parse_qs(parsed.query, keep_blank_values=True)
                if any(len(value) != 1 for value in query.values()):
                    raise ValueError('Repeated query parameters')
                filters = {key: value[0] for key, value in query.items()}
                status = 200
                if parsed.path == '/events':
                    result = store.events(filters)
                elif parsed.path in ('/feature-status', '/feature-status/latest'):
                    result = store.latest(filters)
                elif parsed.path.startswith('/events/'):
                    if filters:
                        raise ValueError('Detail does not accept filters')
                    result = store.detail(unquote(parsed.path[len('/events/'):]))
                    if result is None:
                        status, result = 404, {'error': 'Event not found'}
                else:
                    status, result = 404, {'error': 'Route not found'}
            except (ValueError, TypeError) as error:
                status, result = 400, {'error': str(error)}
            payload = dumps(result).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=Path, default=Path(__file__).parent / 'samples')
    parser.add_argument('--db', type=Path, default=Path(__file__).parent / 'data' / 'backend.sqlite3')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8010)
    parser.add_argument('--import-only', action='store_true')
    args = parser.parse_args()
    store = Store(args.db)
    print(dumps(store.ingest(args.samples)))
    if not args.import_only:
        server = ThreadingHTTPServer((args.host, args.port), handler_for(store))
        print(f'API: http://{args.host}:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
