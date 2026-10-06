"""검수 기록에 따라 파일을 선별하고 현장/원본 그룹을 분리한 시험 데이터 초안 생성."""
from pathlib import Path
from collections import Counter,defaultdict
import json,random,zipfile,shutil,hashlib
import cv2,numpy as np,yaml
ROOT=Path(__file__).resolve().parents[1];AUDIT=ROOT/'data/training_review/full_audit';OUT=ROOT/'data/pilot_v1';OUT.mkdir(exist_ok=True);rng=random.Random(20261006)
ppe=json.loads((AUDIT/'ppe-index.json').read_text())
# contact-sheet 육안 선별 결과. 작은/불명확 객체는 오류 확정 대신 보류한다.
hold_ranges=[(1,3),(22,28),(49,57),(71,72),(75,80),(82,86),(92,118),(123,138),(145,178),(182,183),(189,219),(225,228),(236,237),(250,253),(263,263),(270,272),(275,276),(301,304),(314,314),(317,320),(327,327),(331,347),(349,351),(353,356),(363,378),(380,380)]
hold={i for a,b in hold_ranges for i in range(a,b+1)}
# pHash 및 수평 반전 pHash로 보수적인 유사 원본 그룹 구성. 후보 비교일 뿐 동일 촬영 증명은 아님.
def phash(im):
 gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY);small=cv2.resize(gray,(32,32)).astype(np.float32);dct=cv2.dct(small)[:8,:8];bits=(dct>np.median(dct.flatten()[1:])).flatten();return sum(int(v)<<i for i,v in enumerate(bits))
parents=list(range(len(ppe)))
def find(i):
 while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
 return i
def union(a,b):parents[find(a)]=find(b)
hashes=[];near=[]
for r in ppe:
 im=cv2.imread(r['image']);hashes.append((phash(im),phash(cv2.flip(im,1))))
for i in range(len(ppe)):
 for j in range(i):
  distance=min((a^b).bit_count() for a in hashes[i] for b in hashes[j])
  if ppe[i]['group']==ppe[j]['group'] or distance<=4:
   union(i,j)
   if ppe[i]['split']!=ppe[j]['split']:near.append({'id1':ppe[j]['id'],'id2':ppe[i]['id'],'distance':distance})
grouped=defaultdict(list)
for i,r in enumerate(ppe):grouped[find(i)].append(r)
kept=[];decisions=[]
for gid,items in grouped.items():
 flagged=any(x['id'] in hold or x['issues'] for x in items)
 status='hold_for_relabel_or_distortion_review' if flagged else 'screen_pass_candidate_needs_full_resolution_confirmation'
 for x in items:decisions.append({'id':x['id'],'image':x['image'],'visual_group':gid,'status':status,'directly_flagged':x['id'] in hold,'screening':'all 382 contact-sheet previews inspected; uncertain and distorted candidates held'})
 if not flagged:
  # 기존 증강 사본은 제외하고 시각 그룹당 한 장만 선택
  representative=min(items,key=lambda x:x['id']);kept.append((gid,representative))
rng.shuffle(kept);n=len(kept);nval=max(1,round(n*.15));ntest=max(1,round(n*.15));ppeman=[]
for idx,(gid,r) in enumerate(kept):
 split='val' if idx<nval else 'test' if idx<nval+ntest else 'train'
 for f in ['images','labels']:(OUT/'ppe'/split/f).mkdir(parents=True,exist_ok=True)
 source=Path(r['image']);shutil.copy2(source,OUT/'ppe'/split/'images'/source.name);shutil.copy2(r['label'],OUT/'ppe'/split/'labels'/f'{source.stem}.txt')
 ppeman.append({'id':r['id'],'visual_group':gid,'original_split':r['split'],'split':split,'image':source.name,'training_eligible':False})
