from pathlib import Path
import os,json,re,hashlib,shutil
os.environ['YOLO_CONFIG_DIR']='/private/tmp/cvat_ppe_v3_config'
import torch
from ultralytics import YOLO
base=Path('/Users/sanghyeopkim/Desktop/workspace'); here=Path('/Users/sanghyeopkim/Documents/Codex/2026-10-08/new-chat-3'); dst=here/'work/ppe_training_full_v4/dataset'; out=here/'outputs/ppe_manual_full_v4';out.mkdir(parents=True,exist_ok=True)
records=json.loads((here/'work/ppe_audit/records.json').read_text())
exclude={0:'hood',7:'occluded driver',31:'hood',32:'occluded driver',33:'wrong class',34:'hood',36:'hood',76:'occluded driver',77:'occluded driver',84:'uncertain driver',93:'driver label review',105:'hood',109:'driver label review',116:'hood',117:'hood',134:'missing helmet label',142:'hood',147:'occluded driver',155:'hood',156:'hood'}
def group(n):
 m=re.search(r'video_(\d+)',n)
 if m:return 'NV_'+m[1]
 m=re.search(r'(?:SafeUnsafe_|SU_)(\d+)_tr(\d+)',n)
 if m:return 'SU_'+m[1]+'_'+m[2]
 return 'demo_screenshots' if '2026' in n else n
usable=[r for r in records if r['index'] not in exclude]
groups=sorted(set(group(r['name']) for r in usable if group(r['name'])!='demo_screenshots'))
# Reserve full source videos, including two real factory sources.
nv=[g for g in groups if g.startswith('NV_')]; su=[g for g in groups if g.startswith('SU_')]
val=set(nv[::9]+su[:1]); test=set(nv[4::9]+su[1:2]); test-=val
manifest=[]; seen={}; counts={s:0 for s in ['train','val','test']}
def copy(p,lab,split,origin):
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 # Keep every supplied training image, including previous replay copies.
 seen[h]=split; name=origin+'_'+p.name
 for kind,src in [('images',p),('labels',lab)]:
  target=dst/split/kind/(name if kind=='images' else Path(name).stem+'.txt');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
 counts[split]+=1;manifest.append({'name':name,'source':str(p),'group':group(p.name),'split':split,'sha256':h})
for r in usable:
 p=Path(r['path']);g=group(p.name);split='train';copy(p,p.parents[2]/'labels/train'/(p.stem+'.txt'),split,'new')
old=base/'data/reviewed_pilot/cvat_helmet_training_v1'
for p in sorted((old/'train/images').glob('*')):
 if p.is_file():copy(p,old/'train/labels'/(p.stem+'.txt'),'train','replay')

for split in ['val','test']:
 for p in sorted((base/'data/reviewed_pilot/ppe_color_expansion_v3'/split/'images').glob('*')):
  if p.is_file():copy(p,base/'data/reviewed_pilot/ppe_color_expansion_v3'/split/'labels'/(p.stem+'.txt'),split,'legacy_eval')
yaml=dst/'dataset.yaml';yaml.write_text(f'path: {dst}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: helmeted_head\n  1: no_helmet_head\n')
(out/'data_manifest.json').write_text(json.dumps({'counts':counts,'excluded':[{'name':records[i]['name'],'reason':reason} for i,reason in sorted(exclude.items())],'manifest':manifest,'validation_groups':'legacy only','test_groups':'legacy only','scope':'Development adaptation. All 140 accepted new images and all 350 previous training entries used. Previous duplicate replay entries intentionally preserved at user request; previous model exposure not excluded. Demo screenshots only train; not independent generalization.'},indent=2))
print('DATA_READY',counts,'new',len(usable),'excluded',len(exclude),flush=True)
torch.set_num_threads(4)
weight=base/'models/demo_ppe_failure_context_v3/best.pt'
m=YOLO(str(weight));m.train(data=str(yaml),epochs=8,patience=4,batch=4,imgsz=640,device='cpu',workers=0,project=str(out),name='fit',exist_ok=True,optimizer='AdamW',lr0=.0002,lrf=.1,warmup_epochs=1,warmup_bias_lr=0,warmup_momentum=.8,freeze=10,mosaic=0,mixup=0,translate=.05,scale=.2,seed=20261009,plots=False)
report={'scope':'development comparison, historical training exposure not excluded','models':{}}
for name,w in [('baseline',weight),('candidate',out/'fit/weights/best.pt')]:
 entry={'weight':str(w),'sha256':hashlib.sha256(w.read_bytes()).hexdigest(),'evaluations':{}};model=YOLO(str(w))
 for label,data in [('legacy_regression',yaml)]:
  met=model.val(data=str(data),split='test',imgsz=640,batch=4,device='cpu',workers=0,plots=False,project=str(out),name=f'{name}_{label}',exist_ok=True,verbose=False)
  entry['evaluations'][label]={'overall':{k:float(v) for k,v in met.results_dict.items()},'classes':{met.names[int(c)]:{'precision':float(met.box.p[i]),'recall':float(met.box.r[i]),'map50':float(met.box.ap50[i])} for i,c in enumerate(met.box.ap_class_index)}}
 report['models'][name]=entry
 (out/'comparison.json').write_text(json.dumps(report,indent=2))
print('COMPLETE',json.dumps(report),flush=True)
