# 역할: 이 파일 하나로 Windows 실행 환경을 확인·준비한 뒤 시선 앱을 실행합니다.
"""프로젝트 ZIP을 모두 압축 해제한 뒤 실행합니다. 시작에는 Python 표준 라이브러리만 사용합니다."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent
STATE = ROOT / '.sisun'
SETUP = ROOT / 'scripts/setup_windows.py'
ENV = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')


def capture(command):
    """환경 검색 실패나 응답 지연은 다음 후보 검색으로 넘깁니다."""
    try:
        result = subprocess.run(command, cwd=ROOT, env=ENV, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=30)
        return result.stdout.strip() if result.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def candidates():
    """현재 Python, Conda 환경 등록 목록, 사용자별 설치 위치를 탐색합니다."""
    prefixes = []
    if os.environ.get('CONDA_PREFIX'):
        prefixes.append(Path(os.environ['CONDA_PREFIX']))
    registration = Path.home() / '.conda/environments.txt'
    if registration.is_file():
        prefixes.extend(Path(line.strip()) for line in registration.read_text(encoding='utf-8').splitlines() if line.strip())
    conda_paths = [os.environ.get('CONDA_EXE'), shutil.which('conda.exe')]
    for home in (Path.home(), Path(os.environ.get('LOCALAPPDATA', str(Path.home()))),
                 Path(os.environ.get('ProgramData', 'C:/ProgramData'))):
        for name in ('anaconda3', 'miniconda3', 'miniforge3'):
            base = home / name
            conda_paths.append(str(base / 'Scripts/conda.exe'))
            prefixes.append(base / 'envs/safety')
    for conda in dict.fromkeys(path for path in conda_paths if path):
        if not Path(conda).is_file():
            continue
        try:
            prefixes.extend(Path(path) for path in json.loads(capture([conda, 'env', 'list', '--json'])).get('envs', []))
        except (ValueError, TypeError):
            continue
    paths = [path / 'python.exe' for path in prefixes if path.name.lower() == 'safety']
    selected = STATE / 'runtime-pythonw.txt'
    if selected.is_file():
        paths.append(Path(selected.read_text(encoding='utf-8-sig').strip()).with_name('python.exe'))
    paths.extend([Path(sys.executable).with_name('python.exe'), STATE / 'venv/Scripts/python.exe'])
    seen = set()
    for path in paths:
        key = os.path.normcase(str(path.resolve()))
        if key not in seen and path.is_file():
            seen.add(key)
            yield path


def probe(python):
    print('환경 검사:', python, flush=True)
    try:
        return subprocess.run([str(python), str(SETUP), '--probe'], cwd=ROOT,
                              env=ENV, timeout=90).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def run(command):
    subprocess.run(list(map(str, command)), cwd=ROOT, env=ENV, check=True)


def prepare():
    for python in candidates():
        if not probe(python):
            continue
        # 패키지가 같아도 새 프로젝트의 모델·영상 자료는 최초 한 번 검증합니다.
        signature = hashlib.sha256((ROOT / 'requirements-runtime.txt').read_bytes()
                                   + (ROOT / 'requirements-windows.txt').read_bytes()).hexdigest()
        ready = STATE / 'python-launch-ready.json'
        expected = {'python': str(python.resolve()), 'requirements': signature}
        try:
            installed = json.loads(ready.read_text(encoding='utf-8')) == expected
        except (OSError, ValueError):
            installed = False
        if not installed:
            print('실행 자료와 영상 준비 중입니다. 창을 닫지 마세요.', flush=True)
            run([python, SETUP, '--reuse'])
            ready.write_text(json.dumps(expected), encoding='utf-8')
        return python
    print('호환되는 환경이 없어 기존 설치기로 전용 환경을 준비합니다.', flush=True)
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    run([powershell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
         ROOT / 'dashboard/packaging/windows/install.ps1'])
    python = Path((STATE / 'runtime-pythonw.txt').read_text(encoding='utf-8-sig').strip()).with_name('python.exe')
    if not python.is_file() or not probe(python):
        raise RuntimeError('설치 후 실행 환경 검증에 실패했습니다.')
    return python


def main():
    # .py 연결 프로그램이 pythonw여도 빈 화면 대신 진행 상황을 볼 수 있게 합니다.
    if os.name == 'nt' and sys.stdout is None:
        import ctypes
        ctypes.windll.kernel32.AllocConsole()
        sys.stdout = open('CONOUT$', 'w', encoding='utf-8', buffering=1)
        sys.stderr = sys.stdout
        sys.stdin = open('CONIN$', 'r', encoding='utf-8')
    print('시선 실행을 시작합니다. 환경 확인 결과가 이 창에 표시됩니다.', flush=True)
    if not (ROOT / 'dashboard_desktop.py').is_file() or not SETUP.is_file():
        raise RuntimeError('이 파일만 옮기면 실행할 수 없습니다. 프로젝트 ZIP 전체를 압축 해제하세요.')
    if os.name != 'nt':
        run([sys.executable, ROOT / 'dashboard_desktop.py'])
        return
    STATE.mkdir(exist_ok=True)
    python = prepare()
    print('시선 실행 환경:', python, flush=True)
    # 기존 앱 진입점을 그대로 사용하여 중복 실행·종료·복구 동작을 유지합니다.
    run([python, ROOT / 'dashboard_desktop.py'])


if __name__ == '__main__':
    try:
        main()
    except Exception:
        details = traceback.format_exc()
        print(details, flush=True)
        try:
            STATE.mkdir(exist_ok=True)
            (STATE / 'python-launch-error.log').write_text(details, encoding='utf-8')
        except OSError:
            pass
        if os.name == 'nt':
            try:
                input('실행 실패: 위 내용을 확인한 뒤 Enter를 누르면 닫힙니다. ')
            except EOFError:
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, details, '시선 실행 실패', 16)
        raise SystemExit(1)
