"""Train a separate whole-person hood classifier; never map Normal to PPE SAFE."""
from pathlib import Path
import os,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'outputs/runtime/cache'))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import torch
from ultralytics import YOLO

def main():
 torch.set_num_threads(2)
 data=ROOT/'data/reviewed_pilot/hoodie_roboflow_v1/dataset.yaml'
 initial=ROOT/'models/pretrained/yolo26n.pt'
 model=YOLO(str(initial))
 model.train(data=str(data),epochs=8,imgsz=640,batch=4,device='cpu',workers=0,amp=False,freeze=10,optimizer='AdamW',lr0=.001,warmup_epochs=1,seed=20261007,deterministic=True,mosaic=0,fliplr=.5,scale=.15,translate=.05,patience=8,project=str(ROOT/'outputs/training'),name='hoodie_auxiliary_v1_clean',exist_ok=False,plots=True)
 best=Path(model.trainer.save_dir)/'weights/best.pt'
 result=YOLO(str(best)).val(data=str(data),split='test',device='cpu',workers=0,batch=4,plots=False)
 out=ROOT/'models/hoodie_auxiliary_v1';out.mkdir(parents=True,exist_ok=True)
 shutil.copy2(best,out/'hoodie.pt')
 report={'status':'experimental_not_promoted','box_scope':'whole person','classes':{0:'hooded_person',1:'normal_person'},'normal_is_not_ppe_safe':True,'source':'https://universe.roboflow.com/jaydips-workspace/hoodie-detection-sojdq/dataset/1','author':'Jaydips Workspace','license':'CC BY 4.0','train':512,'val':120,'test':100,'initial_sha256':hashlib.sha256(initial.read_bytes()).hexdigest(),'weights_sha256':hashlib.sha256((out/'hoodie.pt').read_bytes()).hexdigest(),'metrics':result.results_dict,'limitation':'original nearby CCTV frames may cross splits; development metrics only; source6 evaluation still required'}
 (out/'report.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
