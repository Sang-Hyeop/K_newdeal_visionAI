"""기존 safety 환경의 버전 판정과 비파괴 재사용을 검증합니다."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_windows', ROOT / 'scripts/setup_windows.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class EnvironmentTests(unittest.TestCase):
    def test_wrong_python_rejected_before_package_changes(self):
        with patch.object(setup.sys, 'version_info', (3, 10)), patch.object(setup, 'call') as call:
            self.assertFalse(setup.compatible_environment())
            call.assert_not_called()

    def test_matching_pins_require_dependency_and_import_checks(self):
        pins = {}
        for name in ('requirements-runtime.txt', 'requirements-windows.txt'):
            for line in (ROOT / name).read_text(encoding='utf-8').splitlines():
                if '==' in line and not line.startswith('#'):
                    key, value = line.split('==')
                    pins[key.strip()] = value.strip()
        with patch('importlib.metadata.version', side_effect=pins.__getitem__), patch.object(setup, 'call') as call:
            self.assertTrue(setup.compatible_environment())
            self.assertEqual(call.call_count, 2)

    def test_mismatched_package_rejected(self):
        with patch('importlib.metadata.version', return_value='0.0.0'), patch.object(setup, 'call') as call:
            self.assertFalse(setup.compatible_environment())
            call.assert_not_called()

    def test_probe_failure_returns_without_installing(self):
        with patch.object(setup.sys, 'argv', ['setup_windows.py', '--probe']), patch.object(setup, 'compatible_environment', side_effect=ImportError), patch.object(setup, 'call') as call:
            self.assertEqual(setup.main(), 1)
            call.assert_not_called()
