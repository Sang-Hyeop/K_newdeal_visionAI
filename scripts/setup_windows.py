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


def main():
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
    if not installed:
        call('-m', 'pip', 'install', '--disable-pip-version-check', '-r', requirement)
    call('-m', 'pip', 'check')
    call('-c', 'import gradio,pandas,cv2,torch,ultralytics,psutil,imageio_ffmpeg; print("라이브러리 로딩 정상")')
    call(ROOT / 'scripts/setup_runtime.py')
    call(ROOT / 'handoff.py', 'check', '--models')
    stamp.write_text(json.dumps({'requirements': signature}), encoding='utf-8')
    print('시선 설치 및 모델 검증 완료', flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print('설치 실패:', error, file=sys.stderr)
        raise SystemExit(1)
