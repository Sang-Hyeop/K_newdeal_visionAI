"""Extract diverse train-video candidates; unlabelled frames are not training data."""
from pathlib import Path
import json,hashlib,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1]
def fingerprint(im):return cv2.resize(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY),(96,54)).astype(np.float32)
def main():
 out=ROOT/'data/training_review/related_forklift_v1'
 if out.exists():raise ValueError('Existing candidates protected')
 out.mkdir(parents=True)
 inventory=json.loads((ROOT/'outputs/data-audit/full_scan_20261006/inventory.json').read_text())['items'];sources=sorted({x['path'] for x in inventory if x['extension']=='.mp4' and 'safe_unsafe_behaviours' in x['path'] and '/train/' in x['path'] and Path(x['path']).parent.name in ['3_carrying_overload_with_forklift','7_safe_carrying']})
 demo_hashes={hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/videos').glob('*.mp4')};demo=[]
 for name in ['1_forklift_forward.mp4','2_forklift_back.mp4','3_forklift_crush.mp4']:
  cap=cv2.VideoCapture(str(ROOT/'data/videos'/name));fps=cap.get(5);n=int(cap.get(7))
  for i in range(0,n,max(1,round(fps))):
   cap.set(cv2.CAP_PROP_POS_FRAMES,i);ok,im=cap.read()
   if ok:demo.append((name,i,fingerprint(im)))
  cap.release()
 rows=[];holds=[]
 for source in sources:
  path=Path(source);sha=hashlib.sha256(path.read_bytes()).hexdigest()
  if sha in demo_hashes:holds.append({'source':source,'reason':'identical_demo_file'});continue
  cap=cv2.VideoCapture(source);fps=cap.get(5);n=int(cap.get(7));pending=[]
  if fps<=0 or n<1:holds.append({'source':source,'reason':'invalid_video'});cap.release();continue
  for fraction in [.15,.5,.85]:
   idx=round((n-1)*fraction);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,im=cap.read()
   if not ok:continue
   fp=fingerprint(im);scores=[float(np.mean(np.abs(fp-d[2]))) for d in demo];best=int(np.argmin(scores));stem=f'{path.parent.name.split("_")[0]}_{path.stem}_{idx}';row={'source':source,'source_sha256':sha,'video_group':path.stem,'class_folder':path.parent.name,'frame_index':idx,'timestamp_seconds':idx/fps,'image':stem+'.jpg','resolution':list(im.shape[:2][::-1]),'closest_demo':{'source':demo[best][0],'frame_index':demo[best][1],'gray_mae':scores[best]},'training_eligible':False,'status':'unlabelled_pending_visual_review_and_duplicate_check'};pending.append((row,im))
  cap.release()
  if any(row['closest_demo']['gray_mae']<4 for row,im in pending):holds.append({'source':source,'reason':'possible_demo_overlap_requires_review','nearest_matches':[row['closest_demo'] for row,im in pending]});continue
  for row,im in pending:
   row['candidate_id']=len(rows)+1;cv2.imwrite(str(out/row['image']),im);rows.append(row)
 for start in range(0,len(rows),12):
  sheet=np.full((864,1536,3),245,np.uint8)
  for i,row in enumerate(rows[start:start+12]):
   im=cv2.imread(str(out/row['image']));im=cv2.resize(im,(512,288));cv2.putText(im,f"C{row['candidate_id']} {Path(row['source']).stem} t={row['timestamp_seconds']:.1f}",(8,25),0,.65,(0,255,255),2);x=i%3*512;y=i//3*216;im=cv2.resize(im,(512,216));sheet[y:y+216,x:x+512]=im
  cv2.imwrite(str(out/f'page_{start//12+1:02}.jpg'),sheet)
 (out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(out/'holds.json').write_text(json.dumps(holds,ensure_ascii=False,indent=2));summary={'train_video_files_found':len(sources),'frames_extracted':len(rows),'videos_retained':len({row['source_sha256'] for row in rows}),'held_videos':len(holds),'training_started':False,'labels_available':False,'limitations':'Sparse gray-frame similarity screen is not proof of no overlapping events; visual review required; same-camera adaptation, not unseen-site validation'};(out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__':main()
