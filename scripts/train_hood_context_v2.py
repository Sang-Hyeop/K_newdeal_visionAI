"""One context-crop experiment, preserving v1 and all original train/eval files."""
from pathlib import Path
import os,json,random,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
for key,folder in [('YOLO_CONFIG_DIR','yolo'),('MPLCONFIGDIR','matplotlib'),('XDG_CACHE_HOME','cache')]:os.environ.setdefault(key,str(ROOT/'outputs/runtime'/folder))
os.environ.setdefault('OMP_NUM_THREADS','4')
import cv2,yaml,torch
from ultralytics import YOLO

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def labels(p):return [list(map(float,line.split()))for line in p.read_text().splitlines()if line.strip()]
def row_iou(a,b):
 def xy(q):c,x,y,w,h=q;return [x-w/2,y-h/2,x+w/2,y+h/2]
 p=xy(a);q=xy(b);inter=max(0,min(p[2],q[2])-max(p[0],q[0]))*max(0,min(p[3],q[3])-max(p[1],q[1]));return inter/max(1e-12,a[3]*a[4]+b[3]*b[4]-inter)
def conflicting(rows):return any(a[0]!=b[0] and row_iou(a,b)>=.8 for i,a in enumerate(rows)for b in rows[i+1:])
def clean_rows(rows):
 result=[]
 for row in rows:
  if not any(row[0]==old[0]and row_iou(row,old)>=.98 for old in result):result.append(row)
 return result

def crop_example(image_path,label_path,target,destination,name):
 im=cv2.imread(str(image_path));h,w=im.shape[:2];c,x,y,bw,bh=target;x*=w;y*=h;bw*=w;bh*=h;pad=.25*max(bw,bh);left=max(0,int(x-bw/2-pad));top=max(0,int(y-bh/2-pad));right=min(w,int(x+bw/2+pad));bottom=min(h,int(y+bh/2+pad));cw=right-left;ch=bottom-top
 rows=[]
 for cls,xx,yy,ww,hh in clean_rows(labels(label_path)):
  x1=(xx-ww/2)*w;y1=(yy-hh/2)*h;x2=(xx+ww/2)*w;y2=(yy+hh/2)*h;a=max(left,x1);b=max(top,y1);d=min(right,x2);e=min(bottom,y2)
  if d<=a or e<=b:continue
  # Do not turn partially visible labelled people into background negatives.
  if (d-a)*(e-b)/max(1,(x2-x1)*(y2-y1))<.2:continue
  rows.append(f'{int(cls)} {(a+d-2*left)/(2*cw):.8f} {(b+e-2*top)/(2*ch):.8f} {(d-a)/cw:.8f} {(e-b)/ch:.8f}')
 if not rows:raise ValueError('Empty target crop')
 ip=destination/'images'/(name+'.jpg');lp=destination/'labels'/(name+'.txt');assert cv2.imwrite(str(ip),im[top:bottom,left:right]);lp.write_text('\n'.join(rows)+'\n')
 return {'image':str(ip.relative_to(ROOT)),'source_image':str(image_path.relative_to(ROOT)),'source_sha256':sha(image_path),'source_label_sha256':sha(label_path),'crop_xyxy':[left,top,right,bottom],'target_class':int(c),'image_sha256':sha(ip),'label_sha256':sha(lp)}
