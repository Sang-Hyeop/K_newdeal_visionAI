"""Build reviewed context crops without promoting model-generated draft labels."""
import json,shutil,hashlib
from pathlib import Path
import cv2,yaml
ROOT=Path(__file__).resolve().parents[1]
def main():
 source=ROOT/'data/training_review/related_forklift_v1'
 candidates={r['candidate_id']:r for r in json.loads((source/'review_candidates.json').read_text())}
 decisions=json.loads((ROOT/'configs/review/related-forklift-v16.json').read_text())
 base=ROOT/'data/reviewed_pilot/logistics_scaled_filtered_v1'
 out=ROOT/'data/reviewed_pilot/logistics_related_v16'
 if out.exists():raise SystemExit('Existing dataset protected; select another version before rebuilding')
 rows=json.loads((base/'manifest.json').read_text())
 for split in ['train','val','test']:shutil.copytree(base/split,out/split)
 for decision in decisions:
  original=candidates[decision['candidate_id']]
  assert decision['training_eligible'] and decision['source_sha256']==original['source_sha256']
  assert decision['split']=='train'
  image_path=source/original['image']
  assert hashlib.sha256(image_path.read_bytes()).hexdigest()==decision['source_frame_image_sha256']
  image=cv2.imread(str(image_path))
  x1,y1,x2,y2=[int(v*2) for v in decision['crop_xyxy_960']]
  crop=image[y1:y2,x1:x2];h,w=crop.shape[:2];labels=[]
  for cls,l,t,r,b in decision['corrected_boxes_xyxy_960']:
   l=max(l*2,x1)-x1;t=max(t*2,y1)-y1;r=min(r*2,x2)-x1;b=min(b*2,y2)-y1
   if r<=l or b<=t:continue
   labels.append(f'{cls} {(l+r)/2/w:.7f} {(t+b)/2/h:.7f} {(r-l)/w:.7f} {(b-t)/h:.7f}')
  name=decision['image'];cv2.imwrite(str(out/'train/images'/name),crop)
  (out/'train/labels'/Path(name).with_suffix('.txt')).write_text('\n'.join(labels)+'\n')
  rows.append(decision)
 (out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 (out/'dataset.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'train/images','val':'val/images','test':'test/images','names':{0:'person',1:'forklift'}}))
if __name__=='__main__':main()
