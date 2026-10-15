"""고정 카메라의 빈 설비 참조 이미지와 비교해 사람처럼 보이는 고정 오탐을 걸러낸다."""
from functools import lru_cache
from pathlib import Path
import cv2,numpy as np

@lru_cache(maxsize=8)
def _reference(path):
    image=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
    if image is None:raise ValueError('Equipment reference image unavailable')
    return image

def matches_empty_equipment(frame,region):
    if frame is None:return False
    cfg=region['empty_reference'];h,w=frame.shape[:2]
    if [w,h]!=cfg['frame_size']:raise ValueError('Equipment reference camera dimensions changed')
    x,y,xx,yy=cfg['comparison_box_xyxy'];current=cv2.cvtColor(frame[y:yy,x:xx],cv2.COLOR_BGR2GRAY)
    reference=_reference(Path(__file__).resolve().parents[1]/cfg['image_path'])
    if current.shape!=reference.shape:raise ValueError('Equipment reference patch shape changed')
    difference=cv2.absdiff(cv2.GaussianBlur(current,(7,7),0),cv2.GaussianBlur(reference,(7,7),0))
    return float(np.mean(difference>cfg['pixel_difference_threshold']))<=cfg['maximum_changed_fraction']
