from pathlib import Path
import json,cv2,numpy as np
r=Path(__file__).resolve().parents[1];out=r/'data/training_review/related_forklift_v1';rows=json.loads((out/'manifest.json').read_text());sources=sorted({x['source'] for x in rows});refs=[]
def fp(im):return cv2.resize(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY),(64,36)).astype(np.float32)
for name in ['1_forklift_forward.mp4','2_forklift_back.mp4','3_forklift_crush.mp4']:
 cap=cv2.VideoCapture(str(r/'data/videos'/name));fps=cap.get(5);n=int(cap.get(7))
 for i in range(0,n,max(1,round(fps/2))):
  cap.set(cv2.CAP_PROP_POS_FRAMES,i);ok,im=cap.read()
  if ok:refs.append((name,i,fp(im)))
 cap.release()
stack=np.stack([x[2] for x in refs]);report=[]
for source in sources:
 cap=cv2.VideoCapture(source);fps=cap.get(5);n=int(cap.get(7));best=(1e9,None,None)
 for i in range(0,n,max(1,round(fps/2))):
  cap.set(cv2.CAP_PROP_POS_FRAMES,i);ok,im=cap.read()
  if not ok:continue
  dist=np.abs(stack-fp(im)).mean((1,2));j=int(dist.argmin())
  if float(dist[j])<best[0]:best=(float(dist[j]),i,j)
 cap.release();j=best[2];report.append({'source':source,'min_gray_mae':best[0],'source_frame_index':best[1],'closest_demo':{'source':refs[j][0],'frame_index':refs[j][1]} if j is not None else None,'hold':best[0]<4});print(Path(source).name,round(best[0],2),'HOLD' if best[0]<4 else 'candidate',flush=True)
(out/'overlap_audit.json').write_text(json.dumps({'sampling_fps':2,'threshold':4,'status':'conservative_similarity_screen_not_proof_of_event_independence','rows':report},ensure_ascii=False,indent=2));print('retained',sum(not x['hold'] for x in report),'held',sum(x['hold'] for x in report))
