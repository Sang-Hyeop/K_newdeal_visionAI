"""단일 Python 실행 파일의 환경 선택과 기존 앱 연결을 검증합니다."""
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('sisun_launch', Path(__file__).resolve().parents[1] / '시선_실행.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_korean_progress_with_western_windows_console(self):
        output = io.BytesIO()
        stream = io.TextIOWrapper(output, encoding='cp1252')
        with patch.object(launcher.sys, 'stdout', stream):
            launcher.announce('환경 검사', flush=True)
        self.assertEqual(output.getvalue().decode('utf-8').strip(), '환경 검사')

    def test_probe_timeout_is_not_success(self):
        with patch.object(launcher.subprocess, 'run', side_effect=subprocess.TimeoutExpired('python', 90)):
            self.assertFalse(launcher.probe(Path('python.exe')))

    def test_capture_failure_is_not_environment(self):
        with patch.object(launcher.subprocess, 'run', side_effect=OSError):
            self.assertEqual(launcher.capture(['missing']), '')

    def test_reuse_prepares_once_then_uses_same_interpreter(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'requirements-runtime.txt').write_text('runtime')
            (root / 'requirements-windows.txt').write_text('windows')
            python = root / 'safety/python.exe'
            with patch.object(launcher, 'ROOT', root), patch.object(launcher, 'STATE', root), patch.object(launcher, 'candidates', return_value=[python]), patch.object(launcher, 'probe', return_value=True), patch.object(launcher, 'run') as run:
                self.assertEqual(launcher.prepare(), python)
                run.assert_called_once_with([python, launcher.SETUP, '--reuse'])
                self.assertEqual(launcher.prepare(), python)
                self.assertEqual(run.call_count, 1)

    def test_failed_setup_does_not_mark_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('requirements-runtime.txt', 'requirements-windows.txt'):
                (root / name).write_text('')
            with patch.object(launcher, 'ROOT', root), patch.object(launcher, 'STATE', root), patch.object(launcher, 'candidates', return_value=[root / 'python.exe']), patch.object(launcher, 'probe', return_value=True), patch.object(launcher, 'run', side_effect=subprocess.CalledProcessError(1, 'setup')):
                with self.assertRaises(subprocess.CalledProcessError):
                    launcher.prepare()
                self.assertFalse((root / 'python-launch-ready.json').exists())
