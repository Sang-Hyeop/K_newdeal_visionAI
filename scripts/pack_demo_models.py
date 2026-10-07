"""Pack Git-excluded demo weights into a shareable zip with SHA-256 checks."""
from pathlib import Path
import argparse,hashlib,json,zipfile,datetime

ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,default=ROOT/'docs/checkpoints/2026-10-07/model-share-manifest.json');p.add_argument('--output',type=Path);args=p.parse_args()
 manifest=json.loads(args.manifest.read_text());stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
 out=args.output or ROOT/'outputs/checkpoints'/f'demo_models_share_{stamp}.zip'
 out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():raise ValueError('Preserve existing package')
 files=[f for f in manifest['files'] if f.get('present')]
 missing=[f['path'] for f in manifest['files'] if not f.get('present')]
 if missing:raise FileNotFoundError(f'Missing weights: {missing}')
 readme='\n'.join([
  '# Demo model package',
  '',
  f'Branch: {manifest.get("branch")}',
  f'Built: {stamp}',
  f'Runbook: {manifest.get("runbook")}',
  '',
  'Extract into the repo root so paths like models/.../file.pt match.',
  'Verify each file with sha256 from manifest.json inside this zip.',
  '',
  'Files:',
  *[f"- {f['path']}  sha256={f['sha256']}  bytes={f['bytes']}" for f in files],
  '',
 ])
 with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
  z.writestr('README.md',readme)
  z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
  for f in files:
   path=ROOT/f['path'];digest=sha(path)
   if digest!=f['sha256'] or path.stat().st_size!=f['bytes']:
    raise ValueError(f'Hash/size mismatch for {f["path"]}')
   z.write(path,arcname=f['path'])
 package={'package':str(out),'bytes':out.stat().st_size,'sha256':sha(out),'file_count':len(files),'manifest':str(args.manifest)}
 print(json.dumps(package,indent=2))
 (out.with_suffix('.zip.json')).write_text(json.dumps(package,indent=2)+'\n')

if __name__=='__main__':main()
