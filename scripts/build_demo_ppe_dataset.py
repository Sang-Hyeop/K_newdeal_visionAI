"""Explicitly authorized PPE demo adaptation, with unobservable hoods excluded."""
from pathlib import Path
import json,hashlib,shutil
import cv2,yaml
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 base=ROOT/'data/reviewed_pilot/expansion_v3/ppe';out=ROOT/'data/reviewed_pilot/ppe_demo_adaptation_v1';review=ROOT/'data/training_review/demo_ppe_adaptation_v1/overlays'
 if out.exists():raise ValueError('Existing dataset protected')
 review.mkdir(parents=True,exist_ok=True);rows=json.loads((base/'manifest.json').read_text());added=[]
 for split in ['train','val','test']:shutil.copytree(base/split,out/split)
 def write(im,name,boxes,meta,repeats):
  h,w=im.shape[:2];labs=[]
  for c,x,y,x2,y2 in boxes:
   assert c in [0,1] and 0<=x<x2<=w and 0<=y<y2<=h
   labs.append(f'{c} {(x+x2)/2/w:.8f} {(y+y2)/2/h:.8f} {(x2-x)/w:.8f} {(y2-y)/h:.8f}')
  canvas=cv2.resize(im,(960,540))
  for c,x,y,x2,y2 in boxes:cv2.rectangle(canvas,(round(x/w*960),round(y/h*540)),(round(x2/w*960),round(y2/h*540)),(0,255,0) if c==0 else (0,190,255),2)
  cv2.imwrite(str(review/(name+'.jpg')),canvas)
  for rep in range(repeats):
   image=f'{name}_r{rep}.jpg';cv2.imwrite(str(out/'train/images'/image),im);(out/'train/labels'/Path(image).with_suffix('.txt')).write_text('\n'.join(labs)+'\n');row={**meta,'image':image,'training_eligible':True,'split':'train','repeat_index':rep,'repeat_count':repeats,'reviewed_boxes_xyxy':boxes};rows.append(row);added.append(row)
 for i,r in enumerate(json.loads((ROOT/'configs/review/demo-ppe-adaptation-v1.json').read_text())):
  src=ROOT/'data/videos'/r['source'];assert sha(src)==r['source_sha256'];cap=cv2.VideoCapture(str(src));cap.set(1,r['frame_index']);ok,im=cap.read();cap.release();assert ok;h,w=im.shape[:2];rw,rh=r['coordinate_reference'];boxes=[[c,x*w/rw,y*h/rh,x2*w/rw,y2*h/rh] for c,x,y,x2,y2 in r['boxes_xyxy']]
  if r.get('crop_xyxy_reference'):
   l,t,rr,b=[round(v*(w/rw if j%2==0 else h/rh)) for j,v in enumerate(r['crop_xyxy_reference'])];im=im[t:b,l:rr];boxes=[[c,x-l,y-t,x2-l,y2-t] for c,x,y,x2,y2 in boxes]
  write(im,f'demo_ppe_{i}',boxes,{**r,'source':str(src),'group':Path(src).stem},r['repeats'])
 for i,r in enumerate(json.loads((ROOT/'configs/review/demo-ppe-smartyard-v1.json').read_text())):
  p=Path(r['source']);assert sha(p)==r['source_image_sha256'];im=cv2.imread(str(p));h,w=im.shape[:2]
  for j,(c,x,y,x2,y2) in enumerate(r['boxes_xyxy']):
   pw=x2-x;ph=y2-y;l=max(0,int(x-pw));t=max(0,int(y-ph));rr=min(w,int(x2+pw));b=min(h,int(y2+ph));boxes=[[cc,max(xx,l)-l,max(yy,t)-t,min(xx2,rr)-l,min(yy2,b)-t] for cc,xx,yy,xx2,yy2 in r['boxes_xyxy'] if xx2>l and yy2>t and xx<rr and yy<b];write(im[t:b,l:rr],f'smartyard_ppe_support_{i}_{j}',boxes,{**r,'crop_xyxy':[l,t,rr,b],'transform':'annotated_head_context_crop'},1)
 for split in ['val','test']:
  for p in (base/split).rglob('*'):
   if p.is_file():assert sha(p)==sha(out/p.relative_to(base))
 (out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');(out/'dataset.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'train/images','val':'val/images','test':'test/images','names':{0:'helmeted_head',1:'no_helmet_head'}}))
 report={'counts':{s:sum(r['split']==s and r['training_eligible'] for r in rows) for s in ['train','val','test']},'new_weighted_images':len(added),'old_splits_preserved':True,'hoods_are_unobservable_not_no_helmet_labels':True,'demo_target_training_exposed':True}
 (out/'build_report.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':main()
