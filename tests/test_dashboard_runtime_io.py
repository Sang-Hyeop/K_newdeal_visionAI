"""Refresh memory/I/O and concurrent conversion regressions without real ffmpeg."""
import json
import os
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from dashboard import media
from dashboard.records import iter_jsonl, jsonl_snapshot, read_jsonl


class DashboardIOTests(unittest.TestCase):
    def test_refresh_reuses_only_selected_file_and_releases_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'records.jsonl';path.write_text('{"value":1}\n')
            with jsonl_snapshot([path]):
                first=read_jsonl(path);path.write_text('{"value":2}\n')
                self.assertIs(read_jsonl(path),first)
            self.assertEqual(read_jsonl(path),[{'value':2}])
            with jsonl_snapshot([]):
                first=read_jsonl(path);path.write_text('{"value":3}\n')
                self.assertNotEqual(read_jsonl(path),first)

    def test_stream_is_lazy_and_keeps_json_error_visible(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'records.jsonl';path.write_text('{"value":1}\ninvalid\n')
            records=iter_jsonl(path)
            self.assertEqual(next(records),{'value':1})
            with self.assertRaises(json.JSONDecodeError):next(records)

    def test_concurrent_video_requests_share_one_atomic_conversion(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.mp4';source.write_bytes(b'source')
            def convert(args,**kwargs):
                self.assertFalse((Path(folder)/'browser.mp4').exists())
                Path(args[-1]).write_bytes(b'converted')
            with patch.object(media,'LOCAL',folder),patch.object(media,'_ffmpeg',return_value='ffmpeg'),patch.object(media.subprocess,'run',side_effect=convert) as run:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results=list(pool.map(lambda _:media.to_browser_mp4(str(source),'browser.mp4'),range(2)))
            self.assertEqual(run.call_count,1)
            self.assertEqual(results,[str(Path(folder)/'browser.mp4')]*2)
            self.assertEqual(list(Path(folder).glob('.convert-*')),[])

    def test_failed_conversion_preserves_previous_cache_and_returns_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.mp4';source.write_bytes(b'source')
            dest=Path(folder)/'browser.mp4';dest.write_bytes(b'previous');os.utime(dest,(1,1))
            with patch.object(media,'LOCAL',folder),patch.object(media,'_ffmpeg',return_value='ffmpeg'),patch.object(media.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'ffmpeg')):
                self.assertEqual(media.to_browser_mp4(str(source),'browser.mp4'),str(source))
            self.assertEqual(dest.read_bytes(),b'previous')
            self.assertEqual(list(Path(folder).glob('.convert-*')),[])
