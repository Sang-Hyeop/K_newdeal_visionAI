# 역할: 프로젝트 전용 Windows 환경에 의존성과 확정 실행 자료를 설치·검증합니다.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def call(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)


def compatible_environment():
    """기존 환경을 변경하지 않고 확정 버전과 실제 import를 확인합니다."""
    if sys.version_info[:2] != (3, 11) or sys.maxsize <= 2**32:
        return False
    from importlib.metadata import version
    from pip._vendor.packaging.requirements import Requirement
    for filename in ('requirements-runtime.txt', 'requirements-windows.txt'):
        for line in (ROOT / filename).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith(('#', '-r')):
                continue
            requirement = Requirement(line)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            if version(requirement.name) not in requirement.specifier:
                return False
    call('-m', 'pip', 'check')
    call('-c', 'import gradio,pandas,cv2,torch,ultralytics,psutil,imageio_ffmpeg')
    return True


def main():
    if '--probe' in sys.argv:
        try:
            return 0 if compatible_environment() else 1
        except Exception:
            return 1
    reuse = '--reuse' in sys.argv
    if reuse and not compatible_environment():
        raise RuntimeError('선택한 safety 환경의 호환성 검증에 실패했습니다.')
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError('Windows 자동 설치는 Python 3.11 환경을 사용합니다.')
    print('시선 설치: Python', sys.version, flush=True)
    requirement = ROOT / 'requirements-windows.txt'
    signature = hashlib.sha256(requirement.read_bytes() + (ROOT / 'requirements-runtime.txt').read_bytes()).hexdigest()
    stamp = Path(sys.prefix) / 'sisun-install.json'
    try:
        installed = json.loads(stamp.read_text()).get('requirements') == signature
    except (OSError, ValueError):
        installed = False
    if not installed and not reuse:
        call('-m', 'pip', 'install', '--disable-pip-version-check', '-r', requirement)
    call('-m', 'pip', 'check')
    call('-c', 'import gradio,pandas,cv2,torch,ultralytics,psutil,imageio_ffmpeg; print("라이브러리 로딩 정상")')
    call(ROOT / 'scripts/setup_runtime.py')
    call(ROOT / 'handoff.py', 'check', '--models')
    print('브라우저용 영상 6개와 감지 영상 캐시를 준비합니다. 처음에는 시간이 걸립니다.', flush=True)
    call('-c', "from pathlib import Path\n"
         "from dashboard.config import CAMERAS\n"
         "from dashboard.media import camera_origin, camera_detect\n"
         "for cam in CAMERAS:\n"
         "    for build in (camera_origin, camera_detect):\n"
         "        result = build(cam)\n"
         "        if not result or not Path(result).is_file(): raise RuntimeError(str(cam))\n"
         "print('브라우저 영상 준비 완료')")
    if not reuse:
        stamp.write_text(json.dumps({'requirements': signature}), encoding='utf-8')
    print('시선 설치 및 모델 검증 완료', flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print('설치 실패:', error, file=sys.stderr)
        raise SystemExit(1)
