"""Actual fixed-threshold head recall on reviewed crops; adaptation diagnostic."""
from pathlib import Path
import argparse,json,sys,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,torch
from ultralytics import YOLO
from src.ppe_tiled_inference import iou

def main():
 p=argparse.ArgumentParser();p.add_argument('--weights',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 if args.output.exists():raise ValueError('Output protected')
 args.output.mkdir(parents=True);torch.set_num_threads(4);model=YOLO(str(args.weights));review=json.loads((ROOT/'configs/review/ppe-remaining-target-v2.json').read_text());records=[];total={str(c):{'TP':0,'FN':0,'FP':0}for c in [0,1]}
 for r in review:
  im=cv2.imread(str(ROOT/'data/training_review/ppe_remaining_v2'/r['image']));pred=model.predict(im,conf=.5,imgsz=640,device='cpu',verbose=False)[0];boxes=[{'class_id':int(b.cls.item()),'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()}for b in pred.boxes];used=set();miss=[]
  for c,*gt in r['boxes_xyxy']:
   matches=[(iou(gt,b['bbox_xyxy']),j)for j,b in enumerate(boxes)if j not in used and b['class_id']==c];best=max(matches,default=(0,None))
   if best[0]>=.5:used.add(best[1]);total[str(c)]['TP']+=1
   else:total[str(c)]['FN']+=1;miss.append({'class_id':c,'bbox_xyxy':gt})
  for j,b in enumerate(boxes):
   if j not in used:total[str(b['class_id'])]['FP']+=1
  records.append({'index':r['index'],'frame_index':r['frame_index'],'predictions':boxes,'misses':miss})
 report={'weights':str(args.weights.resolve()),'confidence':.5,'iou':.5,'metrics':total,'training_exposed':True,'scope':'53 manually reviewed crops, not every frame or independent accuracy','records':records};(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='records'}))
if __name__=='__main__':main()
