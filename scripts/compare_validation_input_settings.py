"""Compare reused validation samples only; never change production thresholds."""
from pathlib import Path
import subprocess,json,sys
r=Path(__file__).resolve().parents[1];python=sys.executable;reports=[]
for v,weight in [('v6','models/pilot_v6_corrected_forklift/person_forklift.pt'),('v12','models/pilot_v12_low_bias_warmup/person_forklift.pt'),('v14','outputs/training/logistics_pilot_v14_error_focus/weights/best.pt')]:
 for size in [640,960]:
  for conf in [.25,.1]:
   name=f'val_{v}_{size}_{str(conf).replace(".","")}.json';subprocess.run([python,'scripts/audit_pilot_predictions.py','--task','logistics','--data-path','data/reviewed_pilot/logistics_error_focus_v1','--run-name','logistics_pilot_v14_error_focus','--weights',weight,'--split','val','--imgsz',str(size),'--confidence',str(conf),'--report-name',name],cwd=r,check=True,stdout=subprocess.DEVNULL);d=json.load(open(r/'outputs/training/logistics_pilot_v14_error_focus'/name));reports.append({'model':v,'imgsz':size,'confidence':conf,'class_counts':d['class_counts']})
(r/'outputs/diagnostics/v14_regression/validation_scale_comparison.json').write_text(json.dumps({'split':'val','images':8,'configurations':reports,'status':'small reused development validation; no production threshold selection yet'},indent=2));print(json.dumps(reports))
