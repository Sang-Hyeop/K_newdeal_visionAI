# 발표 영상 찾기·브라우저용 H.264
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .api import presentation_row
from .config import DATA_ROOT, LOCAL, NEEDED_VIDEOS, SID_TO_VIDEO, VIDEO_DIR, VIDEO_FILES, WAREHOUSE_VIDEO, _src_video

def find_demo(num):
    """확정 리뷰(선·상자)를 먼저 쓰고, 없을 때만 handoff 임시 결과를 쓴다."""
    row = presentation_row(num)
    if row and row.get("review_video"):
        review = DATA_ROOT / row["review_video"]
        if review.is_file() and review.stat().st_size > 0:
            return review
    found = []
    runs = DATA_ROOT / "outputs" / "handoff_runs"
    if runs.is_dir():
        found += [p for p in runs.glob(f"presentation{num}_*/**/demo.mp4") if p.is_file() and p.stat().st_size > 0]
        found += [p for p in runs.glob(f"presentation{num}_*/*.mp4") if p.is_file() and p.stat().st_size > 0]
    if not found:
        return None
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found[0]


def ensure_repo_demos():
    """발표 1~4 결과 영상이 없으면 handoff.py run 으로 만든다."""
    handoff = DATA_ROOT / "handoff.py"
    if not handoff.is_file():
        print("handoff.py 가 없습니다.", DATA_ROOT)
        return
    for n in NEEDED_VIDEOS:
        if find_demo(n) is not None:
            continue
        cmd = [sys.executable, str(handoff), "run", "--video", str(n)]
        print("handoff 생성", " ".join(cmd))
        subprocess.run(cmd, cwd=str(DATA_ROOT), check=False)

def video_path(name):
    path = VIDEO_DIR / name
    return str(path) if path.is_file() else None


def origin_clip(filename, dest_name):
    """메인 CCTV용 원본. 선·상자 없는 파일."""
    src = video_path(filename)
    if not src:
        return None
    return to_browser_mp4(src, dest_name)


def pack_demo_num(num):
    found = find_demo(num)
    if found is None:
        ensure_repo_demos()
        found = find_demo(num)
    return str(found) if found else None


def demo_clip(sid=None, num=None):
    """발표 결과 H.264. 선·상자 영상이 없으면 원본."""
    if num is None:
        num = SID_TO_VIDEO.get(sid)
    found = pack_demo_num(num) if num is not None else None
    if found:
        tag = sid if sid else num
        return to_browser_mp4(found, f"demo_{tag}.mp4")
    if sid in VIDEO_FILES:
        return video_path(VIDEO_FILES[sid])
    if num is not None:
        return video_path(_src_video(num))
    return video_path(WAREHOUSE_VIDEO)


def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def to_browser_mp4(src, dest_name):
    """브라우저가 못 읽는 mp4v 를 H.264 로 바꾼다. 결과는 team7_data 에 둔다."""
    if not src or not os.path.isfile(src):
        return src
    os.makedirs(LOCAL, exist_ok=True)
    dest = os.path.join(LOCAL, dest_name)
    stamp = dest + ".stamp"
    if (
        os.path.isfile(dest)
        and os.path.getsize(dest) > 0
        and os.path.getmtime(dest) >= os.path.getmtime(src)
    ):
        return dest
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return src
    cmd = [
        ffmpeg, "-y", "-i", src, "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", dest,
    ]
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except Exception:
        return src
    if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
        return src
    Path(stamp).write_text("ok", encoding="utf-8")
    print("browser mp4", dest)
    return dest
