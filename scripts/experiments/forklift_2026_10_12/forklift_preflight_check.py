from pathlib import Path
import json,hashlib,unicodedata,csv,collections,random,cv2,numpy as np
w=Path('/Users/sanghyeopkim/Desktop/workspace');s=Path('/Users/sanghyeopkim/Desktop/cvat_forklift_merged_4_tasks');d=w/'data/reviewed_pilot/cvat_forklift_merged_4_tasks';out=w/'outputs/diagnostics/forklift_preflight_2026-10-12';out.mkdir(parents=True,exist_ok=True);norm=lambda x:unicodedata.normalize('NFC',x)
index={norm(p.name):p for p in(d/'images/train').iterdir()if p.suffix.lower()in{'.jpg','.png','.jpeg'}};labs={norm(p.name):p for p in(d/'labels/train').glob('*.txt')};source_diff=[]
for folder in ['images/train','labels/train']:
 dest=index if folder.startswith('images')else labs
 for p in(s/folder).iterdir():
  if p.name=='.DS_Store' or not p.is_file():continue
  q=dest.get(norm(p.name))
  if not q or p.read_bytes()!=q.read_bytes():source_diff.append(str(p))
assert not source_diff,source_diff
sources={norm(Path(r['image']).name):r for r in csv.DictReader((w/'data/label_review/cctv_forklift_frames_140/source_manifest.csv').open(encoding='utf-8-sig'))};manifest=[];errors=[];hashes=collections.defaultdict(list)
for name,image in index.items():
 label=labs[Path(name).stem+'.txt'];frame=cv2.imread(str(image));assert frame is not None;h,ww=frame.shape[:2];boxes=[]
 for line in label.read_text().splitlines():
  v=line.split();assert len(v)==5 and v[0]=='0';x,y,bw,bh=map(float,v[1:]);assert bw>0 and bh>0 and all(np.isfinite([x,y,bw,bh]));assert x-bw/2>=-1e-5 and y-bh/2>=-1e-5 and x+bw/2<=1+1e-5 and y+bh/2<=1+1e-5;boxes.append([(x-bw/2)*ww,(y-bh/2)*h,(x+bw/2)*ww,(y+bh/2)*h])
 raw=name.split('_',2)[2];source=sources.get(raw);group=source['source_video']if source else 'unmapped_screenshots_train_only';existing=not source or source['same_video_as_existing_training'].lower()=='true';sha=hashlib.sha256(image.read_bytes()).hexdigest();hashes[sha].append(name)
 manifest.append({'image':name,'path':str(image),'label':str(label),'width':ww,'height':h,'boxes':boxes,'source_group':group,'train_only':existing,'kind':source['source']if source else 'screenshot','sha256':sha})
assert len(manifest)==155 and sum(len(r['boxes'])for r in manifest)==190;assert not any(len(v)>1 for v in hashes.values())
# Split only new-source groups; known reused sequences and unmapped screenshots stay in train.
groups=collections.defaultdict(list)
for r in manifest:groups[r['source_group']].append(r)
new=sorted(g for g,rows in groups.items()if not any(r['train_only']for r in rows));random.Random(20261012).shuffle(new);parts={g:'train'for g in groups}
for split,segment in [('val',new[:max(1,len(new)//10)]),('test',new[max(1,len(new)//10):2*max(1,len(new)//10)])]:
 for g in segment:parts[g]=split
prep=w/'data/reviewed_pilot/forklift_cvat_prepared_v1';prep.mkdir(exist_ok=True)
for split in ['train','val','test']:(prep/f'{split}.txt').write_text('\n'.join(r['path']for r in manifest if parts[r['source_group']]==split)+'\n')
(prep/'dataset.yaml').write_text(f'path: {prep}\ntrain: train.txt\nval: val.txt\ntest: test.txt\nnames:\n  0: forklift\n')
for r in manifest:r['split']=parts[r['source_group']]
(prep/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
# Representative cases: each task, screenshot, multiple vehicles, large and small boxes.
chosen=[]
def add(r):
 if r not in chosen:chosen.append(r)
for tid in ['2661266','2661311','2661357','2661383']:
 rows=[r for r in manifest if r['image'].startswith('task_'+tid+'_')];add(max(rows,key=lambda r:len(r['boxes'])));screens=[r for r in rows if r['kind']=='screenshot'];
 if screens:add(screens[0])
for r in sorted(manifest,key=lambda r:max((b[2]-b[0])*(b[3]-b[1])/(r['width']*r['height'])for b in r['boxes']),reverse=True)[:4]:add(r)
for r in sorted(manifest,key=lambda r:min((b[2]-b[0])*(b[3]-b[1])for b in r['boxes']))[:4]:add(r)
chosen=chosen[:16];tiles=[]
for i,r in enumerate(chosen):
 f=cv2.imread(r['path'])
 for b in r['boxes']:
  a,y,c,e=map(int,b);cv2.rectangle(f,(a,y),(c,e),(0,200,255),max(2,r['width']//600))
 f=cv2.resize(f,(480,270));cv2.rectangle(f,(0,0),(480,27),(20,20,20),-1);cv2.putText(f,f"{i+1}: task{r['image'].split('_')[1]} / {len(r['boxes'])} boxes",(6,19),0,.5,(255,255,255),1);tiles.append(f)
while len(tiles)%4:tiles.append(np.zeros((270,480,3),np.uint8))
cv2.imwrite(str(out/'representative_review.jpg'),np.vstack([np.hstack(tiles[i:i+4])for i in range(0,len(tiles),4)]));(out/'visual_samples.json').write_text(json.dumps(chosen,ensure_ascii=False,indent=2))
report={'images':155,'labels':155,'boxes':190,'desktop_workspace_identical':True,'format_errors':[],'duplicate_images':0,'split_counts':dict(collections.Counter(r['split']for r in manifest)),'source_groups':len(groups),'visual_sample_count':len(chosen),'held_out_unlabeled':2,'training_started':False,'class_strategy':'Single forklift specialist; do not mix missing-person labels into person/forklift training','split_scope':'Source-video separated development split; same site and camera may recur'};(out/'preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(report)
