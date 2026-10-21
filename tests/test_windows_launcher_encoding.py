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


# Windows 실제 엔진으로 전체 문법과 Python 호출 경계를 검증합니다.
import os
import subprocess
import sys
import tempfile
import time


@unittest.skipUnless(os.name == 'nt', 'Windows Script Host가 필요한 통합 검사')
class WindowsLauncherExecutionTests(unittest.TestCase):
    def test_both_vbs_files_compile_with_windows_engine(self):
        with tempfile.TemporaryDirectory(prefix='시선 compile ') as folder:
            for name in ('Windows용_시선설치.vbs', '시선.vbs'):
                with self.subTest(name=name):
                    source = (ROOT / name).read_text(encoding='utf-16')
                    # 실행 전에 종료하되 전체 파일은 엔진이 컴파일하도록 합니다.
                    source = source.replace('Option Explicit', 'Option Explicit\r\nWScript.Quit 0', 1)
                    script = Path(folder) / name
                    script.write_text(source, encoding='utf-16')
                    result = subprocess.run(
                        ['cscript.exe', '//Nologo', '//B', '//T:15', str(script)],
                        capture_output=True, timeout=20,
                    )
                    self.assertEqual(result.returncode, 0, repr(result.stderr))

    def test_unmodified_launcher_reaches_python_in_unicode_folder(self):
        with tempfile.TemporaryDirectory(prefix='시선 [test] project ') as folder:
            root = Path(folder)
            script = root / '시선.vbs'
            script.write_bytes((ROOT / '시선.vbs').read_bytes())
            marker = root / 'python-started.txt'
            subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(root / '.sisun/venv')], check=True)
            (root / '.sisun/venv/sisun-install.json').write_text('{}')
            (root / 'dashboard_desktop.py').write_text(
                "from pathlib import Path\n"
                "Path(__file__).with_name('python-started.txt').write_text('started')\n",
                encoding='utf-8',
            )
            pythonw = Path(sys.executable).with_name('pythonw.exe')
            self.assertTrue(pythonw.is_file(), str(pythonw))
            empty_profile = root / 'empty-profile'
            empty_profile.mkdir()
            env = dict(os.environ, USERPROFILE=str(empty_profile),
                       LOCALAPPDATA=str(empty_profile),
                       PATH=str(pythonw.parent) + os.pathsep + os.environ.get('PATH', ''))
            cscript = str(Path(os.environ['SystemRoot']) / 'System32' / 'cscript.exe')
            result = subprocess.run(
                [cscript, '//Nologo', '//B', '//T:15', str(script)],
                env=env, capture_output=True, timeout=20,
            )
            self.assertEqual(result.returncode, 0, repr(result.stderr))
            deadline = time.monotonic() + 10
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertTrue(marker.exists(), 'VBS 실행 후 Python 진입 기록이 생성되지 않았습니다.')
            self.assertEqual(marker.read_text(), 'started')
