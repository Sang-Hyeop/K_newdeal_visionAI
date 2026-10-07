"""Build explicitly authorized demo adaptation while preserving old evaluation splits."""
from pathlib import Path
import json,hashlib,shutil
import cv2,yaml
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 base=ROOT/'data/reviewed_pilot/logistics_related_v16';out=ROOT/'data/reviewed_pilot/logistics_demo_adaptation_v1';review=ROOT/'data/training_review/demo_adaptation_v1/overlays'
 if out.exists():raise ValueError('Existing dataset protected')
 review.mkdir(parents=True,exist_ok=True)
 rows=json.loads((base/'manifest.json').read_text())
 for split in ['train','val','test']:shutil.copytree(base/split,out/split)
 added=[]
 def write(im,name,boxes,meta,repeats):
  h,w=im.shape[:2];labels=[]
  for c,x,y,x2,y2 in boxes:
   assert c in [0,1] and 0<=x<x2<=w and 0<=y<y2<=h
   labels.append(f'{c} {(x+x2)/2/w:.8f} {(y+y2)/2/h:.8f} {(x2-x)/w:.8f} {(y2-y)/h:.8f}')
  overlay=cv2.resize(im,(960,540))
  for c,x,y,x2,y2 in boxes:cv2.rectangle(overlay,(round(x/w*960),round(y/h*540)),(round(x2/w*960),round(y2/h*540)),(0,255,0) if c==0 else (0,190,255),2)
  cv2.imwrite(str(review/(name+'.jpg')),overlay)
  for rep in range(repeats):
   image=f'{name}_r{rep}.jpg';assert cv2.imwrite(str(out/'train/images'/image),im)
   lab=out/'train/labels'/Path(image).with_suffix('.txt');lab.write_text('\n'.join(labels)+ ('\n' if labels else ''))
   row={**meta,'image':image,'split':'train','training_eligible':True,'repeat_index':rep,'source_repeat_count':repeats,'reviewed_boxes_xyxy':boxes,'image_sha256':sha(out/'train/images'/image),'label_sha256':sha(lab)};rows.append(row);added.append(row)
 for r in json.loads((ROOT/'configs/review/demo-adaptation-v1.json').read_text()):
  src=ROOT/'data/videos'/r['source'];assert sha(src)==r['source_sha256'];cap=cv2.VideoCapture(str(src));cap.set(1,r['frame_index']);ok,im=cap.read();cap.release();assert ok
  h,w=im.shape[:2];rw,rh=r['coordinate_reference'];boxes=[[c,x*w/rw,y*h/rh,x2*w/rw,y2*h/rh] for c,x,y,x2,y2 in r['boxes_xyxy']]
  stem=f"demo_{Path(r['source']).stem}_{r['frame_index']}";write(im,stem,boxes,{**r,'source':str(src),'group':Path(src).stem,'transform':'full_frame'},r['repeats'])
  if r.get('context_crop_xyxy'):
   l,t,rr,b=r['context_crop_xyxy'];clipped=[[c,max(x,l)-l,max(y,t)-t,min(x2,rr)-l,min(y2,b)-t] for c,x,y,x2,y2 in boxes if x2>l and y2>t and x<rr and y<b]
   write(im[t:b,l:rr],stem+'_context',clipped,{**r,'source':str(src),'group':Path(src).stem,'transform':'reviewed_context_crop','crop_xyxy':[l,t,rr,b]},r['crop_repeats'])
  if r['source']=='4_hazard_zone_dwell.mp4' and r['frame_index'] in [125,250]:
   for kind,(l,t,rr,b) in {'robot':(550,0,790,310),'sign':(820,380,990,720)}.items():
    assert not any(x2>l and y2>t and x<rr and y<b for c,x,y,x2,y2 in boxes)
    write(im[t:b,l:rr],stem+'_'+kind+'_negative',[],{**r,'source':str(src),'group':Path(src).stem,'transform':'reviewed_object_free_equipment_crop','crop_xyxy':[l,t,rr,b],'negative_kind':kind},2)
 for r in json.loads((ROOT/'configs/review/demo-adaptation-smartyard-v1.json').read_text()):
  p=Path(r['source']);assert sha(p)==r['source_image_sha256'];im=cv2.imread(str(p));assert [im.shape[1],im.shape[0]]==r['resolution'];write(im,Path(r['image']).stem,r['boxes_xyxy'],r,1)
 unchanged=[]
 for split in ['val','test']:
  for p in (base/split).rglob('*'):
   if p.is_file():assert sha(p)==sha(out/p.relative_to(base));unchanged.append({'path':str(p.relative_to(base)),'sha256':sha(p)})
 (out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 (out/'dataset.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'train/images','val':'val/images','test':'test/images','names':{0:'person',1:'forklift'}}))
 report={'counts':{s:sum(r['split']==s for r in rows) for s in ['train','val','test']},'new_weighted_images':len(added),'demo_unique_full_frames':19,'demo_target_contexts':8,'equipment_negative_contexts':4,'new_smartyard_images':8,'unchanged_val_test':unchanged,'evaluation_limit':'Demo source used in train; same-source results are adaptation checks, not independent accuracy.'}
 (out/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in report.items() if k!='unchanged_val_test'})
if __name__=='__main__':main()
