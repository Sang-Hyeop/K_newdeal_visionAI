import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen
from http.server import ThreadingHTTPServer

from backend import Store, handler_for, normalize_event, normalize_observation, parse_jsonl

SAMPLES = Path(__file__).parent / 'samples'


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'test.sqlite3')
        self.counts = self.store.ingest(SAMPLES)
        self.event, self.raw = next(parse_jsonl(SAMPLES / 'forward' / 'events_v1.head.jsonl', 'events'))
        self.observation, _ = next(parse_jsonl(SAMPLES / 'forward' / 'observations_v1.head.jsonl', 'observations'))

    def test_all_samples_and_idempotency(self):
        self.assertGreater(self.counts['events'], 0)
        self.assertGreater(self.counts['observations'], 0)
        self.assertTrue(self.counts['ok'])
        self.assertEqual(self.counts['inserted']['events'], self.counts['events'])
        second = self.store.ingest(SAMPLES)
        self.assertEqual(second['events'], 0)
        self.assertEqual(second['observations'], 0)
        self.assertEqual(second['inserted'], {'events': 0, 'observations': 0})
        self.assertGreater(second['duplicates']['events'], 0)
        self.assertEqual(second['conflicts'], {'events': 0, 'observations': 0})
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0], self.counts['events'])
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO events SELECT * FROM events LIMIT 1')

    def test_conflicting_event_id_keeps_first(self):
        source = Path(self.temp.name) / 'conflict'
        source.mkdir()
        first = copy.deepcopy(self.event)
        first['event_id'] = 'conflict-id'
        second = copy.deepcopy(first)
        second['severity'] = 'CRITICAL' if first.get('severity') != 'CRITICAL' else 'WARNING'
        second['evidence'] = dict(first['evidence'])
        second['evidence']['reason'] = 'different-content'
        (source / 'events_v1.jsonl').write_text(
            json.dumps(first, ensure_ascii=False) + '\n' + json.dumps(second, ensure_ascii=False) + '\n',
            encoding='utf-8')
        (source / 'observations_v1.jsonl').write_text(json.dumps(self.observation) + '\n', encoding='utf-8')
        result = self.store.ingest(source)
        self.assertEqual(result['inserted']['events'], 1)
        self.assertEqual(result['conflicts']['events'], 1)
        self.assertEqual(result['conflict_ids']['events'], ['conflict-id'])
        detail = self.store.detail('conflict-id')
        self.assertEqual(detail['severity'], first.get('severity'))
        self.assertEqual(detail['evidence'].get('reason'), first['evidence'].get('reason'))

    def test_whitespace_only_event_duplicate(self):
        source = Path(self.temp.name) / 'space'
        source.mkdir()
        event = copy.deepcopy(self.event)
        event['event_id'] = 'whitespace-duplicate-id'
        compact = json.dumps(event, ensure_ascii=False, separators=(',', ':'))
        spaced = json.dumps(event, ensure_ascii=False, indent=2).replace('\n', ' ')
        (source / 'events_v1.jsonl').write_text(compact + '\n' + spaced + '\n', encoding='utf-8')
        (source / 'observations_v1.jsonl').write_text(json.dumps(self.observation) + '\n', encoding='utf-8')
        result = self.store.ingest(source)
        self.assertEqual(result['inserted']['events'], 1)
        self.assertEqual(result['duplicates']['events'], 1)
        self.assertEqual(result['conflicts']['events'], 0)

    def test_sort_pagination_and_time_bounds(self):
        page = self.store.events({'limit': 2, 'offset': 0})
        self.assertEqual(page['count'], 2)
        self.assertGreaterEqual(page['total'], page['count'])
        timestamps = [item['timestamp_seconds'] for item in page['events']]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        if timestamps[0] == timestamps[-1]:
            ids = [item['event_id'] for item in page['events']]
            self.assertEqual(ids, sorted(ids))
        edge = page['events'][0]['timestamp_seconds']
        bounded = self.store.events({
            'start_seconds': str(edge), 'end_seconds': str(edge), 'limit': 500})
        self.assertTrue(bounded['events'])
        for item in bounded['events']:
            self.assertEqual(item['timestamp_seconds'], edge)
        self.assertEqual(bounded['total'], bounded['count'])

    def test_unconfirmed_null_and_original_evidence(self):
        event = copy.deepcopy(self.event)
        event.update(event_id='unconfirmed-test', severity='CRITICAL', observation_status='unconfirmed')
        event['evidence']['distance_meters'] = 4.5
        source = Path(self.temp.name) / 'input'
        source.mkdir()
        raw = json.dumps(event, indent=None)
        (source / 'events_v1.jsonl').write_text(raw + '\n', encoding='utf-8')
        (source / 'observations_v1.jsonl').write_text(json.dumps(self.observation) + '\n', encoding='utf-8')
        self.store.ingest(source)
        result = self.store.detail('unconfirmed-test')
        self.assertIsNone(result['severity'])
        self.assertIsNone(result['evidence']['distance_meters'])
        self.assertIsNone(result['distance_meters'])
        self.assertEqual(result['source_raw_json'], raw)
        self.assertEqual(json.loads(result['evidence_raw_json']), event['evidence'])
        with self.store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE events SET severity='SAFE' WHERE event_id='unconfirmed-test'")

    def test_empty_observation_never_safe(self):
        item = copy.deepcopy(self.observation)
        item['events'] = []
        item['feature_status'].update(display_state='SAFE', severity='SAFE', unknown_event_count=0)
        result = normalize_observation(item)
        self.assertEqual(result['feature_status']['display_state'], 'UNKNOWN')
        self.assertIsNone(result['feature_status']['severity'])
        self.assertEqual(result['global_safety_status'], 'not_evaluated')

    def test_critical_not_erased_by_safe_and_unknown(self):
        item = copy.deepcopy(self.observation)
        critical = copy.deepcopy(self.event)
        critical.update(event_type='zone_access', severity='CRITICAL', observation_status='confirmed')
        safe = copy.deepcopy(critical)
        safe.update(event_type='zone_dwell', severity='SAFE')
        unknown = copy.deepcopy(safe)
        unknown.update(observation_status='unconfirmed')
        item['events'] = [critical, safe, unknown]
        item['feature_status']['display_state'] = 'SAFE'
        self.assertEqual(normalize_observation(item)['feature_status']['display_state'], 'CRITICAL')
        critical['severity'] = 'WARNING'
        self.assertEqual(normalize_observation(item)['feature_status']['display_state'], 'WARNING')

    def test_ppe_review_evidence_preserved(self):
        event = copy.deepcopy(self.event)
        event.update(event_type='ppe', severity='WARNING', observation_status='confirmed')
        event['evidence'].update(classification_status='unconfirmed', vehicle_overlap_review_required=True)
        result = normalize_event(event)
        self.assertEqual(result['severity'], 'WARNING')
        self.assertTrue(result['evidence']['vehicle_overlap_review_required'])
        self.assertEqual(result['evidence']['classification_status'], 'unconfirmed')

    def test_malformed_line_rolls_back_import(self):
        source = Path(self.temp.name) / 'bad'
        source.mkdir()
        event = copy.deepcopy(self.event)
        event['event_id'] = 'rollback-test'
        (source / 'events_v1.jsonl').write_text(json.dumps(event) + '\n{bad\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, r':2: error_type=invalid_json; field=record;'):
            self.store.ingest(source)
        self.assertIsNone(self.store.detail('rollback-test'))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events WHERE event_id=?',
                                        ('rollback-test',)).fetchone()[0], 0)

    def test_latest_per_camera_feature_video(self):
        expected = {}
        for path in SAMPLES.rglob('observations_v1.head.jsonl'):
            for item, _ in parse_jsonl(path, 'observations'):
                key = item['camera_id'], item['feature'], item['video']
                rank = item['timestamp_seconds'], item.get('frame_index', 0)
                expected[key] = max(expected.get(key, (-1, -1)), rank)
        actual = self.store.latest({})
        self.assertEqual(actual['count'], len(expected))
        for item in actual['feature_status']:
            key = item['camera_id'], item['feature'], item['video']
            self.assertEqual((item['timestamp_seconds'], item.get('frame_index', 0)), expected[key])

    def test_http_api_filters_detail_latest_errors(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(self.store))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join()
        self.addCleanup(cleanup)
        base = f'http://127.0.0.1:{server.server_port}'
        def get(path):
            with urlopen(base + path) as response:
                return json.load(response)
        listing = get('/events?limit=1')
        self.assertEqual(listing['count'], 1)
        self.assertEqual(listing['limit'], 1)
        self.assertGreaterEqual(listing['total'], 1)
        event = get('/events?severity=null')['events'][0]
        self.assertIsNone(event['severity'])
        encoded = quote(event['event_id'], safe='')
        detail = get('/events/' + encoded)
        self.assertEqual(detail['event_id'], event['event_id'])
        self.assertIn('evidence_raw_json', detail)
        self.assertIn('source_raw_json', detail)
        filtered = get('/events?event_type=proximity&camera_id=forward-proximity&video=1_forklift_forward.mp4&start_seconds=0&end_seconds=1')
        self.assertTrue(filtered['events'])
        for item in filtered['events']:
            self.assertEqual(item['camera_id'], 'forward-proximity')
            self.assertLessEqual(item['timestamp_seconds'], 1)
        video_name = event['video']
        by_video = get('/events?video=' + quote(video_name))
        self.assertTrue(by_video['events'])
        for item in by_video['events']:
            self.assertEqual(item['video'], video_name)
        self.assertGreater(get('/feature-status?feature=ppe')['count'], 0)
        self.assertEqual(get('/feature-status?feature=ppe'), get('/feature-status/latest?feature=ppe'))
        for path, code in [('/events/missing', 404), ('/events?limit=0', 400),
                           ('/events?start_seconds=nan', 400), ('/events?start_seconds=2&end_seconds=1', 400),
                           ('/events?severity=BAD', 400), ('/events?limit=1&limit=2', 400),
                           ('/events?offset=-1', 400)]:
            with self.assertRaises(HTTPError) as raised:
                get(path)
            self.assertEqual(raised.exception.code, code)


if __name__ == '__main__':
    unittest.main()
