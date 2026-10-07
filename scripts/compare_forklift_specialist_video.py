"""Actual frame-by-frame fork predictions; no box interpolation or frozen placeholders."""
import argparse,json,hashlib,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
import cv2,torch
from ultralytics import YOLO
from src.ppe_tiled_inference import iou

def detections(model,frame,size):
 result=model.predict(frame,imgsz=size,conf=.1,device='cpu',verbose=False)[0]
 return [{'class':result.names[int(b.cls.item())],'confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()}for b in result.boxes if result.names[int(b.cls.item())]=='forklift']
def dedup(ds):
 kept=[]
 for d in sorted(ds,key=lambda r:-r['confidence']):
  if not any(iou(d['bbox_xyxy'],k['bbox_xyxy'])>=.5 for k in kept):kept.append(d)
 return kept

def main():
 p=argparse.ArgumentParser();p.add_argument('--tiles',action='store_true');p.add_argument('--mode',choices=['baseline','candidate'],required=True);p.add_argument('--videos',type=int,nargs='+',default=[2]);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline-cache',type=Path);p.add_argument('--weights',type=Path);p.add_argument('--imgsz',type=int,default=640);a=p.parse_args();torch.set_num_threads(2);a.output.mkdir(parents=True,exist_ok=False)
 manifest=json.loads((ROOT/'configs/demo-scenarios.json').read_text());obj=json.loads((ROOT/'configs/demo-object-model.json').read_text());paths=[obj['baseline_weights'],obj['supplement_weights']]if a.mode=='baseline'else [str(a.weights)if a.weights else 'models/safe_carrying_specialist_v1/best.pt'];models=[YOLO(str(ROOT/q))for q in paths]
 hashes={q:hashlib.sha256((ROOT/q).read_bytes()).hexdigest()for q in paths}
 for n in a.videos:
  spec=next(s for s in manifest['scenarios']if s['video_number']==n);source=ROOT/'data/videos'/spec['source_name'];assert hashlib.sha256(source.read_bytes()).hexdigest()==spec['source_sha256'];cap=cv2.VideoCapture(str(source));fps=cap.get(5);w,h=int(cap.get(3)),int(cap.get(4));expected=int(cap.get(7));old=None
  if a.mode=='candidate':
   assert a.baseline_cache is not None;meta=json.loads((a.baseline_cache/f'video{n}-metadata.json').read_text());assert meta['source_sha256']==spec['source_sha256']and meta['imgsz']==a.imgsz;old={r['frame_index']:r for r in map(json.loads,(a.baseline_cache/f'video{n}.jsonl').read_text().splitlines())};assert len(old)==expected
  writer=cv2.VideoWriter(str(a.output/f'video{n}.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h));assert writer.isOpened();idx=0;observed=0
  with (a.output/f'video{n}.jsonl').open('w')as fh:
   while True:
    ok,frame=cap.read()
    if not ok:break
    ds=[d for m in models for d in detections(m,frame,a.imgsz)];tile_rejected=[]
    if a.tiles:
     from src.forklift_tiled_inference import infer_tiled_forklifts
     for m in models:
      accepted,rejected=infer_tiled_forklifts(frame,m);ds+=accepted;tile_rejected+=rejected
    ds=dedup(ds);observed+=any(d['confidence']>=.25 for d in ds);row={'frame_index':idx,'timestamp_seconds':idx/fps,'detections':ds,'tiled_rejected':tile_rejected}
    if old is not None:
     from src.forklift_specialist_ensemble import supplement_forklift_records
     row['fused_detections']=supplement_forklift_records(old[idx]['detections'],ds)
    fh.write(json.dumps(row)+'\n');shown=frame.copy()
    sets=[(ds,(0,220,0),'NEW')]if old is None else [(old[idx]['detections'],(0,140,255),'OLD'),(ds,(0,230,0),'NEW')]
    if a.mode=='baseline':sets=[(ds,(0,140,255),'OLD')]
    for entries,color,label in sets:
     for d in entries:
      if d['confidence']<.25:continue
      l,t,r,b=map(int,d['bbox_xyxy']);cv2.rectangle(shown,(l,t),(r,b),color,2);cv2.putText(shown,f"{label} forklift {d['confidence']:.2f}",(l,max(20,t-5)),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2)
    cv2.putText(shown,f'FRAME {idx} / REAL INFERENCE / no interpolation',(15,h-20),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2);writer.write(shown);idx+=1
    if idx%100==0:print(n,idx,expected,flush=True)
  writer.release();cap.release();assert idx==expected
  meta={'source':str(source),'source_sha256':spec['source_sha256'],'fps':fps,'frames':idx,'weights_sha256':hashes,'confidence_inference':.1,'confidence_display':.25,'imgsz':a.imgsz,'native_scale_tiles':a.tiles,'any_forklift_prediction_frames_at025':observed,'status':'diagnostic, prediction presence is not ground-truth recall; orange=old, green=new; forklift-only specialist is not a person/PPE model'};(a.output/f'video{n}-metadata.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta),flush=True)
if __name__=='__main__':main()
