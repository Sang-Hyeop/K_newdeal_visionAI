from pathlib import Path
import json,shutil,zipfile,hashlib,cv2
ROOT=Path(__file__).resolve().parents[1]
SCRATCH=ROOT/'data/training_review/train_videos_v1'
base=ROOT/'data/reviewed_pilot/logistics_v4'; dest=ROOT/'data/reviewed_pilot/logistics_v5_train_sources'
assert not dest.exists()
shutil.copytree(base,dest)
rows=json.loads((base/'manifest.json').read_text())
archives=json.loads((ROOT/'data/training_review/train_archives_v1/candidates.json').read_text())
cache={}; added=[]
def write(image,name,boxes,row):
 h,w=image.shape[:2]
 assert boxes
 for c,x,y,bw,bh in boxes: assert c in [0,1] and x>=0 and y>=0 and bw>0 and bh>0 and x+bw<=w+1e-4 and y+bh<=h+1e-4
 assert cv2.imwrite(str(dest/'train/images'/f'{name}.jpg'),image)
 (dest/'train/labels'/f'{name}.txt').write_text(''.join(f'{int(c)} {(x+bw/2)/w:.8f} {(y+bh/2)/h:.8f} {bw/w:.8f} {bh/h:.8f}\n' for c,x,y,bw,bh in boxes))
 row.update(stem=name,image=name+'.jpg',split='train',training_eligible=True,corrected_boxes=boxes)
 rows.append(row);added.append(row)
for row in archives:
 if row['source_kind']!='04':continue
 path=row['source_zip']
 if path not in cache:cache[path]=zipfile.ZipFile(path)
 import numpy as np
 im=cv2.imdecode(np.frombuffer(cache[path].read(row['image_member']),dtype=np.uint8),cv2.IMREAD_COLOR)
 assert [im.shape[1],im.shape[0]]==row['resolution']
 row['qa_status']='source_annotation_structural_validation_and_7_of_100_visual_sample_review'
 row['review_method']='original official person boxes; no claim of exhaustive manual review'
 write(im,'archive_'+row['stem'],row['boxes'],row)
manual={1:[[50,84,178,230]],2:[[70,165,337,580]],3:[[52,208,345,580]],4:[[55,78,242,266]],6:[[6,192,217,430],[183,322,359,430],[243,0,514,430]],7:[[65,32,125,183],[120,45,192,113]],8:[[53,74,259,267]]}
video_rows=json.loads((SCRATCH/'crop-candidates.json').read_text())
demo_hashes={hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/videos').glob('*.mp4')}
for row in video_rows:
 if row['id'] not in manual:continue
 sha=hashlib.sha256(Path(row['source']).read_bytes()).hexdigest();assert sha not in demo_hashes
 image=cv2.imread(str(SCRATCH/f"{row['id']:02d}-crop.jpg"))
 boxes=[[0,x1,y1,x2-x1,y2-y1] for x1,y1,x2,y2 in manual[row['id']]]
 row.update(source_sha256=sha,group=Path(row['source']).stem,qa_status='manually_reviewed_visible_person_crop_boxes',review_method='manual visible body bounding boxes; partial bodies included',camera_generalization='same factory camera domain as some demos; not unseen-site evaluation')
 write(image,f"trainvideo_{row['id']:02d}",boxes,row)
for z in cache.values():z.close()
# Frozen validation/test sets: byte-for-byte unchanged.
for split in ['val','test']:
 for folder in ['images','labels']:
  for p in (base/split/folder).iterdir():assert p.read_bytes()==(dest/split/folder/p.name).read_bytes()
(dest/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
(dest/'dataset.yaml').write_text(f'path: {dest}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: person\n  1: forklift\n')
(ROOT/'configs/review/train-sources-v1.json').write_text(json.dumps({'added':added,'held_archive_kind':'07: cargo-inclusive forklift boxes require correction','held_video_crop':[5],'visual_sample_ids':[1,17,33,49,65,81,97],'demos_excluded_by_sha256':True},ensure_ascii=False,indent=2))
print({s:len(list((dest/s/'images').glob('*.jpg'))) for s in ['train','val','test']})
print('Added',len(added),'including',len(manual),'train-video crops')
