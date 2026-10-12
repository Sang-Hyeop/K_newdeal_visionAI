CONFIG={'cover': 0.8, 'overlap': 0.7}
def iou(a,b):
 x=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return x/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-x)

def clean(heads,cover,overlap=.9):
 kept=[]
 for p in sorted(heads,key=lambda p:-p['confidence']):
  a=p['box'];area=max(1e-9,(a[2]-a[0])*(a[3]-a[1]));duplicate=False
  for q in kept:
   if p['class']!=q['class']:continue
   b=q['box'];inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));other=max(1e-9,(b[2]-b[0])*(b[3]-b[1]))
   if iou(a,b)>=overlap or (inter/area>=cover and area<=other*.8):duplicate=True;break
  if not duplicate:kept.append(p)
 return kept
