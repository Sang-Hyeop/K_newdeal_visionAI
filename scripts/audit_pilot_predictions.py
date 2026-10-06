"""개발용 test의 고정 신뢰도/IoU 조건에서 TP/FP/FN 측정. 작은 표본의 진단용."""
from pathlib import Path
import os,json,argparse
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
import cv2,torch
from ultralytics import YOLO

def iou(a,b):
 iw=max(0,min(a[2],b[2])-max(a[0],b[0]));ih=max(0,min(a[3],b[3])-max(a[1],b[1]));inter=iw*ih
 return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter+1e-9)
def main():
 p=argparse.ArgumentParser();p.add_argument('--task',choices=['ppe','logistics'],required=True);p.add_argument('--version',default='v2');args=p.parse_args();task=args.task
 data=ROOT/'data/reviewed_pilot'/('logistics_v2' if task=='logistics' and args.version=='v2' else task)
 out=ROOT/'outputs/training'/f'{task}_pilot_{args.version}';model=YOLO(str(out/'weights/best.pt'));torch.set_num_threads(4)
 counts={name:{'TP':0,'FP':0,'FN':0} for name in model.names.values()};per_image=[]
 for path in sorted((data/'test/images').glob('*.jpg')):
  image=cv2.imread(str(path));h,w=image.shape[:2];gt=[]
  for line in (data/'test/labels'/(path.stem+'.txt')).read_text().splitlines():
   c,x,y,bw,bh=map(float,line.split());gt.append((int(c),[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]))
  result=model.predict(image,imgsz=640,conf=.25,device='cpu',verbose=False)[0];pred=sorted([(int(b.cls.item()),b.xyxy[0].tolist(),float(b.conf.item())) for b in result.boxes],key=lambda x:-x[2]);matched=set()
  for c,box,conf in pred:
   options=[(iou(box,gbox),j) for j,(gc,gbox) in enumerate(gt) if gc==c and j not in matched];best=max(options,default=(0,-1))
   if best[0]>=.5:matched.add(best[1]);counts[model.names[c]]['TP']+=1
   else:counts[model.names[c]]['FP']+=1
  for j,(c,_) in enumerate(gt):
   if j not in matched:counts[model.names[c]]['FN']+=1
  per_image.append({'image':path.name,'gt_count':len(gt),'prediction_count':len(pred),'matched':len(matched)})
 for c in counts.values():
  c['precision']=c['TP']/(c['TP']+c['FP']) if c['TP']+c['FP'] else None
  c['recall']=c['TP']/(c['TP']+c['FN']) if c['TP']+c['FN'] else None
 report={'confidence_threshold':.25,'iou_threshold':.5,'split':'test','status':'small development diagnostic; not final independent evaluation','class_counts':counts,'images':per_image};(out/'fixed_threshold_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['class_counts']))
if __name__=='__main__':main()
