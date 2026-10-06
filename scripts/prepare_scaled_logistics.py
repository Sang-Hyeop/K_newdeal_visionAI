"""Build a larger source-labelled draft; sampled review gates training permission."""
from pathlib import Path
from collections import defaultdict,Counter
import json,zipfile,hashlib,random,cv2,numpy as np
from PIL import Image
from io import BytesIO
ROOT=Path(__file__).resolve().parents[1]

def main():
 out=ROOT/'data/reviewed_pilot/logistics_scaled_v1';review=ROOT/'data/training_review/scaled_v1'
 if out.exists() or review.exists():raise SystemExit('Existing outputs protected')
 p07=json.load(open(ROOT/'data/training_review/full_audit/logistics-pool.json'));p04=json.load(open(ROOT/'outputs/data-audit/full_scan_20261006/logistics04_pool.json'));old=json.load(open(ROOT/'data/reviewed_pilot/logistics_error_focus_v1/manifest.json'));used={r.get('group') for r in old}
 candidates=json.load(open(ROOT/'data/training_review/train_archives_v1/candidates.json'));blocked={r['group'] for r in candidates if r['review_id'] in [14,19,77,112,116]};src=candidates[0];sources={'04':src['source_zip'],'07':next(r['source_zip'] for r in candidates if r['source_kind']=='07')}
 vals={'G04','G13','G18'};tests={'G06','G08','B08'};groups=defaultdict(list)
 for kind,pool in [('07',p07),('04',p04)]:
  for r in pool:
   split='val' if r['site'] in vals else 'test' if r['site'] in tests else 'train'
   if r['issues'] or not r['boxes'] or r['group'] in blocked or (split!='train' and r['group'] in used):continue
   groups[(split,kind,r['group'])].append({**r,'split':split,'source_kind':kind})
 # Round-robin sites prevents one large factory from taking the whole quota.
 selected=[]
 for split in ['train','val','test']:
  for kind,target in [('07',160 if split=='train' else 20),('04',50 if split=='train' else 10)]:
   sites=defaultdict(list)
   for (s,k,g),rows in groups.items():
    if s==split and k==kind:sites[rows[0]['site']].append(rows)
   for rows in sites.values():rows.sort(key=lambda a:(-any(x.get('category')=='people_outside_forklift' for x in a),hashlib.sha256(a[0]['group'].encode()).hexdigest()))
   chosen=[]
   while len(chosen)<target and any(sites.values()):
    for site in sorted(sites):
     if sites[site] and len(chosen)<target:chosen.append(sites[site].pop(0))
   for rows in chosen:
    # Spread through the source sequence, rather than adjacent frames.
    rows.sort(key=lambda r:r['stem']);indices=sorted({round((len(rows)-1)*q) for q in [.15,.5,.85]});selected.extend(rows[i] for i in indices)
 out.mkdir(parents=True);review.mkdir(parents=True);archives={k:zipfile.ZipFile(v) for k,v in sources.items()};indices={k:{Path(n).stem:n for n in z.namelist() if n.endswith('.jpg')} for k,z in archives.items()};manifest=[];holds=[];decoded={}
 try:
  for row in selected:
   kind=row['source_kind'];member=indices[kind].get(row['stem'])
   if not member:holds.append({'stem':row['stem'],'reason':'missing image member'});continue
   raw=archives[kind].read(member)
   try:
    with Image.open(BytesIO(raw)) as integrity_image: integrity_image.load()
   except (OSError,ValueError) as exc:
    holds.append({'stem':row['stem'],'reason':'strict JPEG decode failed','error':str(exc)});continue
   im=cv2.imdecode(np.frombuffer(raw,np.uint8),1)
   if im is None or list(im.shape[:2][::-1])!=row['resolution']:holds.append({'stem':row['stem'],'reason':'image/label resolution mismatch'});continue
   pixelsha=hashlib.sha256(im.tobytes()).hexdigest()
   if pixelsha in decoded:holds.append({'stem':row['stem'],'reason':'exact pixel duplicate','previous':decoded[pixelsha]});continue
   decoded[pixelsha]=row['stem'];h,w=im.shape[:2];split=row['split'];stem='source'+kind+'_'+row['stem'];(out/split/'images').mkdir(parents=True,exist_ok=True);(out/split/'labels').mkdir(parents=True,exist_ok=True);(out/split/'images'/f'{stem}.jpg').write_bytes(raw);lines=[]
   for c,x,y,bw,bh in row['boxes']:
    assert c in [0,1] and min(x,y)>=0 and min(bw,bh)>0 and x+bw<=w+.01 and y+bh<=h+.01;lines.append(f'{c} {(x+bw/2)/w:.8f} {(y+bh/2)/h:.8f} {bw/w:.8f} {bh/h:.8f}')
   (out/split/'labels'/f'{stem}.txt').write_text('\n'.join(lines)+'\n');manifest.append({**row,'stem':stem,'image':stem+'.jpg','source_zip':sources[kind],'image_member':member,'source_image_sha256':hashlib.sha256(raw).hexdigest(),'pixel_sha256':pixelsha,'training_eligible':False,'qa_status':'source_labels_structure_decode_checked_pending_sample_review'})
 finally:
  for z in archives.values():z.close()
 # Diverse reproducible review sample, first per group and across category/site/split.
 sample=[]
 for split,target in [('train',48),('val',12),('test',12)]:
  available=[r for r in manifest if r['split']==split];rng=random.Random(20261006);rng.shuffle(available);seen=set()
  for r in available:
   if r['group'] in seen:continue
   sample.append(r);seen.add(r['group'])
   if len(seen)==target:break
 for j,row in enumerate(sample,1):
  im=cv2.imread(str(out/row['split']/'images'/row['image']));h,w=im.shape[:2]
  for c,x,y,bw,bh in row['boxes']:cv2.rectangle(im,(round(x),round(y)),(round(x+bw),round(y+bh)),(0,255,0) if c==0 else (0,0,255),3)
  canvas=cv2.resize(im,(960,540));cv2.putText(canvas,f"S{j:02} {row['split']} {row['site']} source{row['source_kind']}",(10,25),0,.7,(255,255,255),2);cv2.imwrite(str(review/f'{j:02}.jpg'),canvas);row['sample_review_id']=j
 for start in range(0,len(sample),6):
  canvas=np.full((864,1024,3),245,np.uint8)
  for j,row in enumerate(sample[start:start+6]):
   im=cv2.imread(str(review/f"{row['sample_review_id']:02}.jpg"));x=j%2*512;y=j//2*288;canvas[y:y+288,x:x+512]=cv2.resize(im,(512,288))
  cv2.imwrite(str(review/f'page_{start//6+1:02}.jpg'),canvas)
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));(out/'dataset.yaml').write_text(f'path: {out}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: person\n  1: forklift\n');(review/'sample.json').write_text(json.dumps(sample,ensure_ascii=False,indent=2));(review/'holds.json').write_text(json.dumps(holds,ensure_ascii=False,indent=2));report={'counts':dict(Counter(r['split'] for r in manifest)),'groups':{s:len({r['group'] for r in manifest if r['split']==s}) for s in ['train','val','test']},'holds':len(holds),'sample_count':len(sample),'status':'draft_not_training_eligible','source_annotations_used':True,'demo_frames_added':0};(review/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
