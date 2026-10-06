"""safety 환경에서 실행: python scripts/extract_review_frames.py"""
from pathlib import Path
import json
import cv2

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data' / 'label_review'
FRACTIONS = (0.0, 0.2, 0.4, 0.6, 0.8, 0.96)

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    records = []
    videos = sorted((ROOT / 'data' / 'videos').glob('*.mp4'))
    if not videos:
        raise RuntimeError('data/videos 에 mp4 영상이 없습니다.')
    for source in videos:
        cap = cv2.VideoCapture(str(source))
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if not cap.isOpened() or fps <= 0 or total <= 0:
                raise RuntimeError(f'영상 읽기 실패: {source}')
            folder = DEST / source.stem
            folder.mkdir(exist_ok=True)
            for fraction in FRACTIONS:
                index = min(total - 1, round(total * fraction))
                cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f'프레임 읽기 실패: {source.name}, {index}')
                name = f'{source.stem}__f{index:06d}.jpg'
                target = folder / name
                if not cv2.imwrite(str(target), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    raise RuntimeError(f'저장 실패: {target}')
                records.append(dict(source=str(source.relative_to(ROOT)), image=str(target.relative_to(ROOT)), frame_index=index, timestamp_seconds=round(index/fps, 3), fps=fps, width=frame.shape[1], height=frame.shape[0], purpose='label_policy_review', split='unassigned', annotated=False))
        finally:
            cap.release()
    (DEST / 'manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(videos)} videos, {len(records)} original-resolution frames -> {DEST}')

if __name__ == '__main__':
    main()
