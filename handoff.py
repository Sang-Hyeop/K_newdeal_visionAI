"""Portable entry point for the five-video team handoff (Python 3.11+)."""
import argparse,hashlib,json,os,subprocess,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'outputs/runtime/yolo'))

def call(*args):
    print('RUN:', ' '.join(str(a) for a in args),flush=True)
    subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,check=True)

def check(models=False):
    index=json.loads((ROOT/'configs/team-runtime-index.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'configs/github-runtime.json').read_text(encoding='utf-8'))
    for i,item in enumerate(manifest['files'],1):
        p=ROOT/item['path']
        if not p.is_file() or p.stat().st_size!=item['bytes']:raise ValueError('Missing/changed: '+item['path'])
        with p.open('rb')as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=item['sha256']:raise ValueError('Checksum mismatch: '+item['path'])
    for item in json.loads((ROOT/'configs/demo-videos.json').read_text(encoding='utf-8')):
        p=ROOT/'data/videos'/item['file']
        with p.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=item['sha256']:raise ValueError('Input video checksum mismatch: '+item['file'])
    print('PASS:',len(manifest['files']),'runtime asset hashes and 5 source video hashes match; asset source',index['source_commit'])
    if models:
        import cv2,torch
        from ultralytics import YOLO
        torch.set_num_threads(4)
        source=ROOT/'data/videos/1_forklift_worker_collision_risk.mp4';cap=cv2.VideoCapture(str(source));ok,frame=cap.read();cap.release()
        if not ok:raise ValueError('Cannot decode input video')
        for path in index['model_hashes']:
            model=YOLO(str(ROOT/path));result=model.predict(frame,imgsz=640,conf=.15,device='cpu',verbose=False)[0]
            print('PASS model inference:',path,'boxes',len(result.boxes))
        sys.path.insert(0,str(ROOT))
        from src.ppe_final_detector import FinalPPEDetector
        print('PASS PPE helper:',len(FinalPPEDetector().predict(frame)),'head observations')
    return 0

def run_video(n,fresh=False,max_seconds=None):
    if max_seconds is not None and max_seconds<=0:raise ValueError('max-seconds must be positive')
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    dest=Path('outputs/handoff_runs')/f'presentation{n}_{stamp}'
    if n==2:
        if max_seconds is not None:raise ValueError('Video2 runner processes the full 12-second input; omit --max-seconds')
        call('scripts/run_intrusion_review.py','--output',dest);print('Result:',ROOT/dest);return
    legacy={1:2,3:5,4:4,5:7}[n]
    common=['scripts/run_demo_scenarios.py','--videos',legacy,'--ppe-final','--sample-fps','5']
    limit=['--max-seconds',max_seconds]if max_seconds is not None else[]
    if n==5 and fresh:
        baseline=dest/'baseline';candidates=dest/'candidates';reviewed=dest/'reviewed_cache'
        call(*common,'--proximity-geometry','bottom_center',*limit,'--output',baseline)
        call('scripts/recover_vehicle_cache.py','--input',baseline/'video7','--output',candidates/'video7','--candidates-only')
        call('scripts/review_vehicle_recovery_cache.py','--input',candidates/'video7','--output',reviewed/'video7')
        call(*common,'--reuse-run',reviewed,'--reuse-objects','--proximity-geometry','bottom_center','--temporal-riders',*limit,'--output',dest/'result')
    else:
        caches={1:'presentation1_equipment_corrected_2026-10-14',3:'presentation3_ppe_review_2026-10-14',4:'presentation4_worker_corrected_final_2026-10-14',5:'presentation5_vehicle_recovery_review_cache_v2_2026-10-14'}
        reuse=[]if fresh else['--reuse-run',Path('outputs/diagnostics')/caches[n],'--reuse-objects']
        geometry=['--proximity-geometry','bottom_center','--temporal-riders']if n==5 else[]
        call(*common,*reuse,*geometry,*limit,'--output',dest)
    print('Result:',ROOT/dest)

def main():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='action')
    q=subs.add_parser('check',help='Verify bundled SHA-256; optionally run CPU model inference');q.add_argument('--models',action='store_true')
    subs.add_parser('list',help='Print current review videos and event log locations')
    q=subs.add_parser('run',help='Rebuild current review; cached real observations by default');q.add_argument('--video',type=int,choices=range(1,6),required=True);q.add_argument('--fresh',action='store_true');q.add_argument('--max-seconds',type=float)
    q=subs.add_parser('backend',help='Import the five complete event logs and optionally serve APIs');q.add_argument('--import-only',action='store_true');q.add_argument('--port',type=int,default=8010)
    subs.add_parser('test',help='Run detection and backend unit suites')
    a=p.parse_args()
    if a.action=='check':return check(a.models)
    if a.action=='list':
        index=json.loads((ROOT/'configs/team-runtime-index.json').read_text(encoding='utf-8'))
        for row in index['videos']:
            print('Video',row['presentation_video_number'], '\n Command:',row['entrypoint'])
            for key in ['source_video','camera_config','object_review_profile','review_video','event_root']:
                if row.get(key):print(' ',key+':',ROOT/row[key])
            for path in row['implementation']:print('  implementation:',ROOT/path)
            for path in row['models']:print('  model:',ROOT/path)
            print('  mode:',row['mode'])
    elif a.action=='run':run_video(a.video,a.fresh,a.max_seconds)
    elif a.action=='backend':call('backend_v1/backend.py','--samples','outputs/events','--db','outputs/backend/full_review.sqlite3','--port',a.port,*(['--import-only']if a.import_only else[]))
    elif a.action=='test':
        call('-m','unittest','discover','-s','tests','-q');call('-m','unittest','discover','-s','backend_v1','-p','test_*.py','-q')
    else:p.print_help()
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,subprocess.CalledProcessError)as error:print('ERROR:',error,file=sys.stderr);sys.exit(1)
