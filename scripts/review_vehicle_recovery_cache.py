"""Review supplementary vehicle observations without reusing inferred safety events."""
import argparse,hashlib,json,sys
import cv2
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.vehicle_recovery import review_recovered_vehicles

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();s=json.loads((a.input/'summary.json').read_text());a.output.mkdir(parents=True,exist_ok=False);count=added=rejected=0;cap=cv2.VideoCapture(s['source']);shape=(int(cap.get(4)),int(cap.get(3)));cap.release();assert min(shape)>0
 with (a.input/'detections.jsonl').open()as src,(a.output/'detections.jsonl').open('w')as dst:
  for line in src:
   r=json.loads(line);ds,rej=review_recovered_vehicles(r['object_detections'],shape);r['object_detections']=ds;r['vehicle_recovery']['consensus_rejected']=rej;r['rejected_object_proposals']+=rej;dst.write(json.dumps(r)+'\n');count+=1;added+=sum(d.get('model_source')=='vehicle_recovery_current_image'for d in ds);rejected+=len(rej)
 s.update(status='experimental_not_promoted',vehicle_recovery_provenance={**s.get('vehicle_recovery_provenance',{}),'source_cache':str(a.input),'candidate_log_sha256':sha(a.input/'detections.jsonl'),'recovery_code_sha256':sha(ROOT/'src/vehicle_recovery.py'),'samples':count,'added_observations':added,'consensus_rejected':rejected,'primary_minimum_confidence':.2,'support_minimum_confidence':.25,'minimum_geometric_mean':.3,'minimum_height_fraction':.08,'requires_current_person_context':True,'history_is_search_only':True,'no_new_training':True})
 (a.output/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(count,added,rejected)
if __name__=='__main__':main()
