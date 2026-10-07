"""Build reviewed forklift-only expansion. Unapproved frames are never negatives."""
from pathlib import Path
import json,random,shutil,hashlib,cv2,yaml
ROOT=Path(__file__).resolve().parents[1]
def main():
 review=json.loads((ROOT/'configs/review/safe-carrying-body-v1.json').read_text());base=ROOT/'data/reviewed_pilot/logistics_related_v16';nv=ROOT/'data/reviewed_pilot/nvidia_object_adaptation_v1';out=ROOT/'data/reviewed_pilot/safe_carrying_specialist_v1';out.mkdir(exist_ok=False);rows=[]
 for s in ['train','val','test']:
  for d in ['images','labels']:(out/s/d).mkdir(parents=True)
 def old(p,label,split,origin):
  target=out/split/'images'/p.name
  if target.exists():return
  shutil.copy2(p,target);lines=[]
  for line in label.read_text().splitlines():
   v=line.split()
   if v and v[0]=='1':lines.append('0 '+' '.join(v[1:]))
  (out/split/'labels'/p.with_suffix('.txt').name).write_text('\n'.join(lines)+'\n'if lines else '')
  rows.append({'image':p.name,'split':split,'training_eligible':True,'source_dataset':str(origin),'status':'existing_reviewed_forklift_annotations_remapped_1_to_0','image_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 # Preserve ALL reviewed replay; person class is explicitly outside single-class taxonomy.
 for split in ['train','val','test']:
  for p in sorted((base/split/'images').glob('*.jpg')):old(p,base/split/'labels'/p.with_suffix('.txt').name,split,base)
 # New Nvidia samples only; avoid duplicating replay already present.
 for split in ['train','val','test']:
  for p in sorted((nv/split/'images').glob('video_*.jpg')):old(p,nv/split/'labels'/p.with_suffix('.txt').name,split,nv)
 # Previously reserved same-camera groups remain reserved. They are not an unseen-site benchmark.
 held_test={'3_tr1','3_tr41','3_tr8','3_tr9','7_tr16','7_tr18'};held_val={'3_tr7','3_tr17'}
 for row in review['frames']:
  if not row['training_eligible']:continue
  split='test'if row['source_group']in held_test else 'val'if row['source_group']in held_val else 'train';p=ROOT/'data/training_review/safe_carrying_v1/frames'/row['image'];im=cv2.imread(str(p));h,w=im.shape[:2];l,t,r,b=row['box_xyxy_400'];box=[l*w/400,t*h/225,r*w/400,b*h/225]
  def save(image,box,name,kind):
   ih,iw=image.shape[:2];a,y,c,z=box;assert 0<=a<c<=iw and 0<=y<z<=ih
   cv2.imwrite(str(out/split/'images'/name),image);(out/split/'labels'/Path(name).with_suffix('.txt')).write_text(f'0 {(a+c)/2/iw:.7f} {(y+z)/2/ih:.7f} {(c-a)/iw:.7f} {(z-y)/ih:.7f}\n');rows.append({**row,'image':name,'split':split,'kind':kind,'training_eligible':True,'label_scope':'visible_body_cab; dedicated forklift-only model','source_frame_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  save(im,box,'safe_'+p.name,'full_frame')
  if split=='train':
   a,y,c,z=box;pad=max(c-a,z-y)*.45;x1=max(0,int(a-pad));y1=max(0,int(y-pad));x2=min(w,int(c+pad));y2=min(h,int(z+pad));save(im[y1:y2,x1:x2],[a-x1,y-y1,c-x1,z-y1],'safe_context_'+p.name,'body_context_crop')
 (out/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'dataset.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'train/images','val':'val/images','test':'test/images','names':{0:'forklift'}}));summary={'counts':{s:sum(r['split']==s for r in rows)for s in ['train','val','test']},'new_reviewed_full_frames':89,'source_groups_by_split':{s:sorted({r.get('source_group')for r in rows if r['split']==s and r.get('source_group')})for s in ['train','val','test']},'taxonomy':['forklift'],'limits':['New review is body-focused; does not assert hidden full vehicle extents','Same factory camera, clips may overlap recording events','Original held groups retained; no new-site generalization claim','Do not replace person or PPE detectors with single-class specialist']};(out/'preparation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__':main()
