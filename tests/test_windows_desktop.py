"""Windows 실행 소유권·응답 없는 실행 복구·잠금 재획득을 검증합니다."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from dashboard import windows_desktop as desktop


class OwnershipTests(unittest.TestCase):
    def test_only_exact_project_entry_is_owned(self):
        process = Mock()
        process.cmdline.return_value = ['pythonw.exe', str(desktop.ENTRY)]
        self.assertTrue(desktop.owned_launcher(process))
        process.cmdline.return_value = ['pythonw.exe', str(desktop.ENTRY.parent.parent / 'dashboard_desktop.py')]
        self.assertFalse(desktop.owned_launcher(process))

    def test_recovery_preserves_other_python_and_starting_instance(self):
        owned, other, starting = Mock(pid=101), Mock(pid=102), Mock(pid=103)
        for proc in (owned, other, starting):
            proc.cmdline.return_value = ['pythonw.exe', str(desktop.ENTRY)]
            proc.create_time.return_value = 100
        starting.create_time.return_value = 990
        other.cmdline.return_value = ['pythonw.exe', 'another_app.py']
        with patch.object(desktop.psutil, 'process_iter', return_value=[owned, other, starting]), \
             patch.object(desktop.time, 'time', return_value=1000), \
             patch.object(desktop, 'healthy', return_value=False), \
             patch.object(desktop, 'stop_tree') as stop:
            desktop.recover_unresponsive()
        stop.assert_called_once_with(owned)

    def test_healthy_instance_is_not_terminated(self):
        process = Mock(pid=101)
        process.cmdline.return_value = ['pythonw.exe', str(desktop.ENTRY)]
        process.create_time.return_value = 0
        with patch.object(desktop.psutil, 'process_iter', return_value=[process]), \
             patch.object(desktop, 'healthy', return_value=True), \
             patch.object(desktop, 'stop_tree') as stop:
            desktop.recover_unresponsive()
        stop.assert_not_called()


@unittest.skipUnless(os.name == 'nt', 'Windows OS 파일 잠금 검사')
class WindowsLockTests(unittest.TestCase):
    def test_release_allows_relaunch_without_deleting_lock_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'desktop.lock'
            first, second = desktop.InstanceLock(path), desktop.InstanceLock(path)
            try:
                self.assertTrue(first.acquire())
                self.assertFalse(second.acquire())
                first.release()
                self.assertTrue(path.exists())
                self.assertTrue(second.acquire())
            finally:
                first.release()
                second.release()