(AUDIT/'ppe-review-decisions.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2))
(AUDIT/'ppe-near-duplicate-candidates.json').write_text(json.dumps(near,indent=2))
(OUT/'ppe/manifest.json').write_text(json.dumps(ppeman,ensure_ascii=False,indent=2))
(OUT/'ppe/dataset.yaml').write_text(yaml.safe_dump({'path':str(OUT/'ppe'),'train':'train/images','val':'val/images','test':'test/images','names':{0:'helmeted_head',1:'no_helmet_head'}}))
print('PPE pilot',dict(Counter(r['split'] for r in ppeman)),'visual groups',len(grouped),'near cross-split pairs',len(near),flush=True)
pool=json.loads((AUDIT/'logistics-pool.json').read_text());valsites={'G04','G13','G18'};testsites={'G06','G08','B08'}
BASE=Path('/Users/sanghyeopkim/Downloads/121.물류창고 내 작업 안전 데이터');imagezip=next(BASE.rglob('TS_07_*.zip'))
lman=[];resolution_mismatches=[]
# 이번 스크립트가 만든 미완성 물류 사본만 재생성한다.
if (OUT/"logistics").exists():shutil.rmtree(OUT/"logistics")
with zipfile.ZipFile(imagezip) as z:
 index={Path(n).stem:n for n in z.namelist() if n.endswith('.jpg')}
 for split,target in [('train',320),('val',64),('test',64)]:
  candidates=[r for r in pool if not r['issues'] and ('val' if r['site'] in valsites else 'test' if r['site'] in testsites else 'train')==split and r['stem'] in index]
  rng.shuffle(candidates);groups=Counter();lastframes=defaultdict(list);picked=[]
  quotas={'people_outside_forklift':round(target*.4),'people_overlap_forklift':round(target*.3),'forklift_only':round(target*.2),'person_only':round(target*.05),'background':round(target*.05)}
  counts=Counter()
  for phase in [0,1]:
   for r in candidates:
    if len(picked)>=target:break
    if groups[r['group']]>=2 or r['stem'] in {x['stem'] for x in picked}:continue
    frame=int(r['stem'].rsplit('_',1)[-1])
    if any(abs(frame-f)<30 for f in lastframes[r['group']]):continue
    if phase==0 and counts[r['category']]>=quotas[r['category']]:continue
    picked.append(r);groups[r['group']]+=1;lastframes[r['group']].append(frame);counts[r['category']]+=1
  for folder in ['images','labels']:(OUT/'logistics'/split/folder).mkdir(parents=True,exist_ok=True)
  for r in picked:
   raw=z.read(index[r['stem']]);im=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
   if im is None:raise RuntimeError(r['stem'])
   h,w=im.shape[:2]
   if [w,h]!=r['resolution']:
    resolution_mismatches.append({'stem':r['stem'],'metadata_resolution':r['resolution'],'decoded_resolution':[w,h],'status':'held_no_coordinate_assumption'});continue
   (OUT/'logistics'/split/'images'/f"{r['stem']}.jpg").write_bytes(raw);lines=[]
   for c,x,y,bw,bh in r['boxes']:lines.append(f'{c} {(x+bw/2)/w:.6f} {(y+bh/2)/h:.6f} {bw/w:.6f} {bh/h:.6f}')
   (OUT/'logistics'/split/'labels'/f"{r['stem']}.txt").write_text('\n'.join(lines)+('\n' if lines else ''))
   lman.append({**r,'split':split,'source_zip':str(imagezip),'image_member':index[r['stem']],'training_eligible':False})
  actual=[r for r in lman if r['split']==split];print('logistics',split,len(actual),dict(Counter(r['category'] for r in actual)),flush=True)
(OUT/'logistics/manifest.json').write_text(json.dumps(lman,ensure_ascii=False,indent=2))
(OUT/'logistics/dataset.yaml').write_text(yaml.safe_dump({'path':str(OUT/'logistics'),'train':'train/images','val':'val/images','test':'test/images','names':{0:'person',1:'forklift'}}))
for key in ['site','group']:
 sets={s:{r[key] for r in lman if r['split']==s} for s in ['train','val','test']};assert not sets['train']&sets['val'] and not sets['train']&sets['test'] and not sets['val']&sets['test']
summary={'status':'pilot_draft_not_training_approved','ppe':dict(Counter(r['split'] for r in ppeman)),'ppe_groups':len(grouped),'ppe_screening':dict(Counter(x['status'] for x in decisions)),'cross_split_near_duplicate_pairs':len(near),'logistics':dict(Counter(r['split'] for r in lman)),'logistics_split_sites':{s:sorted({r['site'] for r in lman if r['split']==s}) for s in ['train','val','test']},'logistics_site_and_video_overlap':0,'resolution_mismatches':resolution_mismatches,'notes':['PPE contact-sheet screen only; verify selected candidates at original resolution before training.','pHash groups are conservative near-duplicate candidates, not provenance proof.','Logistics draft count reflects skipped resolution mismatches; visual QA still needed.','Selected site count may be below all 25 sites when some candidates have no target class.','Original test22 used for previous baseline; new pilot test is not untouched final benchmark.','Six demo videos not included.']}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False),flush=True)
