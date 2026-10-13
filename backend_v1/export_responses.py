"""Capture actual HTTP responses for the dashboard handoff."""
import json
from pathlib import Path
import threading
from urllib.request import urlopen
from http.server import ThreadingHTTPServer

from backend import Store, handler_for


def main():
    root = Path(__file__).parent
    store = Store(root / 'data' / 'backend.sqlite3')
    counts = store.ingest(root / 'samples')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    destination = root / 'responses'
    destination.mkdir(exist_ok=True)
    paths = {
        'proximity': '/events?event_type=proximity&limit=1',
        'zone': '/events?event_type=zone_access&limit=1',
        'ppe': '/events?event_type=ppe&limit=1',
        'feature_status': '/feature-status',
    }
    try:
        for name, path in paths.items():
            with urlopen(f'http://127.0.0.1:{server.server_port}' + path) as response:
                value = json.load(response)
            if name != 'feature_status' and not value['events']:
                raise ValueError(f'No sample events for {name}')
            (destination / f'{name}.json').write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            if name == 'proximity':
                event_id = value['events'][0]['event_id']
                with urlopen(f'http://127.0.0.1:{server.server_port}/events/{event_id}') as response:
                    detail = json.load(response)
                (destination / 'event_detail.json').write_text(
                    json.dumps(detail, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'inserted': counts, 'responses': len(list(destination.glob('*.json')))}))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    main()
