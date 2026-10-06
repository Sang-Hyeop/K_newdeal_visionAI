"""검수 승인한 작은 부분집합과 누락/박스 수정 기록을 별도 사본에 적용."""
from pathlib import Path
from collections import Counter
import json,shutil,yaml,argparse
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'data/pilot_v1/logistics';OUT=ROOT/'data/reviewed_pilot/logistics'
def main():
 global OUT
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT);parser.add_argument('--review-config',type=Path,default=ROOT/'configs/review/logistics-pilot.json');args=parser.parse_args();OUT=args.output.resolve()
 if OUT.exists():raise SystemExit(f'Existing output protected: {OUT}')
 decisions=json.loads(args.review_config.read_text());pool={r['stem']:r for r in json.loads((SRC/'manifest.json').read_text())};manifest=[]
 for d in decisions:
  r=pool[d['stem']];record={**r,**d,'review_method':'960px whole-image review, manual correction in display coordinate scale'}
  if d['training_eligible']:
   w,h=r['resolution'];boxes=[list(b) for b in r['boxes']]
   def mapped(c,b):
    x1,y1,x2,y2=b;return [c,x1*w/960,y1*h/540,(x2-x1)*w/960,(y2-y1)*h/540]
   for kind,b in d['changes'].items():
    if kind=='add_person':boxes.append(mapped(0,b))
    elif kind=='forklift':
     indices=[i for i,bx in enumerate(boxes) if bx[0]==1];assert len(indices)==1;boxes[indices[0]]=mapped(1,b)
    elif kind=='replace_last_person':
     indices=[i for i,bx in enumerate(boxes) if bx[0]==0];boxes[indices[-1]]=mapped(0,b)
   for folder in ['images','labels']:(OUT/r['split']/folder).mkdir(parents=True,exist_ok=True)
   shutil.copy2(SRC/r['split']/'images'/(r['stem']+'.jpg'),OUT/r['split']/'images'/(r['stem']+'.jpg'))
   lines=[]
   for c,x,y,bw,bh in boxes:
    assert bw>0 and bh>0 and x>=0 and y>=0 and x+bw<=w+0.01 and y+bh<=h+0.01
    lines.append(f'{c} {(x+bw/2)/w:.6f} {(y+bh/2)/h:.6f} {bw/w:.6f} {bh/h:.6f}')
   (OUT/r['split']/'labels'/(r['stem']+'.txt')).write_text('\n'.join(lines)+'\n');record['corrected_boxes']=boxes
  manifest.append(record)
 (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 (OUT/'dataset.yaml').write_text(yaml.safe_dump({'path':str(OUT),'train':'train/images','val':'val/images','test':'test/images','names':{0:'person',1:'forklift'}}))
 accepted=[r for r in manifest if r['training_eligible']]
 for key in ['site','group']:
  sets={s:{r[key] for r in accepted if r['split']==s} for s in ['train','val','test']}
  assert not sets['train']&sets['val'] and not sets['train']&sets['test'] and not sets['val']&sets['test']
 print(Counter(r['split'] for r in accepted))
if __name__=='__main__':main()
