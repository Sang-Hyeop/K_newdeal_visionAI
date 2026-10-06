"""직접 시각 검수한 TS07 8장: 960x540 화면 좌표를 원본 좌표로 복원."""
from pathlib import Path
import json,shutil,zipfile,cv2,numpy as np,hashlib
ROOT=Path(__file__).resolve().parents[1]
BOXES={101:[550,205,667,326],105:[362,168,582,280],109:[694,0,864,367],113:[221,0,398,283],117:[366,0,697,519],129:[601,158,811,361],145:[306,69,510,214],161:[208,101,375,270]}
def main():
 base=ROOT/'data/reviewed_pilot/logistics_v4';dest=ROOT/'data/reviewed_pilot/logistics_v6_corrected_forklift';assert not dest.exists(),'Protect existing dataset'
 candidates=json.loads((ROOT/'data/training_review/train_archives_v1/candidates.json').read_text());rows=json.loads((base/'manifest.json').read_text());shutil.copytree(base,dest);add=[];cache={}
 held={r['group'] for r in rows if r['training_eligible'] and r['split']!='train'}
 for row in candidates:
  n=row['review_id']
  if n not in BOXES:continue
  assert row['group'] not in held
  path=row['source_zip']
  if path not in cache:cache[path]=zipfile.ZipFile(path)
  image=cv2.imdecode(np.frombuffer(cache[path].read(row['image_member']),np.uint8),1);h,w=image.shape[:2];assert [w,h]==row['resolution']
  x1,y1,x2,y2=BOXES[n];boxes=[b for b in row['boxes'] if b[0]==0]+[[1,x1*w/960,y1*h/540,(x2-x1)*w/960,(y2-y1)*h/540]]
  name='fork_corrected_'+row['stem'];assert cv2.imwrite(str(dest/'train/images'/f'{name}.jpg'),image)
  for c,x,y,bw,bh in boxes:assert x>=0 and y>=0 and bw>0 and bh>0 and x+bw<=w and y+bh<=h
  (dest/'train/labels'/f'{name}.txt').write_text(''.join(f'{int(c)} {(x+bw/2)/w:.8f} {(y+bh/2)/h:.8f} {bw/w:.8f} {bh/h:.8f}\n' for c,x,y,bw,bh in boxes))
  row.update(stem=name,image=name+'.jpg',split='train',training_eligible=True,corrected_boxes=boxes,qa_status='manual_whole_image_review_and_forklift_box_correction',review_method='960x540 visual review; person boxes checked; forklift XYXY manually corrected; visible vehicle extent excluding cargo')
  rows.append(row);add.append(row)
  view=cv2.resize(image,(960,540))
  for c,x,y,bw,bh in boxes:cv2.rectangle(view,(round(x*960/w),round(y*540/h)),(round((x+bw)*960/w),round((y+bh)*540/h)),(0,255,0) if c==0 else (0,0,255),2)
  cv2.imwrite(str(ROOT/'data/training_review/train_archives_v1'/f'corrected-{n}.jpg'),view)
 for z in cache.values():z.close()
 for split in ['val','test']:
  for folder in ['images','labels']:
   for p in (base/split/folder).iterdir():assert p.read_bytes()==(dest/split/folder/p.name).read_bytes()
 hashes={}
 for split in ['train','val','test']:
  for p in (dest/split/'images').glob('*.jpg'):
   sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha not in hashes;hashes[sha]=str(p)
 (dest/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(dest/'dataset.yaml').write_text(f'path: {dest}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: person\n  1: forklift\n')
 (ROOT/'configs/review/corrected-forklift-v1.json').write_text(json.dumps(add,ensure_ascii=False,indent=2))
 print({s:len(list((dest/s/'images').glob('*.jpg'))) for s in ['train','val','test']})
if __name__=='__main__':main()
