"""Windows 설치 자식 프로세스의 실패·시간 제한을 실제 PowerShell로 검증합니다."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell 5.1 실행 검사')
class InstallWaitTests(unittest.TestCase):
    def execute(self, code):
        source = (ROOT / 'dashboard/packaging/windows/install.ps1').read_text(encoding='utf-8-sig')
        helper = 'function Invoke-InstallProcess' + source.split('function Invoke-InstallProcess', 1)[1].split('# conda 등록', 1)[0]
        with tempfile.TemporaryDirectory(prefix='sisun [wait] ') as directory:
            folder = Path(directory)
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            script = folder / 'test.ps1'
            script.write_text("$ErrorActionPreference='Stop'\n$State=" + quote(folder) + "\n$Log='test.log'\n$Python=" + quote(sys.executable) + '\n' + helper + '\n' + code, encoding='utf-8-sig')
            powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            return subprocess.run([str(powershell), '-NoProfile', '-File', str(script)], capture_output=True, timeout=20)

    def test_version_mismatch_is_quiet_and_returns_nonzero(self):
        result = self.execute("$Code=Invoke-InstallProcess $Python @('-c', 'import sys; sys.exit(1)') -TimeoutSeconds 3 -QuietFailure\nif ($Code -ne 1) { throw 'exit code lost' }")
        self.assertEqual(result.returncode, 0, repr(result.stderr))
        self.assertNotIn(b'Traceback', result.stdout + result.stderr)

    def test_hung_process_times_out(self):
        result = self.execute("try { $Code=Invoke-InstallProcess $Python @('-c', 'import time; time.sleep(60)') -TimeoutSeconds 1; exit 2 } catch { exit 0 }")
        self.assertEqual(result.returncode, 0, repr(result.stderr))
