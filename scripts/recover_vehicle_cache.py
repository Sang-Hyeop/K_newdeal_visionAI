# 5번 신규 분석에서 놓친 차량 추가 탐지
"""Supplement a hash-validated real-inference cache using current source images."""
import argparse,hashlib,json,sys
from pathlib import Path
import cv2,torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ultralytics import YOLO
from src.vehicle_recovery import VehicleRecovery,review_recovered_vehicles

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--candidates-only',action='store_true');a=p.parse_args()
 summary=json.loads((a.input/'summary.json').read_text());source=Path(summary['source']);assert sha(source)==summary['source_sha256']
 profile=summary['object_review_profile']
 for key in ['vehicle_weights','vehicle_support_weights']:assert sha(ROOT/profile[key])==summary['model_hashes'][profile[key]]
 torch.set_num_threads(4);engine=VehicleRecovery(YOLO(ROOT/profile['vehicle_weights']),YOLO(ROOT/profile['vehicle_support_weights']),profile);a.output.mkdir(parents=True,exist_ok=False);cap=cv2.VideoCapture(str(source));index=0;count=0;added=0
 with (a.input/'detections.jsonl').open() as src,(a.output/'detections.jsonl').open('w') as dst:
  for line in src:
   row=json.loads(line)
   while index<=row['frame_index']:
    ok,frame=cap.read();index+=1
    if not ok:raise RuntimeError('source ended')
   ds,diag=engine.update(frame,row['object_detections'],row['timestamp_seconds'],row['scene_cut'])
   if not a.candidates_only:
    ds,rejected=review_recovered_vehicles(ds,frame.shape[:2]);diag['consensus_rejected']=rejected
   row.update(object_detections=ds,vehicle_recovery=diag);dst.write(json.dumps(row)+'\n');count+=1;added+=sum(d.get('model_source')=='vehicle_recovery_current_image'for d in ds)
   if count%25==0:print('samples',count,'added',added,flush=True)
 cap.release();summary.update(status='current_vehicle_recovery',vehicle_recovery_provenance={'source_run':str(a.input),'source_log_sha256':sha(a.input/'detections.jsonl'),'method':'960_full_and_square_person_history_context_dual_model_current_image','code_sha256':sha(ROOT/'src/vehicle_recovery.py'),'history_is_search_only':True,'added_observations':added,'no_new_training':True});(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()
