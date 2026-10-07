"""Exact source frames and reviewed primary head references. Adaptation only."""
from pathlib import Path
import argparse,json,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,torch
from ultralytics import YOLO
from src.ppe_person_crop import infer_person_ppe
from src.ppe_recall_ensemble import PPERecallEnsemble
from src.ppe_tiled_inference import infer_tiled_heads,iou

def main():
 p=argparse.ArgumentParser();p.add_argument('--ppe-weights',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--references',type=Path,default=ROOT/'data/training_review/ppe_remaining_v2/global_target_references.json');p.add_argument('--baseline-ppe-weights',type=Path);p.add_argument('--object-imgsz',type=int,default=640);p.add_argument('--helmet-specialist-weights',type=Path);p.add_argument('--source',type=Path,default=ROOT/'data/videos/5_PPE_Helmet.mp4');args=p.parse_args()
 if args.output.exists():raise ValueError('Protected output')
 args.output.mkdir(parents=True);torch.set_num_threads(4);ppe=YOLO(str(args.ppe_weights));people_model=YOLO(str(ROOT/'models/pretrained/yolo26n.pt'));refs=json.loads(args.references.read_text());cap=cv2.VideoCapture(str(args.source));totals={str(c):{'TP':0,'FN':0}for c in [0,1]};rows=[]
 if args.baseline_ppe_weights:ppe=PPERecallEnsemble(YOLO(str(args.baseline_ppe_weights)),ppe,preserve_union=True,helmet_specialist=YOLO(str(args.helmet_specialist_weights))if args.helmet_specialist_weights else None)
 try:
  for key,truth in refs.items():
   cap.set(1,int(key));ok,frame=cap.read()
   if not ok:raise ValueError('Missing frame')
   boxes=people_model.predict(frame,classes=[0],conf=.25,imgsz=args.object_imgsz,device='cpu',verbose=False)[0];people=[b.xyxy[0].tolist()for b in boxes.boxes]
   pred=ppe.predict(frame,conf=.25,imgsz=640,device='cpu',verbose=False)[0];heads=[{'class':ppe.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'source':'full_frame'}for b in pred.boxes];tiles,rejected=infer_tiled_heads(frame,ppe);heads.extend(tiles)
   obs=infer_person_ppe(frame,people,ppe,full_frame_heads=heads,crop_height_fraction=1)
   for o in obs:heads.extend(o['head_candidates'])
   unique=[]
   for gt in truth:
    if not any(gt['class_id']==a['class_id'] and iou(gt['bbox_xyxy'],a['bbox_xyxy'])>=.65 for a in unique):unique.append(gt)
   findings=[]
   for gt in unique:
    label=ppe.names[gt['class_id']];overlap=max((iou(gt['bbox_xyxy'],h['bbox_xyxy'])for h in heads if h['class']==label and h['confidence']>=.5),default=0);found=overlap>=.5;totals[str(gt['class_id'])]['TP' if found else 'FN']+=1;findings.append({**gt,'detected':found,'best_iou':overlap});a,b,c,d=map(int,gt['bbox_xyxy']);cv2.rectangle(frame,(a,b),(c,d),(0,255,0)if found else(0,0,255),2)
   cv2.imwrite(str(args.output/f'frame_{key}.jpg'),frame);rows.append({'frame_index':int(key),'heads':heads,'truth':findings,'people':people,'rejected_tile_heads':rejected})
 finally:cap.release()
 report={'source':str(args.source.resolve()),'weights':str(args.ppe_weights.resolve()),'helmet_specialist_weights':str(args.helmet_specialist_weights)if args.helmet_specialist_weights else None,'object_imgsz':args.object_imgsz,'baseline_ppe_weights':str(args.baseline_ppe_weights)if args.baseline_ppe_weights else None,'references':str(args.references),'confidence':.5,'iou':.5,'training_exposed':True,'scope':'exact reviewed primary-head source frames, not exhaustive whole-video ground truth','metrics':totals,'records':rows};(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(totals))
if __name__=='__main__':main()