def prepare():
 original=ROOT/'data/reviewed_pilot/hoodie_roboflow_v1';out=ROOT/'data/reviewed_pilot/hoodie_context_v2_clean'
 if out.exists():raise ValueError('Preserve existing experiment dataset')
 out.mkdir(parents=True);records=[];excluded=[];rng=random.Random(20261008)
 for split,full_count,crop_counts in [('train',128,(96,32)),('val',120,(24,24)),('test_context',0,(24,24)),('test_full',100,(0,0))]:
  source_split='test'if split in ['test_context','test_full']else split;source=original/source_split;dest=out/split;(dest/'images').mkdir(parents=True);(dest/'labels').mkdir();positive=[];normal=[]
  for p in sorted((source/'images').glob('*.jpg')):
   lab=source/'labels'/(p.stem+'.txt');rows=labels(lab)
   if conflicting(rows):excluded.append({'split':split,'image':str(p.relative_to(ROOT)),'reason':'same_person_opposite_classes_iou_ge_0.8'});continue
   rows=clean_rows(rows);(positive if any(r[0]==0 for r in rows)else normal).append((p,lab,rows))
  rng.shuffle(positive);rng.shuffle(normal)
  full=positive[:full_count//2]+normal[:full_count-full_count//2]
  if split in ['val','test_full']:full=positive+normal
  for ip,lp,rows in full:
   dst=dest/'images'/('full_'+ip.name);dl=dest/'labels'/('full_'+lp.name);shutil.copy2(ip,dst);dl.write_text('\n'.join(str(int(r[0]))+' '+' '.join(f'{v:.8f}'for v in r[1:])for r in rows)+'\n');records.append({'split':split,'kind':'full','image':str(dst.relative_to(ROOT)),'source_image':str(ip.relative_to(ROOT)),'source_sha256':sha(ip),'source_label_sha256':sha(lp),'image_sha256':sha(dst),'label_sha256':sha(dl)})
  for cls,n in enumerate(crop_counts):
   pool=[(ip,lp,r)for ip,lp,rows in positive+normal for r in rows if int(r[0])==cls];rng.shuffle(pool)
   if len(pool)<n:raise ValueError('Insufficient crop pool')
   for i,(ip,lp,target)in enumerate(pool[:n]):records.append({'split':split,'kind':'actual_label_context_crop',**crop_example(ip,lp,target,dest,f'crop_{cls}_{i:04d}')})
 config={'path':str(out),'train':'train/images','val':'val/images','test':'test_full/images','nc':2,'names':['hooded_person','normal_person']};(out/'dataset.yaml').write_text(yaml.safe_dump(config));(out/'context_test.yaml').write_text(yaml.safe_dump({**config,'test':'test_context/images'}));(out/'manifest.json').write_text(json.dumps({'source':'Jaydips Workspace Hoodie Detection v1 / CC BY4.0','inference_context_pad':.25,'previous_weights':'models/hoodie_auxiliary_v1/hoodie.pt','scope':'development only; original adjacent source frames may overlap between splits; no demo frames used','excluded_conflicts':excluded,'files':records},indent=2));return out,records

def metrics(result):
 return {'overall':result.results_dict,'per_class':{result.names[int(c)]:{'precision':float(result.box.p[i]),'recall':float(result.box.r[i]),'mAP50':float(result.box.ap50[i])}for i,c in enumerate(result.box.ap_class_index)}}
def main():
 torch.set_num_threads(4);out,records=prepare();initial=ROOT/'models/hoodie_auxiliary_v1/hoodie.pt'
 checkpoint=ROOT/'docs/checkpoints/2026-10-07/hoodie-context-v2';checkpoint.mkdir(parents=True,exist_ok=True);prep={'status':'prepared_for_single_context_experiment','initial_sha256':sha(initial),'counts':{s:sum(r['split']==s for r in records)for s in ['train','val','test_context','test_full']},'manifest_sha256':sha(out/'manifest.json'),'no_demo_training':True};(checkpoint/'pretraining.json').write_text(json.dumps(prep,indent=2));print(json.dumps(prep),flush=True)
 base_full=YOLO(str(initial)).val(data=str(out/'dataset.yaml'),split='test',imgsz=640,device='cpu',workers=0,batch=4,plots=False,verbose=False)
 base_context=YOLO(str(initial)).val(data=str(out/'context_test.yaml'),split='test',imgsz=640,device='cpu',workers=0,batch=4,plots=False,verbose=False)
 model=YOLO(str(initial));model.train(data=str(out/'dataset.yaml'),epochs=4,imgsz=640,batch=4,device='cpu',workers=0,amp=False,freeze=10,optimizer='AdamW',lr0=.0005,warmup_epochs=1,seed=20261008,deterministic=True,mosaic=0,fliplr=.5,scale=.1,translate=.03,patience=4,project=str(ROOT/'outputs/training'),name='hoodie_context_v2_clean',exist_ok=False,plots=True)
 dest=ROOT/'models/hoodie_context_v2';dest.mkdir(parents=True);best=Path(model.trainer.save_dir)/'weights/best.pt';shutil.copy2(best,dest/'hoodie.pt');candidate=YOLO(str(dest/'hoodie.pt'));context=candidate.val(data=str(out/'context_test.yaml'),split='test',device='cpu',workers=0,batch=4,plots=False,verbose=False);full=candidate.val(data=str(out/'dataset.yaml'),split='test',device='cpu',workers=0,batch=4,plots=False,verbose=False)
 report={**prep,'status':'experimental_not_promoted','weights_sha256':sha(dest/'hoodie.pt'),'baseline_original_clean_test':metrics(base_full),'baseline_context_test':metrics(base_context),'candidate_context_test':metrics(context),'candidate_original_test':metrics(full),'epochs':4,'limitations':['development crop test; nearby original frames can overlap splits','demo-video source6 inference test still required','normal_person never means PPE safe']};(dest/'report.json').write_text(json.dumps(report,indent=2));(checkpoint/'training.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
