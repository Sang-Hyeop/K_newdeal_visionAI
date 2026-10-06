"""Apply visual decisions to an immutable copy of the previous object dataset."""
from pathlib import Path
from collections import Counter, defaultdict
import json, shutil, zipfile, hashlib
import cv2
import yaml
ROOT=Path(__file__).resolve().parents[1]
ACCEPT={2,4,6,7,8,9,10,11,14,16}
def main():
    out=ROOT/'data/reviewed_pilot/logistics_v4'
    if out.exists(): raise SystemExit(f'Existing output protected: {out}')
    rows=json.loads((ROOT/'configs/review/small-workers-v1.json').read_text())
    for row in rows:
        i=row['review_id']; row['training_eligible']=i in ACCEPT
        row['review_method']='960x540 full-frame visual annotation review'
        row['reason']='visible annotations accepted' if i in ACCEPT else 'held: ambiguity, cargo-heavy box or uncertain background labels'
        row['corrected_boxes']=row['boxes']
        if i==3:
            row['reason']='held after second review: partially hidden people behind pallets/tires need closer relabeling'
        if i==6:
            row['corrected_boxes']=[b if b[0]!=1 else [1,710,384,128,204] for b in row['boxes']]
            row['reason']='extended forklift box upward to include visible mast'
    shutil.copytree(ROOT/'data/reviewed_pilot/expansion_v3/logistics',out)
    merged=json.loads((out/'manifest.json').read_text())
    for row in rows:
        row['small_worker_review_id']=row.pop('review_id')
        if not row['training_eligible']:continue
        image=out/row['split']/'images'/(row['stem']+'.jpg')
        assert not image.exists()
        with zipfile.ZipFile(row['source_zip']) as z:image.write_bytes(z.read(row['image_member']))
        im=cv2.imread(str(image)); assert im is not None
        h,w=im.shape[:2]; assert [w,h]==row['resolution']
        lines=[]
        for c,x,y,bw,bh in row['corrected_boxes']:
            assert c in {0,1} and 0<=x<x+bw<=w and 0<=y<y+bh<=h
            lines.append(f'{c} {(x+bw/2)/w:.8f} {(y+bh/2)/h:.8f} {bw/w:.8f} {bh/h:.8f}')
        label=out/row['split']/'labels'/(image.stem+'.txt');label.write_text('\n'.join(lines)+'\n')
        row['image']=image.name;row['image_sha256']=hashlib.sha256(image.read_bytes()).hexdigest()
        row['label_sha256']=hashlib.sha256(label.read_bytes()).hexdigest()
    merged.extend(rows); groups=defaultdict(set); hashes=defaultdict(set); counts=Counter(); instances=Counter()
    for r in merged:
        if r['training_eligible']:groups[r['site']].add(r['split']);groups[r['group']].add(r['split'])
    for s in ['train','val','test']:
        for p in (out/s/'images').glob('*'):
            assert cv2.imread(str(p)) is not None
            label=out/s/'labels'/(p.stem+'.txt');assert label.exists()
            for line in label.read_text().splitlines():
                c,x,y,w,h=map(float,line.split());assert c in {0,1} and w>0 and h>0
                assert -1e-6<=x-w/2<=x+w/2<=1+1e-6 and -1e-6<=y-h/2<=y+h/2<=1+1e-6
                instances[int(c)]+=1
            hashes[hashlib.sha256(p.read_bytes()).hexdigest()].add(s);counts[s]+=1
    assert all(len(v)==1 for v in groups.values()) and all(len(v)==1 for v in hashes.values())
    report={'images':dict(counts),'instances':dict(instances),'cross_split_site_video_overlap':0,'cross_split_exact_duplicates':0,'status':'reviewed_development_dataset'}
    (out/'manifest.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2))
    (out/'dataset.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'train/images','val':'val/images','test':'test/images','names':{0:'person',1:'forklift'}}))
    (out/'expansion-validation.json').unlink(missing_ok=True)
    (out/'validation-v4.json').write_text(json.dumps(report,indent=2))
    print(report)
if __name__=='__main__':main()
