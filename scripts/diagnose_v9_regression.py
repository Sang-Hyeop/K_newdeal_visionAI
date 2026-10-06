"""Compare v6/v9 at object level; never edit held-out labels."""
from pathlib import Path
import os, json, collections
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/runtime/matplotlib'))
import cv2, torch
from ultralytics import YOLO
from audit_pilot_predictions import iou

def read_boxes(path,w,h):
    boxes=[]
    for line in path.read_text().splitlines():
        c,x,y,bw,bh=map(float,line.split())
        boxes.append((int(c),[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]))
    return boxes

def validation_thresholds(base,models):
    reports=[]
    for version,model in models.items():
        for threshold in [.1,.15,.2,.25]:
            counts={c:{'TP':0,'FP':0,'FN':0} for c in ['person','forklift']}
            for p in sorted((base/'val/images').glob('*.jpg')):
                im=cv2.imread(str(p));h,w=im.shape[:2]
                gt=read_boxes(base/'val/labels'/f'{p.stem}.txt',w,h)
                result=model.predict(im,imgsz=640,conf=threshold,device='cpu',verbose=False)[0]
                used=set()
                for b in sorted(result.boxes,key=lambda b:-float(b.conf.item())):
                    c=int(b.cls.item());box=b.xyxy[0].tolist()
                    overlap,j=max([(iou(box,g),j) for j,(gc,g) in enumerate(gt) if gc==c and j not in used],default=(0,-1))
                    key=['person','forklift'][c]
                    if overlap>=.5:counts[key]['TP']+=1;used.add(j)
                    else:counts[key]['FP']+=1
                for j,(c,_) in enumerate(gt):
                    if j not in used:counts[['person','forklift'][c]]['FN']+=1
            reports.append({'version':version,'threshold':threshold,'counts':counts})
    return {'split':'val','iou':.5,'imgsz':640,'reports':reports,
            'selected_operating_threshold':None,'status':'diagnostic; no automatic threshold change'}

def main():
    torch.set_num_threads(4)
    base=ROOT/'data/reviewed_pilot/logistics_v9_hard_examples'
    out=ROOT/'outputs/video_validation/v9_regression_diagnosis'
    out.mkdir(parents=True,exist_ok=True)
    models={v:YOLO(str(ROOT/p)) for v,p in {
        'v6':'models/pilot_v6_corrected_forklift/person_forklift.pt',
        'v9':'models/pilot_v9_hard_examples/person_forklift.pt'}.items()}
    objects=[]
    for image_path in sorted((base/'test/images').glob('*.jpg')):
        image=cv2.imread(str(image_path));h,w=image.shape[:2]
        gt=read_boxes(base/'test/labels'/f'{image_path.stem}.txt',w,h)
        by_version={}
        for version,model in models.items():
            result=model.predict(image,imgsz=640,conf=.01,device='cpu',verbose=False)[0]
            predictions=sorted([(int(b.cls.item()),b.xyxy[0].tolist(),float(b.conf.item())) for b in result.boxes],key=lambda b:-b[2])
            assigned={}; used=set()
            for c,box,conf in predictions:
                choices=[(iou(box,g),j) for j,(gc,g) in enumerate(gt) if gc==c and j not in used]
                overlap,index=max(choices,default=(0,-1))
                if overlap>=.5:
                    assigned[index]={'confidence':conf,'iou':overlap};used.add(index)
            by_version[version]=assigned
        regression=False
        for index,(c,box) in enumerate(gt):
            row={'image':image_path.name,'gt_index':index,'class':['person','forklift'][c],'gt_xyxy':box}
            for v in models:
                match=by_version[v].get(index)
                row[v]={'matched_at_001':match is not None,'confidence':match['confidence'] if match else None,'matched_at_025':bool(match and match['confidence']>=.25)}
            row['regressed']=row['v6']['matched_at_025'] and not row['v9']['matched_at_025']
            row['recovered']=row['v9']['matched_at_025'] and not row['v6']['matched_at_025']
            objects.append(row);regression|=row['regressed']
        if regression:
            for c,box in gt:
                x1,y1,x2,y2=map(round,box);cv2.rectangle(image,(x1,y1),(x2,y2),(0,255,0) if c==0 else (0,0,255),3)
            cv2.imwrite(str(out/f'gt_{image_path.name}'),image)
    distributions={}
    for split in ['train','val','test']:
        heights=[];counts=collections.Counter();empty=0
        for p in (base/split/'labels').glob('*.txt'):
            lines=p.read_text().splitlines();empty+=not lines
            for line in lines:
                c,_,_,_,height=map(float,line.split());counts[int(c)]+=1
                if c==0:heights.append(height*640)
        distributions[split]={'class_box_counts':dict(counts),'empty_images':empty,
            'person_height_proxy_under_32':sum(h<32 for h in heights),
            'person_height_proxy_under_64':sum(h<64 for h in heights),
            'scale_note':'normalized height * 640; proxy, not actual letterboxed pixels'}
    report={'objects':objects,'distribution':distributions,'status':'development diagnosis, not causal proof; held labels unchanged'}
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2))
    (out/'validation_thresholds.json').write_text(json.dumps(validation_thresholds(base,models),indent=2))
    print(json.dumps({'regressed':[r for r in objects if r['regressed']], 'recovered':[r for r in objects if r['recovered']], 'distribution':distributions},indent=2))

if __name__=='__main__':main()
