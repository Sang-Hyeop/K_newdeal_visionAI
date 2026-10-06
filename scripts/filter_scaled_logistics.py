"""Conservative source-label gate; exclusion is not proof of a missing driver."""
from pathlib import Path
import json, shutil
ROOT=Path(__file__).resolve().parents[1]
def contained(p,f):
 _,x,y,w,h=p;_,a,b,c,d=f
 return max(0,min(x+w,a+c)-max(x,a))*max(0,min(y+h,b+d)-max(y,b))/max(w*h,1)
def main():
 src=ROOT/'data/reviewed_pilot/logistics_scaled_v1'; dst=ROOT/'data/reviewed_pilot/logistics_scaled_filtered_v1'
 if dst.exists(): raise RuntimeError('Refusing to overwrite dataset')
 rows=json.loads((src/'manifest.json').read_text()); samples=json.loads((ROOT/'data/training_review/scaled_v1/sample.json').read_text())
 confirmed={samples[i-1]['group'] for i in (10,11,19,25,42)}
 kept=[]; held=[]
 for r in rows:
  people=[b for b in r['boxes'] if b[0]==0]; forks=[b for b in r['boxes'] if b[0]==1]
  reason='visually_confirmed_missing_driver_in_group' if r['group'] in confirmed else ('potential_driver_label_omission' if any(not any(contained(p,f)>=.8 for p in people) for f in forks) else None)
  if reason: held.append(dict(r,hold_reason=reason)); continue
  split=r['split']; name=r['image']
  for kind,filename in [('images',name),('labels',Path(name).stem+'.txt')]:
   target=dst/split/kind/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/split/kind/filename,target)
  kept.append(dict(r,training_eligible=True,qa_status='structural_and_conservative_source_gate_passed; sample_review_only; not_exhaustively_manual'))
 for a,b in [('train','val'),('train','test'),('val','test')]:
  assert not {r['group'] for r in kept if r['split']==a}&{r['group'] for r in kept if r['split']==b}
 assert len({r['pixel_sha256'] for r in kept})==len(kept)
 (dst/'manifest.json').write_text(json.dumps(kept,ensure_ascii=False,indent=2))
 (dst/'dataset.yaml').write_text(f'path: {dst}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: person\n  1: forklift\n')
 report={'counts':{s:sum(r['split']==s for r in kept) for s in ['train','val','test']},'held':len(held),'confirmed_missing_driver_groups':sorted(confirmed),'gate':'each forklift requires a person box with >=80% of person area contained; conservative exclusion, not proof of omissions','limitations':'765 frames structurally checked; 72 contact-sheet samples reviewed; no exhaustive manual label review; test is development-only; possible selection bias','demo_frames_added':0}
 (dst/'quality_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(dst/'holds.json').write_text(json.dumps(held,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
