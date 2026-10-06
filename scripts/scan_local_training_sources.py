import os,json,time
from pathlib import Path
from collections import Counter
out=Path(__file__).resolve().parents[1]/'outputs/data-audit/full_scan_20261006';out.mkdir(parents=True,exist_ok=False);rows=[];errors=[];counts=Counter();start=time.time()
archive_ext={'.zip','.7z','.rar','.tar','.gz','.tgz'};video_ext={'.mp4','.avi','.mov','.mkv'}
def err(e):errors.append({'path':e.filename,'error':str(e)})
for root,dirs,files in os.walk('/',onerror=err,followlinks=False):
 dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(root,d)) and os.path.join(root,d) not in ['/dev','/System/Volumes','/Volumes/Preboot','/Volumes/Recovery']]
 for n in files:
  counts['files_seen']+=1;p=os.path.join(root,n);ext=Path(n).suffix.lower()
  if ext in archive_ext or ext in video_ext or ext=='.pt' or n in ['data.yaml','dataset.yaml']:
   try:stat=os.stat(p);rows.append({'path':p,'bytes':stat.st_size,'extension':ext});counts[ext]+=1
   except OSError as e:err(e)
 if counts['files_seen']%20000< len(files):
  (out/'progress.json').write_text(json.dumps({'counts':dict(counts),'elapsed_seconds':time.time()-start,'current_directory':root}))
report={'root':'/','counts':dict(counts),'items':rows,'errors':errors,'excluded_paths':['/dev','/System/Volumes (mounted aliases/system volumes)','/Volumes/Preboot','/Volumes/Recovery'],'follow_symlinks':False,'elapsed_seconds':time.time()-start,'status':'metadata inventory; archive contents not automatically reviewed'};(out/'inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'counts':dict(counts),'read_errors':len(errors),'elapsed_seconds':time.time()-start}))
