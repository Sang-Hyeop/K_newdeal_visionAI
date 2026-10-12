from pathlib import Path
import os,time,json,hashlib,traceback
os.environ['YOLO_CONFIG_DIR']='/private/tmp/ppe_optimization_v6'
os.environ['MPLCONFIGDIR']='/private/tmp/ppe_optimization_v6_mpl'
root=Path('/Users/sanghyeopkim/Documents/Codex/2026-10-08/new-chat-3');run=root/'outputs/ppe_manual_960_v6';out=run/'optimization';out.mkdir(exist_ok=True);state=out/'status.json'
def status(stage,**kw):state.write_text(json.dumps({'stage':stage,**kw},ensure_ascii=False,indent=2))
status('waiting_for_training_and_initial_comparison')
while True:
 try:s=json.loads((run/'status.json').read_text())
 except (FileNotFoundError,json.JSONDecodeError):time.sleep(30);continue
 if s['state'].startswith('failed'):status('blocked_by_training_failure',training=s);raise SystemExit(1)
 if s['state'].startswith('complete'):break
 time.sleep(30)
try:
 import torch
 from PIL import Image
 from ultralytics import YOLO
 torch.set_num_threads(4)
 data=Path('/Users/sanghyeopkim/Desktop/workspace/data/reviewed_pilot/ppe_color_expansion_v3');weights=run/'fit/weights/best.pt';previous=root/'outputs/ppe_manual_corrected_v5/fit/weights/best.pt';model=YOLO(str(weights));grid=[.10,.15,.20,.25,.30,.35,.40,.45,.50,.60,.70,.80]
 def iou(a,b):
  v=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return v/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-v)
 def predictions(m,split,size):
  records=[]
  for p in sorted((data/split/'images').iterdir()):
   if not p.is_file():continue
   w,h=Image.open(p).size;gt=[]
   for line in (data/split/'labels'/(p.stem+'.txt')).read_text().splitlines():
    c,x,y,bw,bh=map(float,line.split());gt.append((int(c),[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]))
   r=m.predict(str(p),imgsz=size,conf=.05,device='cpu',verbose=False)[0]
   pred=[(int(c),b,float(v)) for c,b,v in zip(r.boxes.cls.cpu().tolist(),r.boxes.xyxy.cpu().tolist(),r.boxes.conf.cpu().tolist())];records.append({'image':p.name,'gt':gt,'pred':pred})
  return records
 def score(records,thresholds):
  stats={c:{'TP':0,'FP':0,'FN':0} for c in [0,1]}
  for r in records:
   used=set()
   for c,b,conf in sorted(r['pred'],key=lambda x:-x[2]):
    if conf<thresholds[c]:continue
    match=max([(iou(b,g),i) for i,(gc,g) in enumerate(r['gt']) if gc==c and i not in used],default=(0,-1))
    if match[0]>=.5:used.add(match[1]);stats[c]['TP']+=1
    else:stats[c]['FP']+=1
   for i,(c,b) in enumerate(r['gt']):
    if i not in used:stats[c]['FN']+=1
  for c,s in stats.items():
   tp,fp,fn=s['TP'],s['FP'],s['FN'];s.update(precision=tp/max(1,tp+fp),recall=tp/max(1,tp+fn),f1=2*tp/max(1,2*tp+fp+fn))
  return {'classes':stats,'macro_f1':sum(s['f1'] for s in stats.values())/2,'total':{k:sum(s[k] for s in stats.values()) for k in ['TP','FP','FN']}}
 status('tuning_on_validation_only');search=[]
 for size in [640,960,1280]:
  records=predictions(model,'val',size);thresholds=[]
  for c in [0,1]:
   choices=[(t,score(records,[t,t])['classes'][c]) for t in grid]
   best=max(choices,key=lambda x:(x[1]['f1'],x[1]['recall'],x[1]['precision'],-x[0]));thresholds.append(best[0])
  search.append({'imgsz':size,'thresholds':thresholds,'validation':score(records,thresholds),'default_validation':score(records,[.25,.25])})
 chosen=max(search,key=lambda x:(x['validation']['macro_f1'],-x['imgsz']));status('evaluating_frozen_settings_on_test',chosen=chosen)
 test={}
 for name,m,size,thresholds in [('previous_v5_default',YOLO(str(previous)),640,[.25,.25]),('v6_default',model,960,[.25,.25]),('v6_validation_selected',model,chosen['imgsz'],chosen['thresholds'])]:
  test[name]={'imgsz':size,'thresholds':thresholds,'test':score(predictions(m,'test',size),thresholds)}
 report={'selection':'Maximize macro class F1 on validation12 only; thresholds maximize each class F1. Tie: recall, precision, lower threshold; resolution tie prefers smaller size. Test9 never used for selection.','scope':'Small development validation/test, historical baseline exposure possible; not independent generalization. Hood-only heads follow user no_helmet_head policy. Unannotated indistinguishable heads are not verified FN ground truth.','model_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),'validation_search':search,'selected':chosen,'test_comparison':test}
 (out/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(out/'candidate_config.json').write_text(json.dumps({'model':str(weights),'imgsz':chosen['imgsz'],'candidate_conf':min(chosen['thresholds']),'class_confidence_thresholds':{'helmeted_head':chosen['thresholds'][0],'no_helmet_head':chosen['thresholds'][1]},'usage':'Predict at candidate_conf, then filter boxes by class confidence. Experimental configuration; not applied to deployed pipeline.'},ensure_ascii=False,indent=2));status('complete_experimental_not_deployed',selected=chosen,test_comparison=test);print('OPTIMIZATION_COMPLETE',flush=True)
except BaseException as e:
 status('failed',error=repr(e));traceback.print_exc();raise
