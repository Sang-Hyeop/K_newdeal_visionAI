"""Render unchanged held references and real inference for remaining forklift failures."""
from pathlib import Path
import sys,json,hashlib,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,torch
from ultralytics import YOLO
from src.object_recall_ensemble import ObjectRecallEnsemble
from src.forklift_specialist_ensemble import ForkliftSpecialistEnsemble
from src.ppe_tiled_inference import iou

def main():
 torch.set_num_threads(2);out=ROOT/'outputs/diagnostics/forklift_failure_audit_v1';out.mkdir(parents=True,exist_ok=True)
 base=ObjectRecallEnsemble(YOLO(ROOT/'models/pilot_v16_related/person_forklift.pt'),YOLO(ROOT/'models/demo_object_adaptation_v1/best.pt'));m=ForkliftSpecialistEnsemble(base,YOLO(ROOT/'models/safe_carrying_envelope_v2/best.pt'))
 report=json.load(open(ROOT/'outputs/diagnostics/safe_carrying_envelope_v2_fixed.json'));dataset=ROOT/'data/reviewed_pilot/safe_carrying_envelope_v2/test';cases=[]
 for r in report['rows']:
  if not r['models']['fused']['0.25']['FN']:continue
  path=dataset/'images'/r['image'];im=cv2.imread(str(path));h,w=im.shape[:2];gt=[]
  for line in (dataset/'labels'/path.with_suffix('.txt').name).read_text().splitlines():
   c,x,y,bh,bv=map(float,line.split());gt.append([(x-bh/2)*w,(y-bv/2)*h,(x+bh/2)*w,(y+bv/2)*h])
  cases.append((r['image'],im,gt,{'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reference':'held_test; unchanged label'}))
 refs=json.load(open(ROOT/'configs/review/reverse-main-vehicle-reference-v2.json'))['frames'];meta=json.load(open(ROOT/'outputs/diagnostics/safe_carrying_envelope_v2_native2/video2-metadata.json'));cap=cv2.VideoCapture(meta['source'])
 for r in refs:
  if r['frame_index']not in [425,450,475,500,525]:continue
  cap.set(1,r['frame_index']);ok,im=cap.read();assert ok;b=r['bbox_xyxy_400'];gt=[[b[0]*4.8,b[1]*4.8,b[2]*4.8,b[3]*4.8]];cases.append((f"reverse_{r['frame_index']}.jpg",im,gt,{'reference':'coarse whole-loaded envelope; same-scene diagnostic','source_sha256':meta['source_sha256'],'frame_index':r['frame_index']}))
 cap.release();rows=[]
 for name,im,gt,provenance in cases:
  models={};shown=im.copy()
  for size in [640,1280]:
   result=m.predict(im,imgsz=size,conf=.01,device='cpu',verbose=False)[0];ds=[{'bbox_xyxy':b.xyxy[0].tolist(),'confidence':float(b.conf.item())}for b in result.boxes if result.names[int(b.cls.item())]=='forklift'];models[str(size)]={'detections':ds,'reference_matches':[{'best_iou_at025':max([iou(d['bbox_xyxy'],g)for d in ds if d['confidence']>=.25],default=0),'best_confidence_at_iou05':max([d['confidence']for d in ds if iou(d['bbox_xyxy'],g)>=.5],default=0)}for g in gt]}
   if size==1280:
    for d in ds:
     if d['confidence']<.1:continue
     a,b,c,e=map(int,d['bbox_xyxy']);cv2.rectangle(shown,(a,b),(c,e),(0,220,0)if d['confidence']>=.25 else(0,150,255),2);cv2.putText(shown,f"{d['confidence']:.2f}",(a,max(20,b-4)),0,.55,(255,255,255),1)
  for g in gt:
   a,b,c,e=map(int,g);cv2.rectangle(shown,(a,b),(c,e),(255,80,0),3)
  cv2.imwrite(str(out/name),shown);rows.append({'image':name,'references':gt,'provenance':provenance,'models':models});print(name,models['1280']['reference_matches'],flush=True)
 (out/'audit.json').write_text(json.dumps({'rows':rows,'legend':'blue=unchanged reference; green=real confidence>=.25; orange=.1-.25; not all proposals true vehicles'},indent=2))
if __name__=='__main__':main()
