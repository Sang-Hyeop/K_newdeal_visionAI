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
        override=manifest.get('local_presentation_overrides',{}).get(item['path'],{})
        p=ROOT/item['path']
        if override.get('disabled_by_presentation_selection'):
            if p.exists():raise ValueError('Disabled feature asset restored; run python handoff.py refresh: '+item['path'])
            continue
        item={**item,**override}
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
    # Presentation IDs match data/videos filenames and configs/demo-scenarios.json video_number.
    common=['scripts/run_demo_scenarios.py','--videos',n,'--sample-fps','5']
    limit=['--max-seconds',max_seconds]if max_seconds is not None else[]
    if n==5 and fresh:
        baseline=dest/'baseline';candidates=dest/'candidates';reviewed=dest/'reviewed_cache'
        call(*common,'--proximity-geometry','bottom_center',*limit,'--output',baseline)
        call('scripts/recover_vehicle_cache.py','--input',baseline/'video5','--output',candidates/'video5','--candidates-only')
        call('scripts/review_vehicle_recovery_cache.py','--input',candidates/'video5','--output',reviewed/'video5')
        call(*common,'--reuse-run',reviewed,'--reuse-objects','--proximity-geometry','bottom_center','--temporal-riders',*limit,'--output',dest/'result')
    else:
        caches={1:'presentation1_equipment_corrected_2026-10-14',3:'presentation3_ppe_review_2026-10-14',4:'presentation4_worker_corrected_final_2026-10-14',5:'presentation5_vehicle_recovery_review_cache_v2_2026-10-14'}
        reuse=[]if fresh else['--reuse-run',Path('outputs/diagnostics')/caches[n],'--reuse-objects']
        geometry=['--proximity-geometry','bottom_center','--temporal-riders']if n==5 else[]
        call(*common,*reuse,*geometry,*limit,'--output',dest)
    print('Result:',ROOT/dest)

