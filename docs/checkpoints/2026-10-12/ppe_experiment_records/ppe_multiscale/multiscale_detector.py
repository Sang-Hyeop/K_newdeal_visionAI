"""Experimental multi-scale PPE; no person, tracking or safety decision dependencies."""
CONFIG={'small_imgsz':640,'large_imgsz':1536,'small_conf':.4,'large_conf':.15,'pair_iou':.25,'remaining_iou':.35,'rescue_imgsz':960,'rescue_conf':.15,'rescue_support_conf':.15,'rescue_support_iou':.25}
def iou(a,b):
 intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
 return intersection/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)
def merge(aa,bb):
 kept=[];used=set()
 for a in sorted(aa,key=lambda p:-p['confidence']):
  hit=max([(iou(a['box'],b['box']),i) for i,b in enumerate(bb) if i not in used and a['class']==b['class']],default=(0,-1))
  if hit[0]>=CONFIG['pair_iou']:
   b=bb[hit[1]];used.add(hit[1]);kept.append({**a,'box':[(x+y)/2 for x,y in zip(a['box'],b['box'])],'source':'multiscale_pair'})
  else:kept.append({**a,'source':'small'})
 kept.extend({**b,'source':'large'} for i,b in enumerate(bb) if i not in used and not any(iou(b['box'],p['box'])>=CONFIG['remaining_iou'] for p in kept))
 return kept

def infer(frame,model):
 predictions={}
 for size in [640,960,1536]:
  p=model.predict(frame,imgsz=size,conf=.05,device='cpu',verbose=False)[0]
  predictions[size]=[{'class':int(c),'confidence':float(s),'box':b} for c,s,b in zip(p.boxes.cls.tolist(),p.boxes.conf.tolist(),p.boxes.xyxy.tolist())]
 kept=merge([p for p in predictions[640] if p['confidence']>=.4],[p for p in predictions[1536] if p['confidence']>=.15])
 for p in sorted(predictions[960],key=lambda p:-p['confidence']):
  if p['confidence']<.15 or any(iou(p['box'],q['box'])>=.35 for q in kept):continue
  if any(q['class']==p['class'] and q['confidence']>=.15 and iou(p['box'],q['box'])>=.25 for size in [640,1536] for q in predictions[size]):kept.append({**p,'source':'supported_baseline_rescue'})
 return kept
