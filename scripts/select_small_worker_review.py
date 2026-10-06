"""Select unseen source groups with small workers; outputs are unapproved drafts."""
from pathlib import Path
import json, zipfile
from collections import Counter
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
def main():
    out = ROOT/'data/training_review/small_workers_v1'
    if out.exists():
        raise SystemExit(f'Existing output protected: {out}')
    pool = json.loads((ROOT/'data/training_review/full_audit/logistics-pool.json').read_text())
    prior = json.loads((ROOT/'data/reviewed_pilot/expansion_v3/logistics/manifest.json').read_text())
    used = {r['group'] for r in prior}
    vals, tests = {'G04','G13','G18'}, {'G06','G08','B08'}
    def split(r):
        return 'val' if r['site'] in vals else 'test' if r['site'] in tests else 'train'
    archive = next(Path('/Users/sanghyeopkim/Downloads/121.물류창고 내 작업 안전 데이터').rglob('TS_07_*.zip'))
    rows, held, groups, sites = [], [], set(), Counter()
    out.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        index = {Path(n).stem:n for n in z.namelist() if n.endswith('.jpg')}
        for s,target in [('train',10),('val',3),('test',3)]:
            candidates = [r for r in pool if not r['issues'] and r['group'] not in used and split(r)==s
                          and any(b[0]==1 for b in r['boxes']) and any(b[0]==0 for b in r['boxes'])
                          and 60 <= max(b[4] for b in r['boxes'] if b[0]==0) <= 200]
            candidates.sort(key=lambda r:(-sum(b[0]==0 for b in r['boxes']),max(b[4] for b in r['boxes'] if b[0]==0),r['stem']))
            count=0
            for r in candidates:
                if r['group'] in groups or sites[r['site']]>=2 or r['stem'] not in index:
                    continue
                raw=z.read(index[r['stem']]); im=cv2.imdecode(np.frombuffer(raw,np.uint8),1)
                if im is None or list(im.shape[:2][::-1])!=r['resolution']:
                    held.append({'stem':r['stem'],'reason':'decode or resolution mismatch'}); continue
                row={**r,'split':s,'review_id':len(rows)+1,'source_zip':str(archive),
                     'image_member':index[r['stem']],'training_eligible':False}
                for c,x,y,w,h in r['boxes']:
                    cv2.rectangle(im,(round(x),round(y)),(round(x+w),round(y+h)),(0,255,0) if c==0 else (0,0,255),3)
                cv2.imwrite(str(out/f'{row["review_id"]:02}.jpg'),cv2.resize(im,(960,540)))
                rows.append(row);groups.add(r['group']);sites[r['site']]+=1;count+=1
                if count==target:break
    (out/'candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    (out/'held.json').write_text(json.dumps(held,ensure_ascii=False,indent=2))
    print('Candidates:',len(rows),'split:',dict(Counter(r['split'] for r in rows)), 'resolution holds:',len(held))
if __name__=='__main__': main()
