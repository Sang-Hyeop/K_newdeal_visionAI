from pathlib import Path
import os,json,hashlib
os.environ['YOLO_CONFIG_DIR']='/private/tmp/cvat_ppe_v5_config'
os.environ['MPLCONFIGDIR']='/private/tmp/cvat_ppe_v5_matplotlib'
import torch
from ultralytics import YOLO
base=Path('/Users/sanghyeopkim/Desktop/workspace'); here=Path('/Users/sanghyeopkim/Documents/Codex/2026-10-08/new-chat-3');dst=here/'work/ppe_training_corrected_v5/dataset';out=here/'outputs/ppe_manual_corrected_v5';yaml=dst/'dataset.yaml'
torch.set_num_threads(4)
weight=base/'models/demo_ppe_failure_context_v3/best.pt'
m=YOLO(str(weight));m.train(data=str(yaml),epochs=8,patience=4,batch=4,imgsz=640,device='cpu',workers=0,project=str(out),name='fit',exist_ok=True,optimizer='AdamW',lr0=.0002,lrf=.1,warmup_epochs=1,warmup_bias_lr=0,warmup_momentum=.8,freeze=10,mosaic=0,mixup=0,translate=.05,scale=.2,seed=20261009,plots=False)
report={'scope':'development comparison, historical training exposure not excluded','models':{}}
for name,w in [('baseline',weight),('previous_full_v4',here/'outputs/ppe_manual_full_v4/fit/weights/best.pt'),('candidate',out/'fit/weights/best.pt')]:
 entry={'weight':str(w),'sha256':hashlib.sha256(w.read_bytes()).hexdigest(),'evaluations':{}};model=YOLO(str(w))
 for label,data in [('legacy_regression',yaml)]:
  met=model.val(data=str(data),split='test',imgsz=640,batch=4,device='cpu',workers=0,plots=False,project=str(out),name=f'{name}_{label}',exist_ok=True,verbose=False)
  entry['evaluations'][label]={'overall':{k:float(v) for k,v in met.results_dict.items()},'classes':{met.names[int(c)]:{'precision':float(met.box.p[i]),'recall':float(met.box.r[i]),'map50':float(met.box.ap50[i])} for i,c in enumerate(met.box.ap_class_index)}}
 report['models'][name]=entry
 (out/'comparison.json').write_text(json.dumps(report,indent=2))
print('COMPLETE',json.dumps(report),flush=True)
