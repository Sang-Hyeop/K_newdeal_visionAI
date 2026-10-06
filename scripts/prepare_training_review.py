"""원본 ZIP을 보존하며 학습 전 검토용 표본과 라벨 미리보기를 만듭니다."""
from pathlib import Path
from collections import Counter
import json, random, zipfile
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/training_review'
BASE=Path('/Users/sanghyeopkim/Downloads/121.물류창고 내 작업 안전 데이터')
SEED=20261006

def draw(im,boxes,names):
    result=im.copy()
    for cls,x1,y1,x2,y2 in boxes:
        color=(0,220,255) if cls==0 else (255,160,50)
        cv2.rectangle(result,(round(x1),round(y1)),(round(x2),round(y2)),color,3)
        cv2.putText(result,names[cls],(round(x1),max(20,round(y1)-5)),cv2.FONT_HERSHEY_SIMPLEX,.65,color,2)
    return result

def sheet(items,path):
    canvas=np.full((len(items)//3*310+(310 if len(items)%3 else 0),1440,3),240,np.uint8)
    for i,(title,im) in enumerate(items):
        h,w=im.shape[:2];scale=min(480/w,270/h);thumb=cv2.resize(im,(round(w*scale),round(h*scale)))
        x=i%3*480;y=i//3*310
        canvas[y+30:y+30+thumb.shape[0],x:x+thumb.shape[1]]=thumb
        cv2.putText(canvas,title,(x+8,y+20),cv2.FONT_HERSHEY_SIMPLEX,.5,(30,30,30),1)
    if not cv2.imwrite(str(path),canvas):raise RuntimeError(path)

def main():
    for folder in ('logistics/images','logistics/labels','logistics/original_json','logistics/previews','ppe/previews'):
        (OUT/folder).mkdir(parents=True,exist_ok=True)
    labelzip=next(BASE.rglob('TL_07_*.zip'));imagezip=next(BASE.rglob('TS_07_*.zip'))
    selected=[];rejections=Counter();used=set();counts=Counter()
    with zipfile.ZipFile(labelzip) as labels,zipfile.ZipFile(imagezip) as images:
        image_map={Path(n).stem:n for n in images.namelist() if n.lower().endswith('.jpg')}
        entries=sorted(n for n in labels.namelist() if n.endswith('.json'));random.Random(SEED).shuffle(entries)
        for name in entries:
            d=json.loads(labels.read(name));raw=d['Raw data Info.'];group=raw['raw_data_ID']
            if group in used:continue
            stem=d['Source data Info.']['source_data_ID'];anns=d['Learning data info.']['annotation']
            target=[a for a in anns if a['class_id'] in ('WO-01','WO-02','WO-04') and a['type']=='box']
            if not any(a['class_id']=='WO-04' for a in target) or not any(a['class_id'] in ('WO-01','WO-02') for a in target):continue
            if stem not in image_map:rejections['missing_image']+=1;continue
            data=images.read(image_map[stem]);im=cv2.imdecode(np.frombuffer(data,dtype=np.uint8),cv2.IMREAD_COLOR)
            if im is None:rejections['decode_failure']+=1;continue
            h,w=im.shape[:2];boxes=[];rows=[];bad=False
            for a in target:
                cls=1 if a['class_id']=='WO-04' else 0
                if len(a['coord'])!=4:bad=True;break
                x,y,bw,bh=map(float,a['coord'])
                if not np.isfinite([x,y,bw,bh]).all() or bw<=0 or bh<=0:bad=True;break
                x1=max(0,x);y1=max(0,y);x2=min(w,x+bw);y2=min(h,y+bh)
                if x2<=x1 or y2<=y1:bad=True;break
                boxes.append((cls,x1,y1,x2,y2));rows.append(f'{cls} {(x1+x2)/2/w:.6f} {(y1+y2)/2/h:.6f} {(x2-x1)/w:.6f} {(y2-y1)/h:.6f}')
            if bad:rejections['invalid_box']+=1;continue
            used.add(group);counts.update(b[0] for b in boxes)
            (OUT/'logistics/images'/f'{stem}.jpg').write_bytes(data)
            (OUT/'logistics/labels'/f'{stem}.txt').write_text('\n'.join(rows)+'\n')
            (OUT/'logistics/original_json'/f'{stem}.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
            preview=draw(im,boxes,['person','forklift']);cv2.imwrite(str(OUT/'logistics/previews'/f'{stem}.jpg'),preview)
            selected.append(dict(id=len(selected)+1,image=stem+'.jpg',raw_video_id=group,location=raw.get('location_ID'),source_zip=str(imagezip),zip_member=image_map[stem],label_member=name,boxes=boxes,status='converted_draft_needs_visual_review',training_eligible=False))
            if len(selected)==12:break
    if len(selected)!=12:raise RuntimeError(f'Only {len(selected)} matching groups')
    litems=[(f"L{x['id']:02} person={sum(b[0]==0 for b in x['boxes'])} forklift={sum(b[0]==1 for b in x['boxes'])}",cv2.imread(str(OUT/'logistics/previews'/x['image']))) for x in selected]
    sheet(litems,OUT/'logistics/contact.jpg')
    old=next(Path('/Users/sanghyeopkim/Desktop').glob('*/시선_팀프로젝트/data/ppe'))
    entries=sorted((old/'train/images').glob('*.jpg'));random.Random(SEED).shuffle(entries)
    pitems=[];ppe=[]
    for i,p in enumerate(entries[:12],1):
        im=cv2.imread(str(p));h,w=im.shape[:2];boxes=[]
        for line in (old/'train/labels'/(p.stem+'.txt')).read_text().splitlines():
            cls,x,y,bw,bh=map(float,line.split());boxes.append((int(cls),(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h))
        preview=draw(im,boxes,['helmeted_head','no_helmet_head']);cv2.imwrite(str(OUT/'ppe/previews'/p.name),preview)
        pitems.append((f'P{i:02} heads={len(boxes)}',preview));ppe.append(dict(id=i,image=str(p),boxes=boxes,status='original_label_review',training_eligible=False))
    sheet(pitems,OUT/'ppe/contact.jpg')
    manifest={'seed':SEED,'purpose':'review_not_training','logistics':selected,'logistics_instances':dict(counts),'rejections':dict(rejections),'ppe':ppe,'notes':['Logistics mapping: WO-01/WO-02 -> person, WO-04 -> forklift. XYWH to normalized YOLO; clipped to image bounds.','One frame per raw video group; grouping does not guarantee independent sites.','PPE uses existing labels; no automatic correction.','Do not train on these drafts until label completeness is reviewed.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('Prepared 12 logistics groups and 12 PPE review images. Instances:',dict(counts),flush=True)
if __name__=='__main__':main()
