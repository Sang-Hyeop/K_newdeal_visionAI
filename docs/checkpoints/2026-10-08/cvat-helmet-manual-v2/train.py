from pathlib import Path
import os,json,hashlib,shutil
os.environ['YOLO_CONFIG_DIR']='/private/tmp/cvat_yolo_config'
import torch
from ultralytics import YOLO
r=Path('/Users/sanghyeopkim/Desktop/workspace');old=r/'data/reviewed_pilot/cvat_helmet_training_v1';dst=r/'data/reviewed_pilot/cvat_helmet_training_v2';run=r/'outputs/training/cvat_helmet_manual_v2';run.mkdir(parents=True,exist_ok=True);torch.set_num_threads(4)
for split in ['train','val','test']:
 for kind in ['images','labels']:(dst/split/kind).mkdir(parents=True,exist_ok=True)
seen={};manifest=[]
for split in ['train','val','test']:
 for p in sorted((old/split/'images').glob('*')):
  if not p.is_file():continue
  h=hashlib.sha256(p.read_bytes()).hexdigest()
  if split=='train' and h in seen:continue
  seen[h]=p.name
  lab=old/split/'labels'/(p.stem+'.txt')
  shutil.copy2(p,dst/split/'images'/p.name);shutil.copy2(lab,dst/split/'labels'/lab.name);manifest.append({'split':split,'name':p.name,'sha256':h})
yaml=dst/'dataset.yaml';yaml.write_text(f'path: {dst}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: helmeted_head\n  1: no_helmet_head\n');(run/'manifest.json').write_text(json.dumps(manifest,indent=2))
weight=r/'models/demo_ppe_failure_context_v3/best.pt';m=YOLO(str(weight));m.train(data=str(yaml),epochs=4,patience=4,batch=4,imgsz=640,device='cpu',workers=0,project=str(run),name='fit',exist_ok=True,optimizer='AdamW',lr0=.0001,lrf=.1,warmup_epochs=1,warmup_bias_lr=0,warmup_momentum=.8,freeze=10,mosaic=0,mixup=0,translate=.05,scale=.2,seed=20261008,plots=False)
print('TRAIN_COMPLETE',flush=True)
