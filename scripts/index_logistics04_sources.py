from pathlib import Path
import json,zipfile,math
from collections import Counter
r=Path(__file__).resolve().parents[1];source=json.load(open(r/'data/training_review/train_archives_v1/candidates.json'))[0];rows=[]
with zipfile.ZipFile(source['label_zip']) as z:
 for n in z.namelist():
  if not n.endswith('.json'):continue
  d=json.loads(z.read(n));a=d['Raw data Info.'];w,h=a['resolution'];boxes=[];issues=[]
  for ann in d['Learning data info.']['annotation']:
   if ann['class_id'] not in ['WO-01','WO-02','WO-04'] or ann['type']!='box':continue
   c=ann['coord']
   if len(c)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in c):issues.append('invalid_box');continue
   x,y,bw,bh=c
   if min(x,y)<0 or min(bw,bh)<=0 or x+bw>w+.01 or y+bh>h+.01:issues.append('outside_box');continue
   boxes.append([1 if ann['class_id']=='WO-04' else 0,*c])
  rows.append({'stem':d['Source data Info.']['source_data_ID'],'member':n,'group':a['raw_data_ID'],'site':a['location_ID'],'resolution':[w,h],'boxes':boxes,'issues':issues,'source_kind':'04'})
p=r/'outputs/data-audit/full_scan_20261006/logistics04_pool.json';p.write_text(json.dumps(rows,ensure_ascii=False));print('04 indexed',len(rows),'groups',len({x['group'] for x in rows}),'issues',sum(bool(x['issues']) for x in rows))
