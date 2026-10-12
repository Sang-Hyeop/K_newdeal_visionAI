from pathlib import Path
import os,json,hashlib,subprocess,sys,traceback,datetime
os.environ['YOLO_CONFIG_DIR']='/private/tmp/cvat_ppe_v6_config'
os.environ['MPLCONFIGDIR']='/private/tmp/cvat_ppe_v6_matplotlib'
import torch
from ultralytics import YOLO
root=Path('/Users/sanghyeopkim/Documents/Codex/2026-10-08/new-chat-3');out=root/'outputs/ppe_manual_to40_v7';work=root/'work/ppe_training_to40_v7';data=root/'work/ppe_training_corrected_v5/dataset/dataset.yaml';base=root/'outputs/ppe_manual_960_v6/fit/weights/last.pt'
status={'state':'training','training_entries':510,'imgsz':960,'additional_epochs':8,'previous_epochs':32,'total_target_epochs':40,'patience':0,'continuation_note':'Weights continued from stripped last.pt; optimizer restarts; not an exact optimizer-state resume.','device':'cpu','previous_model':str(root/'outputs/ppe_manual_960_v6/fit/weights/best.pt'),'policy':'All 160 user-labeled new images included; hood-only=no_helmet_head, visible helmet=helmeted_head; user unobservable unlabeled heads unchanged.','scope':'Development experiment; legacy val12/test9, not independent generalization. Existing deployed model unchanged.'}
def save():
 status['updated_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(out/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
save();torch.set_num_threads(4)
try:
 model=YOLO(str(base));model.train(data=str(data),epochs=8,patience=0,save_period=1,batch=4,imgsz=960,device='cpu',workers=0,project=str(out),name='fit',exist_ok=True,optimizer='AdamW',lr0=.00006,lrf=.1,warmup_epochs=0,warmup_bias_lr=0,warmup_momentum=.8,freeze=10,mosaic=0,mixup=0,translate=.05,scale=.2,seed=20261009,plots=False)
 weight=out/'fit/weights/best.pt';status.update(state='evaluating',weight=str(weight),weight_sha256=hashlib.sha256(weight.read_bytes()).hexdigest());save()
 for name in ['evaluate_fixed.py','compare_video.py']:
  with (work/(name+'.log')).open('w') as log:subprocess.run([sys.executable,str(work/name)],stdout=log,stderr=subprocess.STDOUT,check=True)
 status.update(state='complete_experimental_not_promoted',comparison=str(out/'fixed_comparison.json'),video=str(out/'video7_v6_vs_v7_at_960.mp4'));save();print('PIPELINE_COMPLETE',flush=True)
except BaseException as e:
 status.update(state='failed',error=repr(e));save();traceback.print_exc();raise
