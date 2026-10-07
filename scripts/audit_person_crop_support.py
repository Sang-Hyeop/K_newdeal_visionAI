"""Shadow-only crop support audit; never suppress production detections."""
from pathlib import Path
import argparse,json,os,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))
from scripts.compare_person_sources import overlap
import cv2,torch
from ultralytics import YOLO


def main():
    p=argparse.ArgumentParser()
    for name in ['baseline','weights','review','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sample-indices',type=int,nargs='+',default=[3,7,12,25,38,50,63,75,85])
    args=p.parse_args()
    if args.output.exists():raise ValueError('New output required')
    s=json.loads((args.baseline/'summary.json').read_text());spec=json.loads(args.review.read_text());source=Path(s['source'])
    assert hashlib.sha256(source.read_bytes()).hexdigest()==spec['source_sha256']==s['source_sha256']
    rows=[json.loads(x) for x in (args.baseline/'observations.jsonl').read_text().splitlines()]
    if any(n<0 or n>=len(rows) for n in args.sample_indices):raise ValueError('Invalid sample index')
    torch.set_num_threads(4);model=YOLO(str(args.weights))
    if model.names.get(0)!='person':raise ValueError('Expected person class 0')
    cap=cv2.VideoCapture(str(source));report=[]
    try:
        for n in args.sample_indices:
            r=rows[n];cap.set(1,r['frame_index']);ok,f=cap.read()
            if not ok:raise ValueError('Cannot read source frame')
            h,w=f.shape[:2]
            for t in r['tracks']:
                if t['track_id'] not in spec['reference_tracks']:continue
                a,b,c,d=t['detected_bbox_xyxy'];pw=(c-a)*.3;ph=(d-b)*.3
                x=max(0,int(a-pw));y=max(0,int(b-ph));x2=min(w,int(c+pw));y2=min(h,int(d+ph))
                result=model.predict(f[y:y2,x:x2],classes=[0],conf=.1,imgsz=640,device='cpu',verbose=False)[0];matches=[]
                for box in result.boxes:
                    u,v,u2,v2=box.xyxy[0].tolist()
                    if overlap([a,b,c,d],[u+x,v+y,u2+x,v2+y])>=spec['matching_iou']:matches.append(float(box.conf.item()))
                report.append({'sample_index':n,'track_id':t['track_id'],'timestamp_seconds':r['timestamp_seconds'],'max_support_confidence':max(matches,default=0),'supports_at_0_25':max(matches,default=0)>=.25})
    finally:cap.release()
    args.output.write_text(json.dumps({'method':'v16 proposal + 30 percent context on each side; original person model 640 conf .1; support IoU .25 and score .25','source_sha256':s['source_sha256'],'weights_sha256':hashlib.sha256(args.weights.read_bytes()).hexdigest(),'production_changed':False,'training_performed':False,'rows':report},indent=2)+'\n')
    print('Shadow crop audit saved; no production suppression.')

if __name__=='__main__':main()
