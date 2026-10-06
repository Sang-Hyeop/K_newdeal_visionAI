"""YOLO26 분류 특징층을 유지한 두 클래스 초기화와 추가 학습. 설치 버전 8.4.153 검증용."""
from pathlib import Path
import os,copy,json,hashlib,argparse
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'));os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
import torch
from torch import nn
from ultralytics import YOLO
from ultralytics.models.yolo.detect import DetectionTrainer
NAMES={0:'person',1:'forklift'}
def preserve_head(source):
 model=copy.deepcopy(source).float();head=model.model[-1]
 if head.nc!=80:raise ValueError('Expected 80-class source; do not silently reinitialize another model')
 if source.names[0]!='person' or source.names[7]!='truck':raise ValueError('Unexpected source class mapping')
 for name in ['cv3','one2one_cv3']:
  for branch in getattr(head,name):
   original=branch[-1]
   if not isinstance(original,nn.Conv2d) or original.out_channels!=80:raise ValueError('Unsupported classifier architecture')
   replacement=nn.Conv2d(original.in_channels,2,original.kernel_size,original.stride,original.padding,bias=True)
   with torch.no_grad():
    replacement.weight.copy_(original.weight[[0,7]]);replacement.bias.copy_(original.bias[[0,7]])
   branch[-1]=replacement
 head.nc=2;head.no=2+head.reg_max*4;model.nc=2;model.yaml['nc']=2;model.names=NAMES.copy()
 return model
class PreservedTrainer(DetectionTrainer):
 def get_model(self,cfg=None,weights=None,verbose=True):
  if weights is None:raise ValueError('Local pretrained source required')
  return preserve_head(weights)
def main():
 p=argparse.ArgumentParser();p.add_argument('--epochs',type=int,default=12);p.add_argument('--run-name',default='logistics_pilot_v8_preserved_head');p.add_argument('--data-path',type=Path,default=ROOT/'data/reviewed_pilot/logistics_v7_full_scene');args=p.parse_args()
 base=args.data_path.resolve();rows=json.loads((base/'manifest.json').read_text());accepted=[r for r in rows if r['training_eligible']];snapshot=[]
 for split in ['train','val','test']:
  expected={r.get('image',r['stem']+'.jpg') for r in accepted if r['split']==split};actual={p.name for p in (base/split/'images').glob('*.jpg')};assert expected==actual and expected
  for name in sorted(expected):
   im=base/split/'images'/name;lab=base/split/'labels'/Path(name).with_suffix('.txt').name
   snapshot.append({'split':split,'image':name,'image_sha256':hashlib.sha256(im.read_bytes()).hexdigest(),'label_sha256':hashlib.sha256(lab.read_bytes()).hexdigest()})
 torch.set_num_threads(4);source=ROOT/'models/pretrained/yolo26n.pt';wrapper=YOLO(str(source));original=wrapper.model
 # Person logits must be preserved exactly before training, for both feature branches.
 preserved=preserve_head(original)
 for group in ['cv3','one2one_cv3']:
  for a,b in zip(getattr(original.model[-1],group),getattr(preserved.model[-1],group)):
   assert torch.equal(a[-1].weight[0],b[-1].weight[0]);assert a[0].state_dict().keys()==b[0].state_dict().keys()
 for key,value in original.state_dict().items():
  if '.cv3.' in key or '.one2one_cv3.' in key:
   target=preserved.state_dict()[key]
   if value.shape==target.shape:assert torch.equal(value,target)
 wrapper.train(trainer=PreservedTrainer,data=str(base/'dataset.yaml'),epochs=args.epochs,imgsz=640,batch=4,device='cpu',workers=0,amp=False,seed=20261006,deterministic=True,project=str(ROOT/'outputs/training'),name=args.run_name,exist_ok=False,optimizer='AdamW',lr0=.0003,warmup_epochs=1,freeze=10,mosaic=0,scale=.2,translate=.05,fliplr=.5,patience=12,plots=True)
 out=Path(wrapper.trainer.save_dir);(out/'dataset_snapshot.json').write_text(json.dumps({'dataset':str(base),'files':snapshot,'initial_weights_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'person_classifier_preserved':True,'forklift_initializer':'COCO truck prior, not a trained forklift class','frozen_backbone_layers':10},indent=2))
 best=out/'weights/best.pt';reloaded=YOLO(str(best));assert reloaded.names==NAMES
 result=reloaded.val(data=str(base/'dataset.yaml'),split='test',imgsz=640,device='cpu',workers=0,plots=True,project=str(ROOT/'outputs/training'),name=args.run_name+'_test')
 (out/'test_metrics.json').write_text(json.dumps({'weights':str(best),'metrics':result.results_dict,'status':'development experiment, not final independent evaluation'},indent=2))
if __name__=='__main__':main()
