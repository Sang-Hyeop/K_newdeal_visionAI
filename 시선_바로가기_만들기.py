# 역할: 기존 Windows 바로가기 생성기를 호출하여 바탕화면에 ‘시선’ 아이콘을 만듭니다.
"""프로젝트 전체를 압축 해제한 폴더에서 실행합니다. Python이나 패키지를 설치하지 않습니다."""
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent


def main():
    if os.name != 'nt':
        raise RuntimeError('이 파일은 Windows 바탕화면 바로가기 생성용입니다.')
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    script = ROOT / 'dashboard/packaging/windows/make_shortcut.ps1'
    for required in (script, ROOT / '시선.vbs', ROOT / 'dashboard_desktop.py'):
        if not required.is_file():
            raise FileNotFoundError('프로젝트 ZIP 전체를 압축 해제해주세요. 파일 없음: ' + str(required))
    # 경로에 한글·공백·대괄호가 있어도 셸 문자열로 조합하지 않습니다.
    subprocess.run([str(powershell), '-NoProfile', '-ExecutionPolicy', 'Bypass',
                    '-File', str(script)], cwd=ROOT, check=True, timeout=60)
    return 0


if __name__ == '__main__':
    try:
        main()
    except Exception:
        details = traceback.format_exc()
        try:
            folder = ROOT / '.sisun'
            folder.mkdir(exist_ok=True)
            (folder / 'shortcut-error.log').write_text(details, encoding='utf-8')
        except OSError:
            pass
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, details, '시선 바로가기 생성 실패', 16)
        else:
            print(details, file=sys.stderr)
        raise SystemExit(1)
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, '바탕화면에 시선 바로가기를 만들었습니다.\n바탕화면의 시선을 더블클릭하세요.\n프로젝트 폴더를 이동하거나 삭제하지 마세요.',
            '시선 바로가기 생성 완료', 64)
