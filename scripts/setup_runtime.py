"""Download verified GitHub Release runtime assets; Python standard library only."""
import argparse,hashlib,json,os,shutil,sys,tempfile,urllib.request,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def targets(root,config):
    result={}
    for item in config['files']:
        p=PurePosixPath(item['path'])
        if p.is_absolute() or '..'in p.parts or '\\'in item['path'] or not p.parts or p.parts[0]not in {'models','outputs'} or item['path']in {'models/README.md','outputs/README.md'}:raise ValueError('Invalid runtime asset path: '+item['path'])
        target=root.joinpath(*p.parts)
        if not target.resolve().is_relative_to(root.resolve()):raise ValueError('Asset escapes repository: '+item['path'])
        if item['path']in result:raise ValueError('Duplicate asset: '+item['path'])
        result[item['path']]=(target,item)
    return result

def install_archive(root,config,archive,replace=False):
    if Path(archive).stat().st_size!=config['bytes'] or digest(archive)!=config['sha256']:raise ValueError('Release ZIP checksum mismatch')
    selected=targets(root,config);pending=[]
    for name,(target,item)in selected.items():
        same=target.is_file()and target.stat().st_size==item['bytes']and digest(target)==item['sha256']
        if target.exists()and not same and not replace:raise ValueError('Existing file differs; preserved: '+name+' (use --replace only if intended)')
        if not same:pending.append(name)
    with zipfile.ZipFile(archive)as z:
        if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(selected):raise ValueError('Release ZIP member list differs from manifest')
        for name in pending:
            target,item=selected[name];info=z.getinfo(name)
            if (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Symlink assets are not accepted')
            target.parent.mkdir(parents=True,exist_ok=True)
            fd,temp=tempfile.mkstemp(prefix='.runtime-',dir=target.parent);os.close(fd)
            try:
                with z.open(name)as src,open(temp,'wb')as dst:shutil.copyfileobj(src,dst)
                if Path(temp).stat().st_size!=item['bytes']or digest(temp)!=item['sha256']:raise ValueError('Extracted asset checksum mismatch: '+name)
                os.replace(temp,target)
            finally:
                if Path(temp).exists():Path(temp).unlink()
    return len(pending),len(selected)-len(pending)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--replace',action='store_true',help='Explicitly replace different local runtime assets');p.add_argument('--archive',type=Path,help='Use an already downloaded ZIP');a=p.parse_args()
    config=json.loads((ROOT/'configs/github-runtime.json').read_text(encoding='utf-8'));targets(ROOT,config)
    archive=a.archive.resolve()if a.archive else ROOT/'outputs/runtime_download'/config['url'].rsplit('/',1)[1]
    if not a.archive and (not archive.is_file()or archive.stat().st_size!=config['bytes']or digest(archive)!=config['sha256']):
        archive.parent.mkdir(parents=True,exist_ok=True);partial=archive.with_suffix('.partial')
        print('Downloading GitHub Release:',config['url'],flush=True)
        try:
            request=urllib.request.Request(config['url'],headers={'User-Agent':'Siseon-runtime-setup/1.0'})
            with urllib.request.urlopen(request,timeout=120)as source,partial.open('wb')as dest:shutil.copyfileobj(source,dest)
            if partial.stat().st_size!=config['bytes']or digest(partial)!=config['sha256']:raise ValueError('Downloaded ZIP checksum mismatch')
            os.replace(partial,archive)
        finally:
            if partial.exists():partial.unlink()
    installed,existing=install_archive(ROOT,config,archive,a.replace)
    print(f'PASS: installed {installed} assets; {existing} matching existing assets preserved.')
    print('Next: python -m pip install -r requirements-runtime.txt')
    print('Then: python handoff.py check --models')
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,zipfile.BadZipFile)as error:print('ERROR:',error,file=sys.stderr);sys.exit(1)
