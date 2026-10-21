"""Python 바로가기 진입점이 설치 없이 기존 생성기만 호출하는지 확인합니다."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('shortcut_python', Path(__file__).resolve().parents[1] / '시선_바로가기_만들기.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ShortcutTests(unittest.TestCase):
    def test_uses_existing_generator_without_install(self):
        # pathlib의 WindowsPath 생성을 피하면서 Windows 분기만 검사합니다.
        with patch.object(module, 'os') as windows, patch.object(module.subprocess, 'run') as run:
            windows.name = 'nt'
            windows.environ = {'SystemRoot': 'C:/Windows'}
            self.assertEqual(module.main(), 0)
            command = run.call_args.args[0]
            self.assertEqual(command[-1], str(module.ROOT / 'dashboard/packaging/windows/make_shortcut.ps1'))
            self.assertNotIn('install.ps1', ' '.join(command))
            self.assertTrue(run.call_args.kwargs['check'])
            self.assertEqual(run.call_args.kwargs['cwd'], module.ROOT)

    def test_generator_failure_is_not_reported_as_success(self):
        with patch.object(module, 'os') as windows, patch.object(module.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'powershell')):
            windows.name = 'nt'
            windows.environ = {'SystemRoot': 'C:/Windows'}
            with self.assertRaises(subprocess.CalledProcessError):
                module.main()

    def test_missing_project_does_not_run_generator(self):
        with patch.object(module, 'os') as windows, patch.object(module.Path, 'is_file', return_value=False), patch.object(module.subprocess, 'run') as run:
            windows.name = 'nt'
            windows.environ = {'SystemRoot': 'C:/Windows'}
            with self.assertRaises(FileNotFoundError):
                module.main()
            run.assert_not_called()
