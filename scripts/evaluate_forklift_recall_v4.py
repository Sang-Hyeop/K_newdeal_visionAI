"""Score actual multi-model proposals against unchanged development references."""
from pathlib import Path
import argparse,sys,json,os,hashlib,cv2,torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
from ultralytics import YOLO
from src.object_recall_ensemble import ObjectRecallEnsemble
from src.forklift_specialist_ensemble import supplement_forklift_records
from scripts.evaluate_forklift_specialist_fixed import count_matches

def main():
 p=argparse.ArgumentParser();p.add_argument('--specialist',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reference-audit',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
 quality=json.load(open(a.reference_audit))['images']if a.reference_audit else {}
 paths=[ROOT/'models/pilot_v16_related/person_forklift.pt',ROOT/'models/demo_object_adaptation_v1/best.pt',a.specialist,ROOT/'models/nvidia_object_adaptation_v1/best.pt'];models=[YOLO(str(x))for x in paths];base=ObjectRecallEnsemble(models[0],models[1]);dataset=ROOT/'data/reviewed_pilot/safe_carrying_envelope_v2/test';cases=[]
 for path in sorted((dataset/'images').glob('*.jpg')):
  im=cv2.imread(str(path));h,w=im.shape[:2];gt=[]
  for line in (dataset/'labels'/path.with_suffix('.txt').name).read_text().splitlines():
   c,x,y,bh,bv=map(float,line.split());gt.append([(x-bh/2)*w,(y-bv/2)*h,(x+bh/2)*w,(y+bv/2)*h])
  cases.append(('test50',path.name,im,gt))
 protocol=json.load(open(ROOT/'configs/review/reverse-main-vehicle-reference-v2.json'));meta=json.load(open(ROOT/'outputs/diagnostics/safe_carrying_envelope_v2_native2/video2-metadata.json'));cap=cv2.VideoCapture(meta['source'])
 for r in protocol['frames']:
  cap.set(1,r['frame_index']);ok,im=cap.read();assert ok;cases.append(('reverse22',f"frame{r['frame_index']}",im,[[v*4.8 for v in r['bbox_xyxy_400']]]))
 cap.release();rows=[]
 for scope,name,im,gt in cases:
  result=base.predict(im,imgsz=640,conf=.1,device='cpu',verbose=False)[0];prior=[{'class':'forklift','confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist()}for b in result.boxes if result.names[int(b.cls.item())]=='forklift'];combined=list(prior)
  for mi,size in [(0,1280),(1,1280),(2,640),(2,1280),(3,640),(3,1280)]:
   result=models[mi].predict(im,imgsz=size,conf=.1,device='cpu',verbose=False)[0];observed=[{'class':'forklift','confidence':float(b.conf.item()),'bbox_xyxy':b.xyxy[0].tolist(),'model_source':str(paths[mi]),'inference_imgsz':size}for b in result.boxes if result.names[int(b.cls.item())]=='forklift'];combined=supplement_forklift_records(combined,observed)
  original_gt=gt
  if name in quality:
   change=quality[name];image_path=dataset/'images'/name;label_path=dataset/'labels'/Path(name).with_suffix('.txt').name;assert hashlib.sha256(image_path.read_bytes()).hexdigest()==change['image_sha256'];assert hashlib.sha256(label_path.read_bytes()).hexdigest()==change['original_label_sha256'];gt=[change['reviewed_reference_xyxy']]
  row={'original_references':original_gt,'original_candidate':{str(c):count_matches([d for d in combined if d['confidence']>=c],original_gt)for c in [.1,.25]},'scope':scope,'image':name,'references':gt,'prior':{str(c):count_matches([d for d in prior if d['confidence']>=c],gt)for c in [.1,.25]},'candidate':{str(c):count_matches([d for d in combined if d['confidence']>=c],gt)for c in [.1,.25]},'detections':combined};rows.append(row)
  if len(rows)%10==0:print(len(rows),len(cases),flush=True)
 summary={}
 for scope in ['test50','reverse22']:
  selected=[r for r in rows if r['scope']==scope];summary[scope]={tag:{c:{k:sum(r[tag][c][k]for r in selected)for k in ['TP','FP','FN']}for c in ['0.1','0.25']}for tag in ['prior','candidate']}
 (a.output/'evaluation.json').write_text(json.dumps({'status':'development_candidate_not_independent; not full-frame zero proof','iou':.5,'confidence_primary':.25,'model_sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in paths},'summary':summary,'reference_audit':str(a.reference_audit)if a.reference_audit else None,'rows':rows},indent=2));print(json.dumps(summary))
if __name__=='__main__':main()
