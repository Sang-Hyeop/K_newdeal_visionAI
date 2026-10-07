"""Compare fixed development gates; never promote a checkpoint automatically."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'outputs/diagnostics/targeted_failure_v17';before=json.loads((base/'v16_fixed_gate/report.json').read_text());after=json.loads((base/'v17_fixed_gate/report.json').read_text())
 checks={'target_detection_8_of_8':after['target_detected']==8,'target_tracking_8_of_8':after['target_tracked']==8,'same_real_vehicle_track':after['target_same_vehicle_id'],'actual_worker_tracked_8_of_8':after['target_worker_tracked']==8,'reserved_vehicle_recall_not_worse':after['reserved_detected']>=before['reserved_detected']}
 for split in ['scaled','old']:
  for cls in ['person','forklift']:checks[f'{split}_{cls}_misses_not_worse']=after['fixed_tests'][split][cls]['FN']<=before['fixed_tests'][split][cls]['FN']
 pair_states=[{'frame_index':r['frame_index'],'states':[e['severity'] or 'UNKNOWN' for e in r['matched_actual_pair_events']]} for r in after['target']]
 report={'status':'passed_detection_tracking_gate_pending_visual_alert_review' if all(checks.values()) else 'experimental_not_promoted','checks':checks,'before':before,'after':after,'actual_pair_states':pair_states,'training_runs':1,'epochs':6,'repeat_training_allowed':False,'automatic_promotion':False,'failure_action':'keep v16; stop supplemental training repetition','limits':'These are same-camera development tests. Passing does not certify real-world safety or unseen-site performance.'}
 dest=base/'final_gate.json'
 if dest.exists():raise SystemExit('Existing assessment protected')
 dest.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'status':report['status'],'checks':checks,'actual_pair_states':pair_states}))
if __name__=='__main__':main()
