"""Wait for the active training run, then evaluate without promoting a model."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--wait-seconds',type=int,default=7200);args=p.parse_args()
 run=ROOT/'outputs/training/logistics_pilot_v16_related';out=ROOT/'outputs/diagnostics/v16_related_validation'
 if out.exists():raise RuntimeError('Existing validation output protected')
 out.mkdir(parents=True);status=out/'status.json'
 def write(state,**extra):status.write_text(json.dumps({'status':state,'model_promoted':False,**extra},indent=2))
 write('waiting_for_training_completion');deadline=time.monotonic()+args.wait_seconds
 while not (run/'test_metrics.json').exists():
  if time.monotonic()>deadline:write('timeout_waiting_for_training');return
  time.sleep(10)
 weights=out/'best_snapshot.pt';shutil.copy2(run/'weights/best.pt',weights);sha=hashlib.sha256(weights.read_bytes()).hexdigest()
 write('validating',weights_sha256=sha)
 commands=[]
 for name,data in [('scaled','logistics_scaled_filtered_v1'),('old','logistics_v6_corrected_forklift')]:
  commands.append([sys.executable,'scripts/audit_pilot_predictions.py','--task','logistics','--data-path',f'data/reviewed_pilot/{data}','--weights',str(weights),'--run-name',f'logistics_v16_related_{name}','--report-name','fixed_threshold_final.json'])
 for name,video,config in [('forward','1_forklift_forward.mp4','forward-proximity.json'),('reverse','2_forklift_back.mp4','reverse-proximity.json')]:
  commands.append([sys.executable,'scripts/run_proximity_video.py','--source',f'data/videos/{video}','--weights',str(weights),'--output',str(out/name),'--config',f'configs/cameras/{config}'])
 try:
  with (out/'validation.log').open('w') as log:
   for cmd in commands:
    log.write(json.dumps(cmd)+'\n');log.flush();subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  reports={name:json.loads((ROOT/f'outputs/training/logistics_v16_related_{name}/fixed_threshold_final.json').read_text()) for name in ['scaled','old']}
  reports['v15_scaled']=json.loads((ROOT/'outputs/training/logistics_v15_final_scaled/fixed_threshold_final.json').read_text())
  reports['v15_old']=json.loads((ROOT/'outputs/training/logistics_v15_final_old/fixed_threshold_final.json').read_text())
  reports['baseline_scaled']=json.loads((ROOT/'docs/scaled-v6-baseline.json').read_text())
  subprocess.run([sys.executable,'scripts/diagnose_proximity_gaps.py','--weights',str(weights),'--output',str(out/'gap_frames')],cwd=ROOT,check=True)
  reports['videos']={name:json.loads((out/name/'summary.json').read_text()) for name in ['forward','reverse']}
  (out/'comparison.json').write_text(json.dumps(reports,indent=2));write('completed_pending_visual_review',weights_sha256=sha,limitations='Development data; final video outputs still require visual review; no automatic promotion')
 except Exception as exc:write('validation_failed',error=str(exc));raise
if __name__=='__main__':main()