def refresh_presentations():
    """Update existing presentation views/events in place from observed caches."""
    import copy, types, sqlite3, shutil
    import cv2, numpy as np
    from src.scenario_selection import presentation_groups,presentation_detections
    from src.scenario_render import render
    from src.feature_status import feature_status
    index=json.loads((ROOT/'configs/team-runtime-index.json').read_text())
    manifest=json.loads((ROOT/'configs/demo-scenarios.json').read_text())
    specs={s.get('presentation_video_number') or s['video_number']:s for s in manifest['scenarios'] if s.get('review_enabled',True)}
    audit=[]
    for video in index['videos']:
        n=video['presentation_video_number']
        if n==2:continue  # intrusion + PPE already matches the user selection
        spec=specs[n];dest=ROOT/video['diagnostic_root'];summary=json.loads((dest/'summary.json').read_text())
        rows=[json.loads(line) for line in (dest/'detections.jsonl').read_text().splitlines()]
        before={k:hashlib.sha256(json.dumps([r['feature_events'].get(k,[]) for r in rows],sort_keys=True).encode()).hexdigest() for k in spec['enabled_features']}
        cfg=json.loads((ROOT/video['camera_config']).read_text());cap=cv2.VideoCapture(str(ROOT/video['source_video']));w,h=int(cap.get(3)),int(cap.get(4));fps=summary['processed_fps']
        pipe=None
        if n in (4,5):
            polygon=cfg.get('polygon_normalized',cfg.get('monitor_floor_normalized'))
            pipe=types.SimpleNamespace(config=cfg,polygon=np.array([[x*w,y*h] for x,y in polygon],np.float32),safe_polygons=[np.array([[x*w,y*h] for x,y in p],np.float32) for p in cfg.get('safe_polygons_normalized',[])])
        temp=dest/'.presentation_edit.mp4';writer=cv2.VideoWriter(str(temp),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h));assert writer.isOpened()
        wanted={row['frame_index']:row for row in rows};idx=0;count=0
        try:
            while True:
                ok,frame=cap.read()
                if not ok:break
                if idx not in wanted:idx+=1;continue
                row=wanted[idx];groups=presentation_groups(row['feature_events'],spec);row['feature_events']=groups;row['features']={k:feature_status(v) for k,v in groups.items()}
                if not spec['ppe_enabled']:
                    row['ppe_tracks']=[];row['head_detections']=[];row.pop('unassociated_ppe_review',None)
                if n==3:row['object_detections']=presentation_detections(row['object_detections'],spec)
                zone=row.get('zone')
                if zone:
                    zone['events']=[e for e in zone['events'] if e['event_type'] in groups]
                    zone['transitions']=[e for e in zone.get('transitions',[]) if e['event_type'] in groups]
                proximity=row.get('proximity_tracking') or {}
                canvas=render(frame.copy(),groups,(pipe,zone) if pipe else None,detections=presentation_detections(row['object_detections'],spec),proximity_warning_ratio=cfg.get('warning_ratio',1.6),include_other_safe_people=True,vehicle_occupancy=proximity.get('vehicle_occupancy'))
                if n==5:
                    for person in proximity.get('people',[]):
                        if person['track_id'] in proximity.get('rider_associations',{}):
                            x,y,_,_=map(int,person['detected_bbox_xyxy']);cv2.putText(canvas,'RIDER / NOT PEDESTRIAN',(x,max(135,y+32)),0,.38,(255,220,80),1)
                cv2.putText(canvas,f"VIDEO {n} / t={row['timestamp_seconds']:.2f}s / DEMO-ADAPTED / METERS UNCALIBRATED",(12,h-14),0,.48,(0,190,255),1)
                writer.write(canvas)
                for p in dest.glob(f'preview_{count}.*'):cv2.imwrite(str(p),canvas)
                count+=1;idx+=1
        finally:cap.release();writer.release()
        assert count==len(rows)
        after={k:hashlib.sha256(json.dumps([r['feature_events'].get(k,[]) for r in rows],sort_keys=True).encode()).hexdigest() for k in spec['enabled_features']};assert before==after,'Retained rule verdicts changed'
        review=ROOT/video['review_video'];encoded=dest/'.presentation_encoded.mp4'
        ff=shutil.which('ffmpeg')
        if ff:
            subprocess.run([ff,'-y','-loglevel','error','-i',str(temp),'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(encoded)],check=True);temp.unlink()
        else:temp.replace(encoded)
        shutil.copy2(encoded,review);encoded.unlink()
        if (dest/'demo.mp4').exists():shutil.copy2(review,dest/'demo.mp4')
        (dest/'detections.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        summary.update(video_number=n,presentation_video_number=n,enabled_features=spec['enabled_features'],ppe_enabled=spec['ppe_enabled'],ppe_final_selected=spec['ppe_enabled'],camera_config=cfg,presentation_updated='2026-10-15',features={k:{state:sum(feature_status(row['feature_events'][k])['display_state']==state for row in rows) for state in ['SAFE','WARNING','CRITICAL','UNKNOWN']} for k in spec['enabled_features']})
        (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        for root in [dest,ROOT/video['event_root']]:
            for name in ['ppe','proximity','zone_access','zone_dwell','forklift_proximity']:
                if name not in spec['enabled_features'] and (root/name).is_dir():shutil.rmtree(root/name)
        video['enabled_features']=spec['enabled_features'];video['display_objects']=['person'] if n in (3,4) else ['person','forklift']
        if n in (1,4):video['models']=[v for v in video['models'] if 'ppe_final' not in v]
        if n==3:video['models']=['models/pretrained/yolo26n.pt','models/ppe_final/ppe_helmet_v6_960.pt']
        # Update the existing run manifest when present, without introducing another run.
        parent=dest.parent/'manifest.json'
        if parent.exists():
            entries=json.loads(parent.read_text())
            if isinstance(entries,list):
                entries=[summary if e.get('presentation_video_number',e.get('video_number')) in (n,spec['video_number']) else e for e in entries];parent.write_text(json.dumps(entries,indent=2)+'\n')
        audit.append(dict(video=n,samples=count,enabled_features=spec['enabled_features'],retained_verdict_hashes=after,review_sha256=hashlib.sha256(review.read_bytes()).hexdigest()))
        print(f'Updated existing video {n}: {spec["enabled_features"]}',flush=True)
    index['videos'][1]['enabled_features']=['zone_access','ppe']
    index['source_summary_transform']='Current presentation feature selection applied; retained rule verdicts unchanged; disabled feature logs removed.'
    (ROOT/'configs/team-runtime-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    db=ROOT/'outputs/backend/full_review.sqlite3'
    if db.exists():
        con=sqlite3.connect(db)
        with con:
            for video in index['videos']:
                enabled=video.get('enabled_features')
                if not enabled:continue
                name=Path(video['source_video']).name;marks=','.join('?' for _ in enabled)
                con.execute(f"DELETE FROM events WHERE video=? AND event_type NOT IN ({marks}) AND NOT (event_type='status' AND COALESCE(json_extract(evidence,'$.feature'),'') IN ({marks}))",[name,*enabled,*enabled])
                con.execute(f'DELETE FROM observations WHERE video=? AND feature NOT IN ({marks})',[name,*enabled])
        con.close()
        from backend_v1.backend import Store
        Store(db).ingest(ROOT/'outputs/events')
    release=ROOT/'configs/github-runtime.json';assets=json.loads(release.read_text());overrides={}
    for item in assets['files']:
        p=ROOT/item['path']
        if not p.exists():overrides[item['path']]={'disabled_by_presentation_selection':True}
        elif p.stat().st_size!=item['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
            overrides[item['path']]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    assets['local_presentation_overrides']=overrides
    release.write_text(json.dumps(assets,indent=2)+'\n')
    return audit

def main():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='action')
    q=subs.add_parser('check',help='Verify bundled SHA-256; optionally run CPU model inference');q.add_argument('--models',action='store_true')
    subs.add_parser('refresh',help='Update existing presentation videos and logs in place from saved observations')
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
            for key in ['source_video','camera_config','object_review_profile','diagnostic_root','review_video','event_root']:
                if row.get(key):print(' ',key+':',ROOT/row[key])
            for path in row['implementation']:print('  implementation:',ROOT/path)
            for path in row['models']:print('  model:',ROOT/path)
            print('  mode:',row['mode'])
    elif a.action=='refresh':refresh_presentations()
    elif a.action=='run':run_video(a.video,a.fresh,a.max_seconds)
    elif a.action=='backend':call('backend_v1/backend.py','--samples','outputs/events','--db','outputs/backend/full_review.sqlite3','--port',a.port,*(['--import-only']if a.import_only else[]))
    elif a.action=='test':
        call('-m','unittest','discover','-s','tests','-q');call('-m','unittest','discover','-s','backend_v1','-p','test_*.py','-q')
    else:p.print_help()
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,subprocess.CalledProcessError)as error:print('ERROR:',error,file=sys.stderr);sys.exit(1)
