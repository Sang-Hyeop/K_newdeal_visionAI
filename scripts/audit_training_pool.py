"""safety 환경에서 실행. 전체 PPE 구조 검사/검수판과 물류 후보 인덱스를 생성."""
from pathlib import Path
from collections import Counter,defaultdict
import json,zipfile,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/training_review/full_audit';OUT.mkdir(parents=True,exist_ok=True)
PPE=next(Path('/Users/sanghyeopkim/Desktop').glob('*/시선_팀프로젝트/data/ppe'))
records=[]
for split in ['train','valid','test']:
 for p in sorted((PPE/split/'images').glob('*.jpg')):
  im=cv2.imread(str(p));label=PPE/split/'labels'/f'{p.stem}.txt';issues=[];boxes=[]
  if im is None:issues.append('decode_failed')
  if not label.exists():issues.append('missing_label')
  if im is not None and label.exists():
   h,w=im.shape[:2]
   for line in label.read_text().splitlines():
    try:
     cls,x,y,bw,bh=map(float,line.split());assert cls in (0,1) and np.isfinite([x,y,bw,bh]).all() and bw>0 and bh>0
     if x-bw/2 < -1e-5 or y-bh/2 < -1e-5 or x+bw/2>1+1e-5 or y+bh/2>1+1e-5:issues.append('box_outside_image')
     boxes.append([int(cls),(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h])
    except Exception:issues.append('invalid_label_row')
  records.append(dict(id=len(records)+1,image=str(p),label=str(label),split=split,group=p.stem.split('.rf.')[0],boxes=boxes,issues=issues))
for start in range(0,len(records),24):
 batch=records[start:start+24];canvas=np.full((6*350,4*340,3),245,np.uint8)
 for index,r in enumerate(batch):
  im=cv2.imread(r['image']);h,w=im.shape[:2]
  for c,x1,y1,x2,y2 in r['boxes']:cv2.rectangle(im,(round(x1),round(y1)),(round(x2),round(y2)),(0,220,255) if c==0 else (255,140,0),2)
  s=min(320/w,320/h);im=cv2.resize(im,(round(w*s),round(h*s)));x=index%4*340;y=index//4*350;canvas[y+25:y+25+im.shape[0],x:x+im.shape[1]]=im
  cv2.putText(canvas,f"P{r['id']:03} {r['split']} labels={len(r['boxes'])}",(x+3,y+18),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,0,0),1)
 cv2.imwrite(str(OUT/f'ppe_page_{start//24+1:02}.jpg'),canvas)
(OUT/'ppe-index.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print('PPE',len(records),'images',len(set(r['group'] for r in records)),'source-name groups',Counter(i for r in records for i in r['issues']),flush=True)
BASE=Path('/Users/sanghyeopkim/Downloads/121.물류창고 내 작업 안전 데이터');labelzip=next(BASE.rglob('TL_07_*.zip'))
pool=[];site=Counter();categories=Counter()
with zipfile.ZipFile(labelzip) as z:
 entries=[n for n in z.namelist() if n.endswith('.json')]
 for i,n in enumerate(entries):
  d=json.loads(z.read(n));raw=d['Raw data Info.'];anns=d['Learning data info.']['annotation'];targets=[];bad=[]
  w,h=raw['resolution']
  for a in anns:
   if a['class_id'] not in ('WO-01','WO-02','WO-04') or a['type']!='box':continue
   coords=a['coord']
   if len(coords)!=4 or not np.isfinite(coords).all() or coords[2]<=0 or coords[3]<=0:bad.append('invalid_box');continue
   x,y,bw,bh=coords
   if x<-.01 or y<-.01 or x+bw>w+.01 or y+bh>h+.01:bad.append('outside_box')
   targets.append([1 if a['class_id']=='WO-04' else 0,*coords])
  people=[b for b in targets if b[0]==0];forks=[b for b in targets if b[0]==1]
  # 위치 겹침은 운전자 여부의 정답이 아니라 샘플 다양성 확보용 proxy다.
  outside=any(not any(f[1]<=p[1]+p[3]/2<=f[1]+f[3] and f[2]<=p[2]+p[4]/2<=f[2]+f[4] for f in forks) for p in people)
  category='people_outside_forklift' if people and forks and outside else 'people_overlap_forklift' if people and forks else 'forklift_only' if forks else 'person_only' if people else 'background'
  row=dict(stem=d['Source data Info.']['source_data_ID'],member=n,group=raw['raw_data_ID'],site=raw['location_ID'],resolution=[w,h],boxes=targets,category=category,issues=bad)
  pool.append(row);site[row['site']]+=1;categories[category]+=1
  if (i+1)%20000==0:print('logistics indexed',i+1,flush=True)
(OUT/'logistics-pool.json').write_text(json.dumps(pool,ensure_ascii=False))
(OUT/'logistics-summary.json').write_text(json.dumps({'label_zip':str(labelzip),'images':len(pool),'sites':dict(site),'categories':dict(categories),'groups':len(set(r['group'] for r in pool)),'invalid_candidate_rows':sum(bool(r['issues']) for r in pool)},ensure_ascii=False,indent=2))
print('logistics',len(pool),'sites',dict(site),'categories',dict(categories),flush=True)
