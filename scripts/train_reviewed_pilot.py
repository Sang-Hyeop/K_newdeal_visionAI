"""학습 허용 manifest를 확인하고 지정 초기 가중치로 개발용 학습."""
from pathlib import Path
import os,json,argparse,hashlib
ROOT=Path(__file__).resolve().parents[1]
for folder in ['yolo','matplotlib','cache']:(ROOT/'outputs/runtime'/folder).mkdir(parents=True,exist_ok=True)
os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'outputs/runtime/cache'))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
os.environ.setdefault('OMP_NUM_THREADS','4')
import torch
from ultralytics import YOLO

def main():
 p=argparse.ArgumentParser();p.add_argument('--dataset',choices=['ppe','logistics'],required=True);p.add_argument('--epochs',type=int,default=10);p.add_argument('--run-name');p.add_argument('--data-path',type=Path);p.add_argument('--weights',type=Path);p.add_argument('--learning-rate',type=float);p.add_argument('--freeze',type=int,default=0);p.add_argument('--warmup-bias-lr',type=float);p.add_argument('--resume',type=Path);p.add_argument('--patience',type=int,default=10);args=p.parse_args();run_name=args.run_name or args.dataset+'_pilot_v1'
 if args.freeze<0 or args.patience<0:raise ValueError('freeze and patience must be nonnegative')
 base=args.data_path or ROOT/'data/reviewed_pilot'/args.dataset
 rows=json.loads((base/'manifest.json').read_text());accepted=[r for r in rows if r['training_eligible']]
 assert accepted and all(any(r['split']==s for r in accepted) for s in ['train','val','test'])
 # manifest 승인과 실제 학습 파일이 정확히 일치해야 한다.
 snapshot=[]
 for split in ['train','val','test']:
  expected={r.get('image',r.get('stem','')+'.jpg') for r in accepted if r['split']==split}
  actual={p.name for p in (base/split/'images').glob('*.jpg')}
  if expected!=actual:raise ValueError(f'{split}: manifest/image mismatch')
  for name in sorted(expected):
   image=base/split/'images'/name;label=base/split/'labels'/(image.stem+'.txt')
   snapshot.append({'split':split,'image':name,'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'label_sha256':hashlib.sha256(label.read_bytes()).hexdigest()})
 torch.set_num_threads(4)
 initial=args.weights or ROOT/'models/pretrained/yolo26n.pt'
 model=YOLO(str(initial))
 training_options={'freeze':args.freeze}
 if args.resume is not None:
  if not args.resume.is_file():raise ValueError('Missing resume checkpoint')
  training_options['resume']=str(args.resume.resolve())
 if args.warmup_bias_lr is not None:
  if not 0<=args.warmup_bias_lr<1:raise ValueError('warmup-bias-lr must be between 0 and 1')
  training_options['warmup_bias_lr']=args.warmup_bias_lr
 if args.learning_rate is not None:
  if not 0 < args.learning_rate < 1:raise ValueError('learning-rate must be between 0 and 1')
  training_options.update(optimizer='AdamW',lr0=args.learning_rate,warmup_epochs=1.0)
 model.train(**training_options,data=str(base/'dataset.yaml'),epochs=args.epochs,imgsz=640,batch=4,device='mps' if torch.backends.mps.is_available() else 'cpu',workers=0,amp=False,seed=20261006,deterministic=True,project=str(ROOT/'outputs/training'),name=run_name,exist_ok=False,plots=True,mosaic=0.0,fliplr=0.5,scale=0.2,translate=0.05,degrees=0.0,patience=args.patience)
 (Path(model.trainer.save_dir)/'dataset_snapshot.json').write_text(json.dumps({'dataset':str(base.resolve()),'files':snapshot,'initial_weights':str(initial.resolve()),'initial_weights_sha256':hashlib.sha256(initial.read_bytes()).hexdigest(),'resume_checkpoint':str(args.resume.resolve()) if args.resume else None,'patience':args.patience,'freeze_layers':args.freeze,'epochs':args.epochs,'learning_rate':args.learning_rate,'warmup_bias_lr':model.trainer.args.warmup_bias_lr},indent=2))
 best=Path(model.trainer.save_dir)/'weights/best.pt'
 result=YOLO(str(best)).val(data=str(base/'dataset.yaml'),split='test',imgsz=640,device='cpu',workers=0,plots=True,project=str(ROOT/'outputs/training'),name=run_name+'_test')
 (Path(model.trainer.save_dir)/'test_metrics.json').write_text(json.dumps({'weights':str(best),'metrics':result.results_dict,'per_class':{result.names[int(c)]:{'precision':float(result.box.p[i]),'recall':float(result.box.r[i]),'mAP50':float(result.box.ap50[i]),'mAP50_95':float(result.box.ap[i])} for i,c in enumerate(result.box.ap_class_index)},'status':'development pilot; not independent final CCTV benchmark'},indent=2))
if __name__=='__main__':main()
