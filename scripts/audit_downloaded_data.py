from pathlib import Path
from collections import Counter,defaultdict
import json, math
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--output',type=Path,default=Path('outputs/data-audit/inventory.json'))
args=parser.parse_args()
base=args.root
args.output.parent.mkdir(parents=True,exist_ok=True)
report={}
for name in ('aihub_smartyard','aihub_logistics'):
 root=base/name;counts=Counter();classes=Counter();bad=Counter();groups=defaultdict(set)
 images=defaultdict(list)
 for p in root.rglob('*.jpg'):images[p.stem].append(str(p))
 for p in root.rglob('*.json'):
  try:d=json.loads(p.read_text())
  except Exception:bad['invalid_json']+=1;continue
  split=p.relative_to(root).parts[0];counts[split+'_json']+=1
  if p.stem not in images:bad['missing_image']+=1
  if name=='aihub_smartyard':
   group=p.parent.name;counts[split+'_'+group]+=1
   w=d['images']['width'];h=d['images']['height']
   cmap={c['id']:c['name'] for c in d['class']}
   anns=d['annotations'];key=p.stem.rsplit('_',1)[0]
   for a in anns:
    classes[cmap.get(a['object_class'],'UNKNOWN')]+=1
    b=a.get('bbox',[])
    if len(b)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in b):bad['invalid_bbox']+=1;continue
    x1,y1,x2,y2=b
    if x2<=x1 or y2<=y1:bad['nonpositive_xyxy']+=1
    if x1<0 or y1<0 or x2>w or y2>h:bad['outside_bounds_xyxy']+=1
  else:
   raw=d['Raw data Info.'];key=raw['raw_data_ID'];anns=d['Learning data info.']['annotation']
   for a in anns:classes[a['class_id']+'|'+a['type']]+=1
  groups[split].add(key)
 common=groups['training']&groups['validation']
 report[name]=dict(root=str(root),images=sum(map(len,images.values())),counts=dict(counts),annotation_classes=dict(classes),issues=dict(bad),group_overlap=len(common),group_overlap_examples=sorted(common)[:10],group_definition='smartyard filename minus final frame token; logistics raw_data_ID')
 print(name,json.dumps(report[name],ensure_ascii=False),flush=True)
args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
