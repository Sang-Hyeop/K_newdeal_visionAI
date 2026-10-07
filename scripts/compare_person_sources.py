"""Compare separately evaluated person sources without tuning or training."""
from pathlib import Path
import argparse,json


def overlap(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union>0 else 0.


def main():
    p=argparse.ArgumentParser()
    for name in ['baseline','candidate','review','output']:p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise ValueError('New output required')
    spec=json.loads(args.review.read_text());summaries=[json.loads((d/'summary.json').read_text()) for d in [args.baseline,args.candidate]]
    assert all(s['source_sha256']==spec['source_sha256'] for s in summaries)
    rows=[[json.loads(x) for x in (d/'observations.jsonl').read_text().splitlines()] for d in [args.baseline,args.candidate]]
    assert len(rows[0])==len(rows[1]);metrics={}
    for identity,label in spec['reference_tracks'].items():
        checks=[]
        for before,after in zip(*rows):
            assert before['frame_index']==after['frame_index'] and before['timestamp_seconds']==after['timestamp_seconds']
            target=next((t for t in before['tracks'] if t['track_id']==identity),None)
            if target:
                matches=[t['track_id'] for t in after['tracks'] if overlap(target['detected_bbox_xyxy'],t['detected_bbox_xyxy'])>=spec['matching_iou']]
                checks.append({'timestamp_seconds':before['timestamp_seconds'],'candidate_matching_track_ids':matches})
        metrics[identity]={'review_label':label,'baseline_observations':len(checks),'candidate_overlap_matches':sum(bool(c['candidate_matching_track_ids']) for c in checks),'checks':checks}
    report={'review':spec,'summaries':summaries,'metrics':metrics,'production_promoted':False,'training_performed':False,'limitation':'Selected-track overlap audit, not independent accuracy benchmark; additional videos not evaluated for this candidate.'}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print({key:{k:v for k,v in value.items() if k!='checks'} for key,value in metrics.items()})

if __name__=='__main__':main()
