"""Taxonomy-aware fixed forklift evaluation; single-class and two-class weights compared by name."""
import argparse,json,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
import cv2,torch
from ultralytics import YOLO
from src.object_recall_ensemble import ObjectRecallEnsemble
from src.forklift_specialist_ensemble import ForkliftSpecialistEnsemble
from src.ppe_tiled_inference import iou

def count_matches(pred,gt):
    adjacency=[[i for i,b in enumerate(gt)if iou(d['bbox_xyxy'],b)>=.5]for d in pred];assigned={}
    def visit(k,seen):
        for g in adjacency[k]:
            if g in seen:continue
            seen.add(g)
            if g not in assigned or visit(assigned[g],seen):assigned[g]=k;return True
        return False
    tp=sum(visit(k,set())for k in range(len(pred)))
    return {'TP':tp,'FN':len(gt)-tp,'FP':len(pred)-tp}
def main():
    p=argparse.ArgumentParser();p.add_argument('--weights',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--dataset',type=Path,default=ROOT/'data/reviewed_pilot/safe_carrying_envelope_v2');a=p.parse_args();torch.set_num_threads(2)
    base=ObjectRecallEnsemble(YOLO(str(ROOT/'models/pilot_v16_related/person_forklift.pt')),YOLO(str(ROOT/'models/demo_object_adaptation_v1/best.pt')));specialist=YOLO(str(a.weights));fused=ForkliftSpecialistEnsemble(base,specialist);dataset=a.dataset;rows=[]
    for imfile in sorted((dataset/'test/images').glob('*.jpg')):
        im=cv2.imread(str(imfile));h,w=im.shape[:2];gt=[]
        for line in (dataset/'test/labels'/imfile.with_suffix('.txt').name).read_text().splitlines():
            cls,cx,cy,bw,bh=map(float,line.split());assert cls==0;gt.append([(cx-bw/2)*w,(cy-bh/2)*h,(cx+bw/2)*w,(cy+bh/2)*h])
        entry={'image':imfile.name,'GT':len(gt),'models':{}}
        # Separate passes for reproducible model outputs; all kwargs identical.
        for tag,model in [('previous_bundle',base),('specialist',specialist),('fused',fused)]:
            result=model.predict(im,imgsz=640,conf=.1,device='cpu',verbose=False)[0];pred=[{'bbox_xyxy':b.xyxy[0].tolist(),'confidence':float(b.conf.item())}for b in result.boxes if result.names[int(b.cls.item())]=='forklift'];entry['models'][tag]={str(c):count_matches([d for d in pred if d['confidence']>=c],gt)for c in [.1,.25]}
        rows.append(entry)
    summary={}
    for tag in ['previous_bundle','specialist','fused']:
        summary[tag]={}
        for c in ['0.1','0.25']:
            sums={k:sum(r['models'][tag][c][k]for r in rows)for k in ['TP','FP','FN']};sums.update(recall=sums['TP']/max(1,sums['TP']+sums['FN']),precision=sums['TP']/max(1,sums['TP']+sums['FP']));summary[tag][c]=sums
    subsets={}
    for subset,selected in [('legacy40',[r for r in rows if not r['image'].startswith(('safe_','video_'))]),('new_factory_envelope',[r for r in rows if r['image'].startswith('safe_')]),('nvidia_holdout',[r for r in rows if r['image'].startswith('video_')])]:
        subsets[subset]={'frames':len(selected),'counts':{tag:{c:{k:sum(r['models'][tag][c][k]for r in selected)for k in ['TP','FP','FN']}for c in ['0.1','0.25']}for tag in ['previous_bundle','specialist','fused']}}
    a.output.write_text(json.dumps({'imgsz':640,'iou':.5,'model_sha256':hashlib.sha256(a.weights.read_bytes()).hexdigest(),'test_frames':len(rows),'summary':summary,'subsets':subsets,'rows':rows,'limits':['Development set with historical vehicle boxes and reviewed loaded-vehicle envelopes; box scope differences must be inspected','Class mapped by name; person detections excluded from forklift-only metrics','Not independent unseen-factory benchmark']},indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
