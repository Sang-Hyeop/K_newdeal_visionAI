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

    def test_hung_same_project_owner_is_reaped_but_other_python_survives(self):
        import subprocess
        import sys
        import time
        import psutil
        with tempfile.TemporaryDirectory(prefix='시선 old owner ') as folder:
            root = Path(folder)
            entry = root / 'dashboard_desktop.py'
            lock_path = root / 'desktop.lock'
            ready = root / 'ready'
            entry.write_text(
                "import msvcrt, pathlib, time\n"
                "root = pathlib.Path(__file__).parent\n"
                "stream = (root / 'desktop.lock').open('a+b')\n"
                "stream.write(b' '); stream.flush(); stream.seek(0)\n"
                "msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)\n"
                "(root / 'ready').touch()\n"
                "time.sleep(300)\n", encoding='utf-8')
            owner = subprocess.Popen([sys.executable, str(entry)])
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'])
            lock = desktop.InstanceLock(lock_path)
            try:
                deadline = time.monotonic() + 10
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(.1)
                self.assertTrue(ready.exists())
                self.assertFalse(lock.acquire())
                future = time.time() + 200
                with patch.object(desktop, 'ENTRY', entry), \
                     patch.object(desktop.time, 'time', return_value=future), \
                     patch.object(desktop, 'healthy', return_value=False):
                    desktop.recover_unresponsive()
                owner.wait(timeout=10)
                self.assertIsNone(unrelated.poll())
                self.assertTrue(lock.acquire())
            finally:
                lock.release()
                for child in (owner, unrelated):
                    if child.poll() is None:
                        child.terminate()
                    child.wait(timeout=10)
