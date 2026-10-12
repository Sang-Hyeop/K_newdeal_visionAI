from pathlib import Path
import json,cv2,yaml,hashlib
w=Path('/Users/sanghyeopkim/Desktop/workspace');base=w/'data/reviewed_pilot/forklift_cvat_combined_v1';out=w/'data/reviewed_pilot/forklift_real_context_v2';(out/'train/images').mkdir(parents=True,exist_ok=True);(out/'train/labels').mkdir(exist_ok=True)
rows=json.loads((base/'manifest.json').read_text());new=json.loads((w/'data/reviewed_pilot/forklift_cvat_prepared_v1/manifest.json').read_text());eligible=[r for r in new if r['training_eligible'] and r['split']=='train' and r['kind'] in ['screenshot','SafeUnsafe']];crops=[];hashes=set()
for r in eligible:
 f=cv2.imread(r['path']);h,ww=f.shape[:2]
 for j,b in enumerate(r['boxes']):
  a,y,z,t=b
  for pad in [.5,1.0]:
   margin=max(z-a,t-y)*pad;x0=max(0,int(a-margin));y0=max(0,int(y-margin));x1=min(ww,int(z+margin));y1=min(h,int(t+margin));boxes=[];valid=True
   for c in r['boxes']:
    u,v,s,e=c;inter=max(0,min(s,x1)-max(u,x0))*max(0,min(e,y1)-max(v,y0))
    if inter==0:continue
    if u<x0 or v<y0 or s>x1 or e>y1:valid=False;break
    boxes.append([u-x0,v-y0,s-x0,e-y0])
   if not valid or not boxes:continue
   crop=f[y0:y1,x0:x1];sha=hashlib.sha256(crop.tobytes()).hexdigest()
   if sha in hashes:continue
   hashes.add(sha);name=f'context_{len(crops):03d}.jpg';p=out/'train/images'/name;label=out/'train/labels'/Path(name).with_suffix('.txt');cv2.imwrite(str(p),crop);ch,cw=crop.shape[:2]
   label.write_text(''.join(f'0 {(u+s)/2/cw:.8f} {(v+e)/2/ch:.8f} {(s-u)/cw:.8f} {(e-v)/ch:.8f}\n' for u,v,s,e in boxes));crops.append(dict(path=str(p),label=str(label),split='train',origin='actual_context_crop',parent=r['path'],crop_xyxy=[x0,y0,x1,y1],source_group=r['source_group'],sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
   if len(crops)>=64:break
  if len(crops)>=64:break
 if len(crops)>=64:break
allrows=rows+crops
for split in ['train','val','test']:(out/f'{split}.txt').write_text(''.join(r['path']+'\n' for r in allrows if r['split']==split))
assert (out/'val.txt').read_text()==(base/'val.txt').read_text() and (out/'test.txt').read_text()==(base/'test.txt').read_text()
(out/'dataset.yaml').write_text(yaml.safe_dump(dict(path=str(out),train='train.txt',val='val.txt',test='test.txt',names={0:'forklift'})))
(out/'manifest.json').write_text(json.dumps(allrows,ensure_ascii=False,indent=2));summary=dict(original_training_kept=626,new_context_crops=len(crops),training=626+len(crops),val=99,test=61,new_independent_photos=0,labels_modified=False,partial_other_boxes_rejected=True);(out/'preparation.json').write_text(json.dumps(summary,indent=2));print(summary)
