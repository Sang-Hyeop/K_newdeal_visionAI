"""Compare fixed-test errors and training distribution; no automatic label edits."""
from pathlib import Path
import json,os,hashlib
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,torch
from ultralytics import YOLO
from ultralytics.models.yolo.detect import DetectionTrainer
from types import SimpleNamespace
from audit_pilot_predictions import iou

def main():
 out=ROOT/'outputs/diagnostics/v14_regression';out.mkdir(parents=True,exist_ok=True)
 if (out/'error_comparison.json').exists():raise SystemExit('Existing diagnostic protected')
 torch.set_num_threads(4)
 source=YOLO(str(ROOT/'models/pilot_v6_corrected_forklift/person_forklift.pt')).model.float();trainer=object.__new__(DetectionTrainer);trainer.args=SimpleNamespace(cls_remap=True);trainer.data={'nc':2,'names':{0:'person',1:'forklift'},'channels':3}
 rebuilt=trainer.get_model(cfg=source.yaml,weights=source,verbose=False);a=source.state_dict();b=rebuilt.state_dict();different=[k for k in a if k not in b or not torch.equal(a[k],b[k])];assert not different and a.keys()==b.keys()
 (out/'initial_transfer_audit.json').write_text(json.dumps({'source_names':source.names,'target_names':rebuilt.names,'source_tensor_count':len(a),'target_tensor_count':len(b),'different_tensors':different,'scope':'Installed get_model initialization only; excludes training updates.'},indent=2))
 data=ROOT/'data/reviewed_pilot/logistics_error_focus_v1';reports={};weights={'v6':ROOT/'models/pilot_v6_corrected_forklift/person_forklift.pt','v12':ROOT/'models/pilot_v12_low_bias_warmup/person_forklift.pt','v14':ROOT/'outputs/training/logistics_pilot_v14_error_focus/weights/best.pt'}
 for version,weight in weights.items():
  model=YOLO(str(weight));items=[]
  for path in sorted((data/'test/images').glob('*.jpg')):
   im=cv2.imread(str(path));h,w=im.shape[:2];gt=[]
   for j,line in enumerate((data/'test/labels'/path.with_suffix('.txt').name).read_text().splitlines()):
    c,x,y,bw,bh=map(float,line.split());gt.append({'index':j,'class':model.names[int(c)],'bbox':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h],'height_at_640':bh*h*640/max(w,h)})
   result=model.predict(im,imgsz=640,conf=.05,device='cpu',verbose=False)[0];pred=sorted([{'class':model.names[int(b.cls)],'bbox':b.xyxy[0].tolist(),'confidence':float(b.conf)} for b in result.boxes],key=lambda p:-p['confidence']);used=set();matched={};fps=[]
   for p in pred:
    if p['confidence']<.25:continue
    score,j=max([(iou(p['bbox'],g['bbox']),g['index']) for g in gt if g['class']==p['class'] and g['index'] not in used],default=(0,-1))
    if score>=.5:used.add(j);matched[j]=p
    else:fps.append(p)
   for g in gt:
    candidates=sorted([{**p,'iou':iou(p['bbox'],g['bbox'])} for p in pred if p['class']==g['class']],key=lambda p:-p['iou']);best=candidates[0] if candidates else None
    g['status']='TP' if g['index'] in used else 'FN';g['best_same_class_candidate']=best
    g['diagnostic_reason']='matched' if g['status']=='TP' else ('same_class_box_below_threshold' if best and best['iou']>=.5 and best['confidence']<.25 else 'no_matching_same_class_box_at_conf_0.05')
   items.append({'image':path.name,'ground_truth':gt,'false_positive_predictions':fps})
   cv2.imwrite(str(out/f'{version}_{path.stem}.jpg'),cv2.resize(result.plot(),(960,540)))
  reports[version]=items
 (out/'error_comparison.json').write_text(json.dumps({'conf_for_matching':.25,'conf_for_candidate_search':.05,'iou_threshold':.5,'versions':reports,'limitation':'Predictions below0.05 absent; diagnostic reasons are not causal explanations.'},indent=2))
 manifest=json.load(open(data/'manifest.json'));counts=Counter();groups=Counter();sizes=Counter();roles={'mostly_contained_in_forklift_proxy':0,'not_contained_proxy':0};records=[]
 for path in sorted((data/'train/images').glob('*.jpg')):
  im=cv2.imread(str(path));h,w=im.shape[:2];boxes=[]
  for line in (data/'train/labels'/path.with_suffix('.txt').name).read_text().splitlines():
   c,x,y,bw,bh=map(float,line.split());boxes.append((int(c),[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]));counts['person' if c==0 else 'forklift']+=1
   if c==0:
    height=bh*h*640/max(w,h);sizes['under_32px_at_640' if height<32 else '32_to_64px_at_640' if height<64 else 'at_least_64px_at_640']+=1
  if not boxes:counts['background_images']+=1
  for c,b in boxes:
   if c!=0:continue
   area=(b[2]-b[0])*(b[3]-b[1]);contained=any(max(0,min(b[2],f[2])-max(b[0],f[0]))*max(0,min(b[3],f[3])-max(b[1],f[1]))/area>=.8 for fc,f in boxes if fc==1);roles['mostly_contained_in_forklift_proxy' if contained else 'not_contained_proxy']+=1
  row=next(r for r in manifest if r['split']=='train' and r.get('image',r['stem']+'.jpg')==path.name);groups[row.get('group','unrecorded')]+=1;records.append({'image':path.name,'site':row.get('site'),'group':row.get('group')})
 distribution={'train_images':len(records),'label_counts':dict(counts),'person_height_distribution':dict(sizes),'person_vehicle_containment_proxy':roles,'groups_with_multiple_images':{k:v for k,v in groups.items() if v>1},'train_records':records,'limitations':'Containment is geometry only, not verified driver identity. Groups include crops of the same frame; label counts do not measure independent diversity.'};(out/'training_distribution.json').write_text(json.dumps(distribution,indent=2));print(json.dumps({k:v for k,v in distribution.items() if k!='train_records'}))
if __name__=='__main__':main()
