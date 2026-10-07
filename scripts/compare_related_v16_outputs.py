"""Collect fixed-condition v15/v16 diagnostics; never promote automatically."""
from pathlib import Path
import json,cv2,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 d=ROOT/'outputs/diagnostics/v16_related_validation'
 if json.loads((d/'status.json').read_text())['status']!='completed_pending_visual_review':raise SystemExit('Validation not complete')
 report=json.loads((d/'comparison.json').read_text())
 report['model_promoted']=False
 report['data_notes']={'new_unique_source_frames':15,'train_images':466,'val_images':82,'test_images':40,'unreviewed_candidates_remaining':180,'demo_frames_used':0,'evaluation_scope':'development tests and same-camera demo adaptation; not independent-site accuracy'}
 report['weights_sha256']=hashlib.sha256((d/'best_snapshot.pt').read_bytes()).hexdigest()
 report['fixed_count_changes']={}
 for split in ['scaled','old']:
  report['fixed_count_changes'][split]={}
  for cls in ['person','forklift']:
   before=report['v15_'+split]['class_counts'][cls];after=report[split]['class_counts'][cls]
   report['fixed_count_changes'][split][cls]={k:{'before':before[k],'after':after[k],'delta':after[k]-before[k]} for k in ['TP','FP','FN']}
 report['video_before_after']={}
 for name in ['forward','reverse']:
  before=json.loads((ROOT/'outputs/diagnostics/v15_final_validation'/name/'summary.json').read_text());after=report['videos'][name]
  report['video_before_after'][name]={'before':before,'after':after}
  imgs=[]
  indices=[225,240,250,265] if name=='forward' else [310,320,330,345]
  for i in indices:
   a=cv2.imread(str(ROOT/'outputs/diagnostics/proximity_gaps_20261007'/f'{name}_{i}.jpg'));b=cv2.imread(str(d/'gap_frames'/f'{name}_{i}.jpg'))
   a=cv2.resize(a,(640,360));b=cv2.resize(b,(640,360));cv2.putText(a,'v15 diagnostic',(10,350),0,.65,(255,255,255),2);cv2.putText(b,'v16 diagnostic',(10,350),0,.65,(255,255,255),2)
   imgs.append(cv2.hconcat([a,b]))
  cv2.imwrite(str(d/f'{name}_before_after.jpg'),cv2.vconcat(imgs))
 (d/'final_comparison.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report['fixed_count_changes'],indent=2))
if __name__=='__main__':main()
