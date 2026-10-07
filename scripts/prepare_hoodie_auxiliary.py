"""Reproduce the sampled hood dataset and normalize mixed YOLO polygons to boxes."""
from pathlib import Path
import random,json,hashlib,shutil,yaml
ROOT=Path(__file__).resolve().parents[1]
def main():
 source=ROOT/'data/external/hoodie_detection_roboflow_v1';out=ROOT/'data/reviewed_pilot/hoodie_roboflow_v1'
 if (out/'manifest.json').exists():raise ValueError('Preserve existing dataset; use a new destination before rebuilding')
 out.mkdir(parents=True,exist_ok=True);files=[];converted=0
 for split,n in [('train',512),('valid',120),('test',100)]:
  labels=sorted((source/split/'labels').glob('*.txt'));positive=[];normal=[]
  for p in labels:
   (positive if any(x.split()[0]=='0'for x in p.read_text().splitlines()if x.strip())else normal).append(p)
  rng=random.Random(20261007);rng.shuffle(positive);rng.shuffle(normal);chosen=positive[:min(len(positive),n//2)]+normal[:n-min(len(positive),n//2)]
  target=out/('val'if split=='valid'else split);(target/'images').mkdir(parents=True);(target/'labels').mkdir()
  for p in chosen:
   image=next((source/split/'images').glob(p.stem+'.*'));rows=[]
   for line in p.read_text().splitlines():
    q=list(map(float,line.split()));c=int(q[0])
    if c not in (0,1):raise ValueError('Unexpected class')
    if len(q)==5:box=q[1:]
    elif len(q)>=7 and len(q)%2==1:
     xs=q[1::2];ys=q[2::2];box=[(min(xs)+max(xs))/2,(min(ys)+max(ys))/2,max(xs)-min(xs),max(ys)-min(ys)];converted+=1
    else:raise ValueError('Invalid label shape')
    if not all(0<=v<=1 for v in box)or box[2]<=0 or box[3]<=0:raise ValueError('Invalid box')
    row=str(c)+' '+' '.join(f'{v:.8f}'for v in box)
    if row not in rows:rows.append(row)
   shutil.copy2(image,target/'images'/image.name);label=target/'labels'/(image.stem+'.txt');label.write_text('\n'.join(rows)+'\n')
   files.append({'split':split,'image':str(image),'label':str(p),'sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
 (out/'dataset.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'train/images','val':'val/images','test':'test/images','nc':2,'names':['hooded_person','normal_person']}))
 (out/'manifest.json').write_text(json.dumps({'source':'https://universe.roboflow.com/jaydips-workspace/hoodie-detection-sojdq/dataset/1','license':'CC BY 4.0','author':'Jaydips Workspace','box_scope':'whole person; not helmet labels','sample_visual_review':16,'warning':'source frame sequences may overlap between original splits; test is development only','polygon_boxes_converted':converted,'files':files},indent=2))
 print('prepared',len(files),'images;',converted,'polygons converted')
if __name__=='__main__':main()
