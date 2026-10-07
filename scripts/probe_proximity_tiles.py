from pathlib import Path
import os,json,cv2,torch
r=Path(__file__).resolve().parents[1];os.environ['YOLO_CONFIG_DIR']=str(r/'outputs/runtime/yolo')
from ultralytics import YOLO
torch.set_num_threads(4);m=YOLO(str(r/'models/pilot_v15_scaled_filtered/person_forklift.pt'));root=r/'outputs/diagnostics/proximity_gaps_20261007';base=json.loads((root/'report.json').read_text());out=root/'tiles';out.mkdir(exist_ok=False);report=[]
for row in base['rows']:
 cap=cv2.VideoCapture(str(r/'data/videos'/row['source']));cap.set(cv2.CAP_PROP_POS_FRAMES,row['frame_index']);ok,im=cap.read();cap.release();assert ok;h,w=im.shape[:2];side=round(min(w,h)*.8);xs=list(range(0,max(1,w-side),max(1,round(side*.75))));ys=list(range(0,max(1,h-side),max(1,round(side*.75))));xs=sorted(set(xs+[w-side]));ys=sorted(set(ys+[h-side]));boxes=[]
 for y in ys:
  for x in xs:
   pred=m.predict(im[y:y+side,x:x+side],conf=.1,imgsz=640,device='cpu',verbose=False)[0]
   for b in pred.boxes:
    if int(b.cls.item())!=1:continue
    a,c,d,e=b.xyxy[0].tolist();boxes.append({'confidence':float(b.conf.item()),'bbox_xyxy':[a+x,c+y,d+x,e+y],'tile_xyxy':[x,y,x+side,y+side],'tile_edge_clipped':a<=1 or c<=1 or d>=side-1 or e>=side-1})
 canvas=im.copy()
 for b in sorted(boxes,key=lambda b:b['confidence']):
  a,c,d,e=map(round,b['bbox_xyxy']);cv2.rectangle(canvas,(a,c),(d,e),(0,220,255),2);cv2.putText(canvas,f"F {b['confidence']:.2f} clip={b['tile_edge_clipped']}",(a,max(25,c)),0,.55,(0,220,255),2)
 cv2.putText(canvas,f"tile probe {row['source']} {row['timestamp_seconds']:.2f}s",(10,25),0,.7,(0,220,255),2);cv2.imwrite(str(out/f"{row['source'].split('.')[0]}_{row['frame_index']}.jpg"),canvas);report.append({'source':row['source'],'frame_index':row['frame_index'],'timestamp_seconds':row['timestamp_seconds'],'tile_count':len(xs)*len(ys),'forklift_proposals':boxes});print(row['source'],round(row['timestamp_seconds'],2),[(round(b['confidence'],2),list(map(round,b['bbox_xyxy'])),b['tile_edge_clipped']) for b in boxes],flush=True)
(out/'report.json').write_text(json.dumps({'status':'diagnostic_only_not_promoted','same_weights':base['weights_sha256'],'confidence':.1,'tile_side_ratio':.8,'overlap_ratio':.25,'rows':report,'limitations':'Duplicate and clipped proposals not fused; no end-to-end accuracy'},indent=2))
