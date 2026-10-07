"""Focused far/turning training expansion; historical evaluation images remain immutable."""
from pathlib import Path
import json,hashlib,shutil,random,cv2,yaml
ROOT=Path(__file__).resolve().parents[1]
def main():
 review=json.load(open(ROOT/'configs/review/forklift-demo-far-v5.json'));base=ROOT/'data/reviewed_pilot/forklift_far_v4';out=ROOT/'data/reviewed_pilot/forklift_demo_far_v5';out.mkdir(exist_ok=False);rows=[];old=json.load(open(base/'manifest.json'));rng=random.Random(20261007)
 selected=[r for r in old if r['split']!='train'or r['image'].startswith(('far_','video_'))]
 general=[r for r in old if r['split']=='train'and not r['image'].startswith(('far_','video_'))];positive=[];negative=[]
 for r in general:
  (positive if (base/'train/labels'/Path(r['image']).with_suffix('.txt').name).read_text().strip()else negative).append(r)
 rng.shuffle(positive);rng.shuffle(negative);selected+=positive[:40]+negative[:40]
 for split in ['train','val','test']:
  for kind in ['images','labels']:(out/split/kind).mkdir(parents=True)
 for r in selected:
  for kind,ext in [('images','.jpg'),('labels','.txt')]:shutil.copy2(base/r['split']/kind/Path(r['image']).with_suffix(ext).name,out/r['split']/kind/Path(r['image']).with_suffix(ext).name)
  rows.append(dict(r))
 for r in review['frames']:
  assert r['training_eligible'] and r['source_group']not in {'3_tr1','3_tr41','3_tr8','3_tr9','7_tr16','7_tr18','3_tr7','3_tr17'}
  p=ROOT/'data/training_review/forklift_demo_far_v5/frames'/r['image'];im=cv2.imread(str(p));h,w=im.shape[:2];a,b,c,d=[v*4.8 for v in r['bbox_xyxy_400']]
  def save(frame,box,name,kind):
   ih,iw=frame.shape[:2];x,y,z,t=box;assert 0<=x<z<=iw and 0<=y<t<=ih;cv2.imwrite(str(out/'train/images'/name),frame);(out/'train/labels'/Path(name).with_suffix('.txt').name).write_text(f'0 {(x+z)/2/iw:.7f} {(y+t)/2/ih:.7f} {(z-x)/iw:.7f} {(t-y)/ih:.7f}\n');rows.append({**r,'image':name,'split':'train','kind':kind,'source_frame_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  save(im,[a,b,c,d],'far_'+p.name,'full_frame')
  for i,pad_ratio in enumerate([.2,.55,1.0]):
   pad=max(c-a,d-b)*pad_ratio;x=max(0,int(a-pad));y=max(0,int(b-pad));z=min(w,int(c+pad));t=min(h,int(d+pad));save(im[y:t,x:z],[a-x,b-y,c-x,d-y],f'far_context{i}_'+p.name,'actual_context_crop')
 (out/'manifest.json').write_text(json.dumps(rows,indent=2));(out/'dataset.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'train/images','val':'val/images','test':'test/images','names':{0:'forklift'}}));summary={'counts':{s:sum(r['split']==s for r in rows)for s in ['train','val','test']},'new_full_frames':7,'new_context_crops':21,'evaluation_unchanged':True,'limits':['Same factory camera development specialization','Focused replay subset; previous bundle must be preserved for other scenes','No synthetic boxes or evaluation anchor frames used; adjacent demo frames are training-exposed']};(out/'preparation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__':main()
