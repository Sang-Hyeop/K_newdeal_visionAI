"""Windows 설치·실행 파일의 한글 경로와 BOM 보존을 검증합니다."""
import codecs
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WindowsLauncherEncodingTests(unittest.TestCase):
    def test_powershell_has_explicit_unicode_encoding(self):
        data = (ROOT / 'dashboard/packaging/windows/make_shortcut.ps1').read_bytes()
        self.assertTrue(data.startswith(codecs.BOM_UTF8))
        source = data.decode('utf-8-sig')
        self.assertIn('시선.vbs', source)
        self.assertIn('시선.lnk', source)
        self.assertNotIn('\ufffd', source)

    def test_wsh_launchers_use_unicode_bom(self):
        for name in ('Windows용_시선설치.vbs', '시선.vbs'):
            with self.subTest(name=name):
                data = (ROOT / name).read_bytes()
                self.assertTrue(data.startswith(codecs.BOM_UTF16_LE))
                source = data.decode('utf-16')
                self.assertIn('Option Explicit', source)
                self.assertIn('dashboard_desktop.py', source)
                self.assertNotIn('\ufffd', source)
