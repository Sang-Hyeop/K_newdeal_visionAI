from pathlib import Path
import shutil,json,hashlib,os
os.environ['YOLO_CONFIG_DIR']='/private/tmp/cvat_yolo_config'
import torch
from ultralytics import YOLO
root=Path('/Users/sanghyeopkim/Desktop/workspace');src=root/'data/reviewed_pilot/cvat_helmet_merged';dst=root/'data/reviewed_pilot/cvat_helmet_training_v1';run=root/'outputs/training/cvat_helmet_manual_v1';run.mkdir(parents=True,exist_ok=True)
manifest=[]
for p in sorted((src/'images/train').glob('*.jpg')):
 n=p.stem
 if 'video_00259' in n or 'video_00261' in n:split='hold'
 elif 'video_00260' in n or 'SU_6_tr4_' in n:split='val'
 elif 'video_00276' in n or 'SU_6_tr12_' in n:split='test'
 else:split='train'
 manifest.append({'image':p.name,'split':split})
 if split=='hold':continue
 for kind,source in [('images',p),('labels',src/'labels/train'/(n+'.txt'))]:
  target=dst/split/kind/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
# Replay only previous train images; reserve its pre-existing test as regression check.
old=root/'data/reviewed_pilot/ppe_color_expansion_v3'
for p in (old/'train/images').glob('*'):
 if not p.is_file():continue
 for kind,source in [('images',p),('labels',old/'train/labels'/(p.stem+'.txt'))]:
  if source.exists():shutil.copy2(source,dst/'train'/kind/('replay_'+source.name))
yaml=dst/'dataset.yaml';yaml.write_text(f'path: {dst}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: helmeted_head\n  1: no_helmet_head\n')
(run/'split_manifest.json').write_text(json.dumps(manifest,indent=2));print('SPLIT', {s:sum(x['split']==s for x in manifest) for s in ['train','val','test','hold']},flush=True)
torch.set_num_threads(4)
weight=root/'models/demo_ppe_failure_context_v3/best.pt'
model=YOLO(str(weight))
model.train(data=str(yaml),epochs=6,patience=3,batch=4,imgsz=640,device='cpu',workers=0,project=str(run),name='fit',exist_ok=True,optimizer='AdamW',lr0=.0003,freeze=10,mosaic=0,mixup=0,translate=.05,scale=.2,seed=20261008,plots=False)
report={'scope':'development comparison, source-video disjoint within new manual set; historical exposure not excluded, not independent site generalization','models':{}}
for name,weight in [('baseline',weight),('candidate',run/'fit/weights/best.pt')]:
 m=YOLO(str(weight));entry={'weights':str(weight),'sha256':hashlib.sha256(weight.read_bytes()).hexdigest(),'evaluations':{}}
 for label,data,split in [('manual_holdout',yaml,'test'),('legacy_regression',old/'dataset.yaml','test')]:
  metrics=m.val(data=str(data),split=split,imgsz=640,batch=4,device='cpu',workers=0,plots=False,project=str(run),name=f'{name}_{label}',exist_ok=True,verbose=False)
  entry['evaluations'][label]={'overall':{k:float(v) for k,v in metrics.results_dict.items()},'per_class':{metrics.names[int(c)]:{'precision':float(metrics.box.p[i]),'recall':float(metrics.box.r[i]),'map50':float(metrics.box.ap50[i])} for i,c in enumerate(metrics.box.ap_class_index)}}
 report['models'][name]=entry
(run/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
