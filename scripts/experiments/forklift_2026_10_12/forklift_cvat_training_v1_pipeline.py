from pathlib import Path
import os,json,time,traceback,hashlib
os.environ['OMP_NUM_THREADS']='4';os.environ['MKL_NUM_THREADS']='4';os.environ['YOLO_CONFIG_DIR']='/private/tmp/forklift_yolo_config'
import torch
torch.set_num_threads(4)
from ultralytics import YOLO
w=Path('/Users/sanghyeopkim/Desktop/workspace');data=w/'data/reviewed_pilot/forklift_cvat_combined_v1/dataset.yaml';out=w/'outputs/diagnostics/forklift_cvat_training_v1';out.mkdir(parents=True,exist_ok=True);base=w/'models/forklift_far_v4/best.pt'
def save(name,v):(out/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def status(stage,**kw):
 save('status.json',dict(stage=stage,updated_at=time.strftime('%Y-%m-%d %H:%M:%S'),training_images=626,validation_images=99,test_images=61,epochs=6,**kw));(out/'진행상황.txt').write_text(f'{stage}\n'+json.dumps(kw,ensure_ascii=False,indent=2)+'\n')
def epoch(trainer):status('training',epoch=int(trainer.epoch)+1,total_epochs=6)
def evaluate(weights,name):
 model=YOLO(str(weights));results={}
 for group,dataset in [('existing_test',w/'data/reviewed_pilot/forklift_far_v4/dataset.yaml'),('new_test',w/'data/reviewed_pilot/forklift_cvat_prepared_v1/dataset.yaml')]:
  status('evaluating',model=name,dataset=group)
  m=model.val(data=str(dataset),split='test',imgsz=960,batch=4,device='cpu',workers=0,conf=.001,iou=.7,plots=False,project=str(out/'evaluation'),name=name+'_'+group,exist_ok=True)
  results[group]={k:float(v) for k,v in m.results_dict.items()}
 save(name+'_evaluation.json',results);return results
try:
 status('starting',initial_weights=str(base));model=YOLO(str(base));assert model.names=={0:'forklift'}
 model.add_callback('on_train_epoch_end',epoch)
 model.train(data=str(data),epochs=6,imgsz=960,freeze=10,lr0=.00003,optimizer="AdamW",warmup_bias_lr=.00003,warmup_epochs=1,batch=4,device='cpu',workers=0,seed=20261012,patience=0,amp=False,cache=False,project=str(w/'models/experiments'),name='forklift_cvat_combined_v1',exist_ok=True,plots=False,save=True,verbose=True)
 best=Path(model.trainer.save_dir)/'weights/best.pt';assert best.is_file()
 baseline=evaluate(base,'baseline');candidate=evaluate(best,'candidate')
 save('final_comparison.json',dict(baseline=baseline,candidate=candidate,candidate_weights=str(best),candidate_sha256=hashlib.sha256(best.read_bytes()).hexdigest(),promoted=False,limits='Small development tests from related sites; training includes scene adaptation and synthetic frames. AP metrics are not counts at a deployed confidence threshold.'))
 status('completed',candidate_weights=str(best),promoted=False)
except Exception:
 error=traceback.format_exc();save('failure.json',dict(error=error));status('failed',error=error);raise
