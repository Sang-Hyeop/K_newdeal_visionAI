"""Recall diagnostic using real multiscale detections; never edit test labels."""
from pathlib import Path
import os,json,sys,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import torch,cv2
from ultralytics import YOLO
from src.object_recall_ensemble import ObjectRecallEnsemble
from src.ppe_tiled_inference import iou

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Protected output')
 torch.set_num_threads(4);base=YOLO(ROOT/'models/pilot_v16_related/person_forklift.pt');new=YOLO(ROOT/'models/demo_object_adaptation_v1/best.pt');last=YOLO(ROOT/'models/demo_object_adaptation_v1/last.pt');person=YOLO(ROOT/'models/pretrained/yolo26n.pt');model=ObjectRecallEnsemble(base,new);reports={};a.output.mkdir(parents=True)
 for split,data in [('scaled',ROOT/'data/reviewed_pilot/logistics_scaled_filtered_v1'),('old',ROOT/'data/reviewed_pilot/logistics_v6_corrected_forklift')]:
  counts={c:{'TP':0,'FN':0,'FP':0}for c in [0,1]};records=[]
  for path in sorted((data/'test/images').glob('*.jpg')):
   im=cv2.imread(str(path));h,w=im.shape[:2];truth=[]
   for line in (data/'test/labels'/(path.stem+'.txt')).read_text().splitlines():
    c,x,y,bw,bh=map(float,line.split());truth.append({'class_id':int(c),'bbox_xyxy':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]})
   predictions=[]
   for net,size,source in [(model,640,'baseline_preserved640'),(base,1280,'baseline1280'),(new,1280,'adapted1280'),(last,640,'adapted_last640'),(person,1280,'pretrained_person1280')]:
    kwargs={'classes':[0]}if net is person else{}
    for b in net.predict(im,conf=.25,imgsz=size,device='cpu',verbose=False,**kwargs)[0].boxes:predictions.append({'class_id':int(b.cls.item()),'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'source':source})
   matched=set();findings=[]
   for box in predictions:
    options=[(iou(box['bbox_xyxy'],g['bbox_xyxy']),j)for j,g in enumerate(truth)if g['class_id']==box['class_id']and j not in matched];best=max(options,default=(0,-1))
    if best[0]>=.5:matched.add(best[1]);counts[box['class_id']]['TP']+=1
    else:counts[box['class_id']]['FP']+=1
   for j,g in enumerate(truth):
    if j not in matched:counts[g['class_id']]['FN']+=1
    findings.append({**g,'detected':j in matched,'best_iou':max((iou(g['bbox_xyxy'],b['bbox_xyxy'])for b in predictions if b['class_id']==g['class_id']),default=0)})
   records.append({'image':str(path),'truth':findings,'predictions':predictions})
  reports[split]={'class_counts':counts,'records':records};print(split,counts,flush=True)
 (a.output/'report.json').write_text(json.dumps({'status':'experimental_raw_union_not_promoted','confidence':.25,'iou':.5,'all_images_same_routes':True,'notes':'Real proposals only; duplicated boxes retained for diagnostic; false positives may rise substantially; no deployment promotion','datasets':reports},indent=2)+'\n')
if __name__=='__main__':main()
