"""Fine-tune PPE from the expanded corpus while preserving source validation/test partitions."""
from pathlib import Path
import json,hashlib,shutil,csv,time
import torch
from ultralytics import YOLO
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 old=ROOT/'data/reviewed_pilot/ppe_head63_finetune';extra=ROOT/'data/annotation_candidates/hard_hat_workers_v5_2026-10-15';data=ROOT/'data/reviewed_pilot/ppe_expanded_1577';out=ROOT/'models/experiments/ppe_expanded_1577';policy=ROOT/'configs/ppe-user-approved-policy-2026-10-15.json';policy_hash=sha(policy);weights=ROOT/'models/ppe_final/ppe_helmet_v6_960.pt'
 if data.exists() or out.exists():raise FileExistsError('Use a new run directory; do not overwrite an existing experiment')
 data.mkdir(parents=True);out.mkdir(parents=True);files=[]
 def add(src,label,split,name,origin,group=None):
  di=data/split/'images';dl=data/split/'labels';di.mkdir(parents=True,exist_ok=True);dl.mkdir(parents=True,exist_ok=True);ip=di/name;lp=dl/(Path(name).stem+'.txt');shutil.copy2(src,ip);shutil.copy2(label,lp);assert sha(src)==sha(ip) and sha(label)==sha(lp)
  files.append(dict(image=str(ip.relative_to(data)),label=str(lp.relative_to(data)),split=split,image_sha256=sha(ip),label_sha256=sha(lp),origin=origin,source_group=group))
 for split in ['train','val','test']:
  for p in sorted((old/split/'images').iterdir()):
   if p.is_file() and not p.name.startswith('.'):add(p,old/split/'labels'/(p.stem+'.txt'),split,p.name,'existing_ppe573_and_development_holdouts')
 m=json.loads((extra/'manifest.json').read_text());assert len(m['items'])==1004
 for a in m['items']:
  split={'train':'train','valid':'val','test':'test'}[a['source_split']];add(extra/a['image'],extra/a['label'],split,Path(a['image']).name,'hard_hat_workers_v5',a['source_group'])
 hashes={s:{a['image_sha256'] for a in files if a['split']==s} for s in ['train','val','test']};assert all(not hashes[a]&hashes[b] for a,b in [('train','val'),('train','test'),('val','test')])
 counts={s:sum(a['split']==s for a in files) for s in hashes}
 assert counts=={'train':1263,'val':218,'test':117}
 for a in files:
  for line in (data/a['label']).read_text().splitlines():
   c,x,y,w,h=map(float,line.split());assert c in (0,1) and w>0 and h>0 and x-w/2>=-1e-6 and y-h/2>=-1e-6 and x+w/2<=1+1e-6 and y+h/2<=1+1e-6
 (data/'dataset.yaml').write_text(f'path: {data}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: helmeted_head\n  1: no_helmet_head\n')
 manifest={'available_expansion_corpus':1577,'including_preexisting_development_holdouts':1598,'counts':counts,'source_split_preserved':True,'exact_hash_cross_split_overlap':0,'limitations':'Public-source splits retained; near-duplicate screening performed during import but semantic/scene independence and historical pretrained exposure not proven. Original 573 development images all stay train. New source val206/test108 never used for gradient updates in this run.','files':files};(data/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 params=dict(data=str(data/'dataset.yaml'),epochs=10,patience=4,imgsz=640,batch=8,device='cpu',workers=0,project=str(out.parent),name=out.name,exist_ok=True,lr0=.0003,lrf=.1,optimizer='AdamW',freeze=10,seed=42,deterministic=True,plots=False,save=True,amp=False,mosaic=.15,close_mosaic=3,mixup=0.,degrees=0.,translate=.05,scale=.15,fliplr=.5,cache=False)
 request={'initial_weights':str(weights),'initial_sha256':sha(weights),'initial_choice':'Original v6; previous head63 experiment was not promoted','policy_sha256':policy_hash,'counts':counts,'params':params,'runtime_promotion':False};(out/'run_request.json').write_text(json.dumps(request,indent=2)+'\n');print('DATA VERIFIED',counts,flush=True)
 torch.set_num_threads(6);started=time.time();YOLO(str(weights)).train(**params);assert sha(policy)==policy_hash
 compare={}
 for label,p in [('baseline',weights),('candidate',out/'weights/best.pt')]:
  val=YOLO(str(p)).val(data=str(data/'dataset.yaml'),split='test',imgsz=960,batch=1,device='cpu',workers=0,plots=False,project=str(out),name='comparison_'+label,exist_ok=True,verbose=False)
  compare[label]={'weights':str(p),'sha256':sha(p),'metrics':{k:float(v) for k,v in val.results_dict.items()},'per_class':{'class_ids':val.box.ap_class_index.tolist(),'precision':val.box.p.tolist(),'recall':val.box.r.tolist(),'mAP50':val.box.ap50.tolist(),'mAP50_95':val.box.ap.tolist()}}
 result={'status':'completed_candidate_not_promoted','counts':counts,'epochs_completed':len(list(csv.DictReader((out/'results.csv').open()))),'elapsed_seconds':time.time()-started,'policy_unchanged':sha(policy)==policy_hash,'policy_sha256':policy_hash,'dataset_manifest_sha256':sha(data/'manifest.json'),'comparison':compare,'weights':{n:{'path':str(out/'weights'/n),'sha256':sha(out/'weights'/n),'bytes':(out/'weights'/n).stat().st_size} for n in ['best.pt','last.pt']},'limitation':'117 development/public-source test images (108 imported source test + 9 existing). Not independent real-site evaluation. Full video comparison still required.'}
 (out/'training_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('COMPLETE',json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
