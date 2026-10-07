"""Build one reviewed, scale-preserving supplemental dataset; protect old splits."""
from pathlib import Path
import hashlib,json,shutil
import cv2,numpy as np,yaml
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 base=ROOT/'data/reviewed_pilot/logistics_related_v16';out=ROOT/'data/reviewed_pilot/logistics_targeted_v17'
 if out.exists():raise SystemExit('Existing dataset protected')
 decisions=json.loads((ROOT/'configs/review/related-forklift-v17.json').read_text())
 protocol=json.loads((ROOT/'configs/review/related-forklift-v17-protocol.json').read_text())
 held=set(protocol['held_source_groups']);rows=json.loads((base/'manifest.json').read_text())
 assert not any(r.get('video_group') in held for r in rows if r['split']=='train')
 assert not any(r['video_group'] in held for r in decisions)
 demos={sha(p) for p in (ROOT/'data/videos').glob('*.mp4')};verified={}
 for r in decisions:
  source=Path(r['source'])
  if source not in verified:verified[source]=sha(source)
  assert verified[source]==r['source_sha256'] and verified[source] not in demos
 for split in ['train','val','test']:shutil.copytree(base/split,out/split)
 review=ROOT/'outputs/diagnostics/targeted_failure_v17/approved_overlay';review.mkdir(parents=True,exist_ok=True)
 for k,r in enumerate(decisions):
  p=ROOT/'data/training_review/related_forklift_v1'/r['image'];assert sha(p)==r['source_frame_image_sha256']
  im=cv2.imread(str(p));h,w=im.shape[:2];assert (w,h)==(1920,1080)
  l,t,rr,b=[x*2 for x in r['context_xyxy_960']];canvas=np.full_like(im,114);canvas[t:b,l:rr]=im[t:b,l:rr];labels=[]
  overlay=cv2.resize(canvas,(960,540))
  for c,x1,y1,x2,y2 in r['boxes_xyxy_960']:
   assert l/2<=x1<x2<=rr/2 and t/2<=y1<y2<=b/2
   labels.append(f'{c} {(x1+x2)/960/2:.7f} {(y1+y2)/540/2:.7f} {(x2-x1)/960:.7f} {(y2-y1)/540:.7f}')
   cv2.rectangle(overlay,(x1,y1),(x2,y2),(0,255,0) if c else (255,100,0),2)
  cv2.putText(overlay,f"C{r['candidate_id']} {r.get('negative_kind','positive')}",(10,525),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2)
  cv2.imwrite(str(review/f'{k:02d}.jpg'),overlay)
  for repeat in range(r['repeats']):
   name=f"targeted_C{r['candidate_id']}_{r.get('negative_kind','positive')}_r{repeat}.jpg";cv2.imwrite(str(out/'train/images'/name),canvas)
   (out/'train/labels'/Path(name).with_suffix('.txt')).write_text('\n'.join(labels)+ ('\n' if labels else ''))
   row=dict(r);row.update(image=name,repeat_index=repeat,augmentation='neutral_mask_outside_reviewed_context_original_scale');rows.append(row)
 unchanged=[]
 for split in ['val','test']:
  for p in (base/split).rglob('*'):
   if p.is_file():assert sha(p)==sha(out/p.relative_to(base));unchanged.append({'path':str(p.relative_to(base)),'sha256':sha(p)})
 (out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 (out/'dataset.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'train/images','val':'val/images','test':'test/images','names':{0:'person',1:'forklift'}}))
 report={'train_images':sum(r['split']=='train' for r in rows),'new_unique_positive_frames':15,'positive_repeat_count':3,'negative_contexts':6,'negative_unique_source_frames':3,'unchanged_val_test_files':unchanged,'excluded_groups':sorted(held),'transform':protocol['data_transform'],'warning':'repeat images are sampling weight, not independent data'}
 (out/'build_report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='unchanged_val_test_files'}))
if __name__=='__main__':main()
