from pathlib import Path
import json,hashlib,yaml
w=Path('/Users/sanghyeopkim/Desktop/workspace');old=w/'data/reviewed_pilot/forklift_far_v4';new=w/'data/reviewed_pilot/forklift_cvat_prepared_v1';out=w/'data/reviewed_pilot/forklift_cvat_combined_v1';out.mkdir(exist_ok=True)
rows=[]
for split in ['train','val','test']:
 for p in sorted((old/split/'images').glob('*')):
  if p.suffix.lower() not in ['.jpg','.png','.jpeg']:continue
  rows.append(dict(path=str(p),label=str(old/split/'labels'/f'{p.stem}.txt'),split=split,origin='existing',sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
for r in json.loads((new/'manifest.json').read_text()):
 if r['training_eligible']:rows.append({**r,'origin':'new_cvat'})
# Existing splits are unchanged; a new exact duplicate must not contaminate a held-out split.
seen={};duplicates=[]
for r in rows:
 if r['sha256'] in seen:
  prev=seen[r['sha256']]
  assert prev['split']==r['split'],f"cross-split duplicate {r['path']}"
  duplicates.append(r);continue
 seen[r['sha256']]=r
assert not duplicates,f'Unexpected duplicates: {len(duplicates)}'
for r in rows:
 p=Path(r['path']);label=Path(r['label']);assert label.is_file()
 inferred=Path(str(p.parent).replace('/images','/labels'))/f'{p.stem}.txt';assert inferred==label
 for line in label.read_text().splitlines():
  parts=line.split();assert len(parts)==5 and parts[0]=='0'
for s in ['train','val','test']:(out/f'{s}.txt').write_text(''.join(r['path']+'\n' for r in rows if r['split']==s))
(out/'dataset.yaml').write_text(yaml.safe_dump(dict(path=str(out),train='train.txt',val='val.txt',test='test.txt',names={0:'forklift'})))
(out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
summary=dict(total=len(rows),splits={s:sum(r['split']==s for r in rows) for s in ['train','val','test']},origins={s:sum(r['origin']==s for r in rows) for s in ['existing','new_cvat']},duplicate_files=0,existing_training_includes_context_crops=True,independent_site_validation=False)
(out/'preparation.json').write_text(json.dumps(summary,indent=2));print(summary)
