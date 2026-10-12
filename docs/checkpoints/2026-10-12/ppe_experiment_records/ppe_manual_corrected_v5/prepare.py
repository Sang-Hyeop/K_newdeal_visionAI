from pathlib import Path
import json,unicodedata,math,shutil,hashlib
here=Path('/Users/sanghyeopkim/Documents/Codex/2026-10-08/new-chat-3'); raw=Path('/Users/sanghyeopkim/Desktop/cvat_ppe_merged_4_tasks'); fix=Path('/Users/sanghyeopkim/Desktop/task_2656094_annotations_2026_10_09_02_19_54_ultralytics yolo detection 1.0'); dst=here/'work/ppe_training_corrected_v5/dataset'; out=here/'outputs/ppe_manual_corrected_v5';out.mkdir(exist_ok=True)
norm=lambda s:unicodedata.normalize('NFC',s)
imgs={norm(p.stem):p for p in (raw/'images/train').iterdir() if p.is_file()}; labs={norm(p.stem):p for p in (fix/'labels/train').glob('*.txt')};excluded=json.loads((here/'outputs/ppe_manual_full_v4/data_manifest.json').read_text())['excluded']; expected={norm(Path(x['name']).stem) for x in excluded}
assert set(labs)==expected,(set(labs)-expected,expected-set(labs))
audit=[];errors=[];classes={0:0,1:0}
for key,l in labs.items():
 assert key in imgs,key
 for ln,row in enumerate(l.read_text().splitlines(),1):
  try:
   v=list(map(float,row.split()));assert len(v)==5 and all(math.isfinite(x) for x in v)
   c,x,y,w,h=v;assert c in [0,1] and 0<=x<=1 and 0<=y<=1 and 0<w<=1 and 0<h<=1
   assert x-w/2>=-1e-5 and y-h/2>=-1e-5 and x+w/2<=1.00001 and y+h/2<=1.00001
   classes[int(c)]+=1
  except Exception:errors.append([l.name,ln,row])
 old=raw/'labels/train'/(imgs[key].stem+'.txt');audit.append({'image':imgs[key].name,'corrected_label':str(l),'old_boxes':len(old.read_text().splitlines()),'new_boxes':len(l.read_text().splitlines()),'changed':old.read_text()!=l.read_text()})
assert not errors,errors
# Keep all 490 prior training entries, then restore the 20 omitted images with corrected labels.
prior=here/'work/ppe_training_full_v4/dataset'
for split in ['train','val','test']:
 for kind in ['images','labels']:
  target=dst/split/kind;target.mkdir(parents=True,exist_ok=True)
  for p in (prior/split/kind).iterdir():
   if p.is_file() and p.suffix.lower() in (['.jpg','.jpeg','.png'] if kind=='images' else ['.txt']):shutil.copy2(p,target/p.name)
for key,l in labs.items():
 im=imgs[key];shutil.copy2(im,dst/'train/images'/('new_'+im.name));shutil.copy2(l,dst/'train/labels'/('new_'+im.stem+'.txt'))
counts={s:len(list((dst/s/'images').iterdir())) for s in ['train','val','test']};assert counts['train']==510,counts
trainsha={hashlib.sha256(p.read_bytes()).hexdigest() for p in (dst/'train/images').iterdir()}
for s in ['val','test']:assert not any(hashlib.sha256(p.read_bytes()).hexdigest() in trainsha for p in (dst/s/'images').iterdir())
(dst/'dataset.yaml').write_text(f'path: {dst}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: helmeted_head\n  1: no_helmet_head\n')
report={'counts':counts,'classes_in_corrected_20':classes,'review':audit,'label_policy':'User visually reviewed labels are authoritative. Hood-only heads are no_helmet_head; visible helmet is helmeted_head. Unannotated indistinguishable heads remain unannotated; do not treat these as verified false negatives.','source_images':str(raw),'corrected_labels':str(fix),'previous_training_entries':490,'restored_images':20,'unique_training_image_hashes':len(trainsha),'scope':'All 160 new images included alongside 350 old training entries; previous duplicate replay entries intentionally preserved. Legacy val12/test9 only, not independent-site evaluation.'}
(out/'data_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'counts':counts,'corrected20_boxes':classes,'changed_files':sum(x['changed'] for x in audit)},ensure_ascii=False))
