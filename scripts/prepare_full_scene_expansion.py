"""전체 CCTV 프레임의 수동 검수 라벨. 애매한 원거리 영역은 일부 이미지에서 명시적으로 마스크."""
from pathlib import Path
import json,cv2,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
# 960x540 화면 XYXY. 0 person, 1 forklift.
MANUAL={
'source2_52':[[0,287,337,416,540],[0,4,162,37,244],[0,87,58,111,100],[0,191,97,219,111],[0,350,57,385,137],[0,502,45,535,127]],
'source2_130':[[0,285,334,417,540],[0,87,58,111,100],[0,187,96,220,112],[0,324,56,365,129]],
'source2_208':[[0,170,371,288,540],[0,5,160,42,283],[0,89,65,120,101],[0,187,91,220,109]],
'source3_24':[[0,280,341,421,540],[0,87,58,111,100],[0,110,46,149,89],[0,266,60,306,113]],
'source3_62':[[0,283,350,420,540],[0,87,58,111,100],[0,120,52,155,89]],
'source3_99':[[0,280,345,421,540],[0,6,143,39,224],[0,89,57,111,100],[0,111,48,139,103]],
'source4_24':[[1,83,6,149,125],[0,763,210,850,308]],
'source4_62':[[1,92,10,174,139],[0,763,210,850,309]],
'source4_99':[[1,109,24,198,158],[0,764,210,848,309]],
'source8_45':[[1,167,52,293,211],[0,766,210,850,309]],
}
def main():
 base=ROOT/'data/reviewed_pilot/logistics_v6_corrected_forklift';dest=ROOT/'data/reviewed_pilot/logistics_v7_full_scene';review=ROOT/'data/training_review/full_scene_v1';assert not dest.exists()
 rows=json.loads((base/'manifest.json').read_text());candidates=json.loads((review/'candidates.json').read_text());shutil.copytree(base,dest);added=[]
 demos={hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/videos').glob('*.mp4')};hashes={}
 for item in candidates:
  stem=Path(item['image']).stem
  if stem not in MANUAL:continue
  source_sha=hashlib.sha256(Path(item['source']).read_bytes()).hexdigest();assert source_sha not in demos
  im=cv2.imread(str(review/item['image']));h,w=im.shape[:2];assert (w,h)==(1920,1080)
  masks=[[300 if item['id']==8 else 200,0,960,200]] if item['id'] in [4,8] else []
  for x1,y1,x2,y2 in masks:im[y1*2:y2*2,x1*2:x2*2]=0
  name='cctv_full_'+stem;cv2.imwrite(str(dest/'train/images'/(name+'.jpg')),im)
  boxes=[[c,x1*2,y1*2,(x2-x1)*2,(y2-y1)*2] for c,x1,y1,x2,y2 in MANUAL[stem]]
  for c,x,y,bw,bh in boxes:assert x>=0 and y>=0 and bw>0 and bh>0 and x+bw<=w and y+bh<=h
  (dest/'train/labels'/(name+'.txt')).write_text(''.join(f'{c} {(x+bw/2)/w:.8f} {(y+bh/2)/h:.8f} {bw/w:.8f} {bh/h:.8f}\n' for c,x,y,bw,bh in boxes))
  row=dict(item,stem=name,image=name+'.jpg',split='train',group=Path(item['source']).stem,training_eligible=True,corrected_boxes=boxes,source_sha256=source_sha,masked_regions_xyxy_960=masks,qa_status='manual_whole_frame_review_with_declared_ignore_masks' if masks else 'manual_whole_frame_visible_person_review',camera_generalization='factory camera domain overlaps some demos; not unseen-site evaluation')
  rows.append(row);added.append(row)
  view=cv2.resize(im,(960,540))
  for c,x1,y1,x2,y2 in MANUAL[stem]:cv2.rectangle(view,(x1,y1),(x2,y2),(0,255,0) if c==0 else (0,0,255),2)
  cv2.imwrite(str(review/(stem+'_labelled.jpg')),view)
 for split in ['val','test']:
  for folder in ['images','labels']:
   for p in (base/split/folder).iterdir():assert p.read_bytes()==(dest/split/folder/p.name).read_bytes()
 for split in ['train','val','test']:
  for p in (dest/split/'images').glob('*.jpg'):
   sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha not in hashes;hashes[sha]=str(p)
 (dest/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(dest/'dataset.yaml').write_text(f'path: {dest}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: person\n  1: forklift\n')
 (ROOT/'configs/review/full-scene-v1.json').write_text(json.dumps({'added':added,'held':['source8_113','source8_181'],'held_reason':'cab visibility and foreground occlusion remain ambiguous; no unverified automatic person labels','raw_frames':6,'masked_frames':4,'adjacent_frames_all_train':True},ensure_ascii=False,indent=2))
 print({s:len(list((dest/s/'images').glob('*.jpg'))) for s in ['train','val','test']})
if __name__=='__main__':main()
