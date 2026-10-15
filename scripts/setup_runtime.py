"""Download verified GitHub Release runtime assets; Python standard library only."""
import argparse,hashlib,json,os,shutil,sys,tempfile,urllib.request,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def asset_path(root,name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..'in p.parts or '\\'in name or not p.parts or p.parts[0]not in {'models','outputs'} or name in {'models/README.md','outputs/README.md'}:
        raise ValueError('Invalid runtime asset path: '+name)
    target=root.joinpath(*p.parts)
    if not target.resolve().is_relative_to(root.resolve()):raise ValueError('Asset escapes repository: '+name)
    return target

def targets(root,config):
    result={};destinations=set()
    for item in config['files']:
        name=item.get('archive_path',item['path'])
        asset_path(root,name)
        target=asset_path(root,item['path'])
        if name in result or target.resolve() in destinations:raise ValueError('Duplicate asset: '+name)
        result[name]=(target,item);destinations.add(target.resolve())
    # Never delete another member's destination while migrating old paths.
    for name,(target,item)in result.items():
        if name!=item['path'] and asset_path(root,name).resolve() in destinations:raise ValueError('Archive path overlaps another destination: '+name)
    return result

def install_archive(root,config,archive,replace=False):
    if Path(archive).stat().st_size!=config['bytes'] or digest(archive)!=config['sha256']:raise ValueError('Release ZIP checksum mismatch')
    selected=targets(root,config);pending=[]
    for name,(target,item)in selected.items():
        override=config.get('local_presentation_overrides',{}).get(item['path'],{})
        if override.get('disabled_by_presentation_selection') and not target.exists():continue
        if override.get('sha256') and target.is_file() and target.stat().st_size==override['bytes'] and digest(target)==override['sha256']:continue
        same=target.is_file()and target.stat().st_size==item['bytes']and digest(target)==item['sha256']
        if target.exists()and not same and not replace:raise ValueError('Existing file differs; preserved: '+item['path']+' (use --replace only if intended)')
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
    # Migrate only verified duplicates after every required asset installed.
    for name,(target,item)in selected.items():
        if name==item['path']:continue
        legacy=asset_path(root,name)
        if legacy.is_file() and not legacy.is_symlink():
            if legacy.stat().st_size==item['bytes'] and digest(legacy)==item['sha256']:
                legacy.unlink();parent=legacy.parent
                while parent!=root and parent.is_dir() and not any(parent.iterdir()):
                    previous=parent;parent=parent.parent;previous.rmdir()
            else:print('Preserved different legacy file:',name)
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
    print('Then: python handoff.py refresh')
    print('Finally: python handoff.py check --models')
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,zipfile.BadZipFile)as error:print('ERROR:',error,file=sys.stderr);sys.exit(1)
