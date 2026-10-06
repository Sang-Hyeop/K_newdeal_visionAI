"""육안으로 작성한 수동 라벨 초안을 출력합니다. 학습에서는 제외합니다."""
from pathlib import Path
import json, shutil
import cv2
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/label_review/annotated_examples'
NAMES=['person','forklift','helmet','no_helmet_head']
COLORS=[(70,210,70),(255,150,40),(0,220,255),(80,80,255)]
SAMPLES=[
 ('Helmet_forklift/Helmet_forklift__f000230.jpg',[
 (0,455,316,557,614),(0,540,279,633,537),(0,655,276,741,517),(0,738,304,816,580),(0,608,355,756,645),
 (2,484,316,527,352),(2,570,280,609,315),(2,675,277,716,308),(2,752,305,804,343),(3,685,356,739,418)],
 ['PPE-focused partial example: left/right foreground forklift mast intentionally not labeled; exclude from training.', 'Rear middle person lower body is occluded; visible silhouette enclosed.', 'Hooded head visibly lacks an external safety helmet; hidden under-hood equipment cannot be inferred.']),
 ('forklift_forward/forklift_forward__f000115.jpg',[
 (0,401,357,510,584),(0,789,190,840,279),(1,716,153,860,379),(2,412,357,459,391)],
 ['Forklift right/front is occluded by rack; box encloses visible vehicle only, excluding cargo.', 'Driver head is dark/unclear: PPE head label withheld; exclude this draft from training pending review.'])]

def main():
 for sub in ['images','labels','previews']: (OUT/sub).mkdir(parents=True,exist_ok=True)
 manifest=[]
 for relative, boxes, notes in SAMPLES:
  source=ROOT/'data/label_review'/relative
  im=cv2.imread(str(source))
  if im is None: raise RuntimeError(source)
  h,w=im.shape[:2]; lines=[]
  for index,(cls,x1,y1,x2,y2) in enumerate(boxes):
   assert 0<=cls<4 and 0<=x1<x2<=w and 0<=y1<y2<=h
   values=[(x1+x2)/2/w,(y1+y2)/2/h,(x2-x1)/w,(y2-y1)/h]
   lines.append(f'{cls} '+' '.join(f'{v:.6f}' for v in values))
   color=COLORS[cls];cv2.rectangle(im,(x1,y1),(x2,y2),color,2)
   text=f'{index+1}'
   y=max(15,y1-5)
   cv2.putText(im,text,(x1,y),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,0),3,cv2.LINE_AA)
   cv2.putText(im,text,(x1,y),cv2.FONT_HERSHEY_SIMPLEX,0.45,color,1,cv2.LINE_AA)
  for cls,name in enumerate(NAMES):
   cv2.putText(im,name,(15,30+cls*25),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,0),4,cv2.LINE_AA)
   cv2.putText(im,name,(15,30+cls*25),cv2.FONT_HERSHEY_SIMPLEX,0.6,COLORS[cls],1,cv2.LINE_AA)
  shutil.copy2(source,OUT/'images'/source.name)
  (OUT/'labels'/f'{source.stem}.txt').write_text('\n'.join(lines)+'\n')
  if not cv2.imwrite(str(OUT/'previews'/source.name),im): raise RuntimeError('preview write failed')
  manifest.append(dict(image=source.name,boxes=boxes,notes=notes,status='manual_visual_draft',training_eligible=False,split='review_only'))
 (OUT/'annotations.json').write_text(json.dumps(manifest,indent=2))
 print(f'{len(manifest)} draft images; {sum(len(s[1]) for s in SAMPLES)} boxes; review only')
if __name__=='__main__':main()
