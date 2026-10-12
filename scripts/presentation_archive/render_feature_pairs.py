from pathlib import Path
import cv2,json,zipfile
from PIL import Image,ImageDraw,ImageFont
B=Path('/Users/sanghyeopkim/Desktop/workspace');O=Path.cwd()/'outputs/project_4_features_8_frames';O.mkdir(parents=True,exist_ok=True)
font='/System/Library/Fonts/AppleSDGothicNeo.ttc'
def read(rel):return [json.loads(l) for l in (B/rel).read_text().splitlines()]
def raw(source,t):
 cap=cv2.VideoCapture(str(source));fps=cap.get(cv2.CAP_PROP_FPS);fi=round(t*fps);cap.set(cv2.CAP_PROP_POS_FRAMES,fi);ok,a=cap.read();cap.release();assert ok;return Image.fromarray(cv2.cvtColor(a,cv2.COLOR_BGR2RGB)),fi
P='outputs/diagnostics/demo_object_recall_bundle_v1/forward';Z='outputs/diagnostics/scenario_ppe_warning_preserved/video7';H='outputs/checkpoints/ppe_recall_specialists_v1_final/ppe5_integrated'
pr=read(P+'/observations.jsonl')[15];zr=read(Z+'/zone_access/observations_v1.jsonl')[113];dr=read(Z+'/zone_dwell/observations_v1.jsonl')[126];hr=read(H+'/observations_v1.jsonl')[8]
zconfig=json.loads((B/'configs/cameras/warehouse-summary.json').read_text());poly=zconfig['monitor_floor_normalized'];safe_polys=zconfig['safe_polygons_normalized']
specs=[('01_proximity','작업자 · 지게차 위험 접근 감지','영상 평면의 근접 경고 · 실제 거리(m) 아님',B/'data/videos/1_forklift_forward.mp4',pr),('02_zone_intrusion','위험구역 침범 감지','7번 영상의 기존 통로 ROI · 차량 검출 시 침범 주의',B/'data/videos/7_Logistics Warehouse.mp4',zr),('03_roi_dwell','ROI 체류시간','7번 영상의 기존 통로 ROI · 차량 검출 + 3초 이상 체류 시 위험',B/'data/videos/7_Logistics Warehouse.mp4',dr),('04_ppe_helmet','PPE · 안전모 착용 감지','기존 모델의 안전모 검출 결과',B/'data/videos/5_PPE_Helmet.mp4',hr)]
def lane_policy(inside, vehicle_present, dwell_seconds):
 if inside is None:return {'access':'UNKNOWN','dwell':'UNKNOWN'}
 if not inside:return {'access':'NORMAL','dwell':'NORMAL'}
 if vehicle_present is None:return {'access':'UNKNOWN','dwell':'UNKNOWN'}
 return {'access':'CAUTION' if vehicle_present else 'NORMAL','dwell':('DANGER' if dwell_seconds>=3 else 'CAUTION') if vehicle_present else ('CAUTION' if dwell_seconds>=3 else 'NORMAL')}
assert lane_policy(True,False,0)=={'access':'NORMAL','dwell':'NORMAL'}
assert lane_policy(True,False,3)=={'access':'NORMAL','dwell':'CAUTION'}
assert lane_policy(True,True,0)=={'access':'CAUTION','dwell':'CAUTION'}
assert lane_policy(True,True,3)=={'access':'CAUTION','dwell':'DANGER'}

meta=[]
for stem,title,sub,src,row in specs:
 t=row['timestamp_seconds'];im,fi=raw(src,t);im.save(O/(stem+'_original.png'));a=im.convert('RGBA');W,Hh=a.size;s=W/1280;d=ImageDraw.Draw(a)
 def f(n):return ImageFont.truetype(font,max(12,round(n*s)))
 def label(x,y,txt,col=(255,191,55),size=19):
  ft=f(size);bb=d.textbbox((0,0),txt,font=ft);w=bb[2]+16*s;h=(size+12)*s;x=max(3,min(x,W-w-3));y=max(96*s,min(y,Hh-h-3));d.rounded_rectangle((x,y,x+w,y+h),radius=4*s,fill=(12,19,31,235));d.text((x+8*s,y+3*s),txt,font=ft,fill=col)
 def box(bb,txt,col):
  x1,y1,x2,y2=bb;d.rectangle(bb,outline=col,width=max(3,round(3*s)));label(x1,y1-34*s,txt,col)
 if stem.startswith(('02','03')):
  ov=Image.new('RGBA',a.size);od=ImageDraw.Draw(ov);pts=[(x*W,y*Hh) for x,y in poly];od.polygon(pts,fill=(255,90,60,35));
  for safe in safe_polys:
   sp=[(x*W,y*Hh) for x,y in safe];od.polygon(sp,fill=(0,0,0,0));od.line(sp+[sp[0]],fill=(76,230,158,220),width=round(2*s))
  od.line(pts+[pts[0]],fill=(255,173,51,255),width=round(4*s));a=Image.alpha_composite(a,ov);d=ImageDraw.Draw(a)
 if stem.startswith('01'):
  e=next(e for e in row['events'] if e['severity']=='WARNING');col=(255,191,55);box(e['person_bbox_xyxy'],'작업자  |  접근 주의',col);box(e['forklift_bbox_xyxy'],'지게차', (60,211,255));p=e['person_anchor_xy'];q=e['nearest_vehicle_point_xy'];d.line([tuple(p),tuple(q)],fill=col,width=round(4*s));
  for x,y in [p,q]:d.ellipse((x-5*s,y-5*s,x+5*s,y+5*s),fill=col)
  label((p[0]+q[0])/2,(p[1]+q[1])/2,'근접 경고',col,22)
 elif stem.startswith(('02','03')):
  is_dwell=stem.startswith('03');mode='dwell' if is_dwell else 'access'
  colors={'NORMAL':(76,230,158),'CAUTION':(255,191,55),'DANGER':(255,91,91),'UNKNOWN':(190,198,210)}
  words={'NORMAL':'정상','CAUTION':'주의','DANGER':'위험','UNKNOWN':'확인 불가'}
  states={};vehicles={};drawn=set();used_labels=[]
  for event in row['events']:
   ev=event['evidence'];tid=ev.get('track_id')
   if not tid or tid in states:continue
   current=[v for v in ev.get('vehicle_evidence',[]) if v.get('age_seconds')==0]
   for v in current:vehicles[v['track_id']]=v
   confirmed=event.get('observation_status')=='confirmed'
   if not confirmed:continue  # Presentation: show only confirmed observations.
   inside=ev.get('inside');dwell=ev.get('observed_dwell_seconds',0)
   present=True if ev.get('vehicle_lane_state')=='observed_in_lane' and current else (False if ev.get('vehicle_absence_confirmed') else None)
   status=lane_policy(inside,present,dwell)[mode] if confirmed else 'UNKNOWN'
   states[tid]=status;bb=ev.get('person_bbox_xyxy')
   if bb is None:continue
   drawn.add(tid);col=colors[status];x1,y1,x2,y2=bb
   if confirmed:d.rectangle(bb,outline=col,width=max(3,round(3*s)))
   else:
    # Last known location only; dashed box never claims a current detection.
    for y in range(round(y1),round(y2),round(14*s)):
     d.line((x1,y,x1,min(y+7*s,y2)),fill=col,width=round(2*s));d.line((x2,y,x2,min(y+7*s,y2)),fill=col,width=round(2*s))
    for x in range(round(x1),round(x2),round(14*s)):
     d.line((x,y1,min(x+7*s,x2),y1),fill=col,width=round(2*s));d.line((x,y2,min(x+7*s,x2),y2),fill=col,width=round(2*s))
   short='P'+tid.split(':')[-1]
   detail=(f' · {dwell:.1f}초' if is_dwell and inside and confirmed else (' · 통로 밖' if inside is False and confirmed else ''))
   txt=f'{short} · {words[status]}{detail}'
   if not confirmed:txt+=' (추적 불확실)'
   tx=max(3,min(x1,W-350*s));ty=max(96*s,y1-30*s)
   tw=d.textbbox((0,0),txt,font=f(16))[2]+16*s;th=28*s
   for _ in range(8):
    rect=(tx,ty,tx+tw,ty+th)
    if not any(rect[0]<r[2] and rect[2]>r[0] and rect[1]<r[3] and rect[3]>r[1] for r in used_labels):break
    ty+=30*s
   used_labels.append((tx,ty,tx+tw,ty+th));label(tx,ty,txt,col,16)
  # Each vehicle is drawn once, using current-frame evidence only.
  kept=[]
  for tid,v in sorted(vehicles.items(),key=lambda it:(it[1]['bbox_xyxy'][2]-it[1]['bbox_xyxy'][0])*(it[1]['bbox_xyxy'][3]-it[1]['bbox_xyxy'][1])):
   bb=v['bbox_xyxy'];area=(bb[2]-bb[0])*(bb[3]-bb[1])
   duplicate=False
   for _,old in kept:
    ob=old['bbox_xyxy'];inter=max(0,min(bb[2],ob[2])-max(bb[0],ob[0]))*max(0,min(bb[3],ob[3])-max(bb[1],ob[1]));oa=(ob[2]-ob[0])*(ob[3]-ob[1])
    if inter/max(1,min(area,oa))>.8:duplicate=True
   if duplicate:continue
   kept.append((tid,v));d.rectangle(bb,outline=(60,211,255),width=round(2*s))
  vehicles=dict(kept)
  counts={st:sum(v==st for v in states.values()) for st in colors}
  x=W*.66;y=Hh*.15;d.rounded_rectangle((x,y,x+W*.32,y+Hh*.23),radius=12*s,fill=(12,19,31,235))
  d.text((x+18*s,y+12*s),'작업자별 체류시간 판정' if is_dwell else '작업자별 통로 침범 판정',font=f(25),fill='white')
  d.text((x+18*s,y+52*s),f"정상 {counts['NORMAL']}  ·  주의 {counts['CAUTION']}  ·  위험 {counts['DANGER']}",font=f(23),fill=(255,191,55))
  d.text((x+18*s,y+88*s),'통로 내 차량 검출 · 확인된 작업자 기준',font=f(18),fill=(190,204,222))
  d.text((x+18*s,y+122*s),'차량 있음: 진입 즉시 주의 · 체류 3초부터 위험' if is_dwell else '통로 밖 정상 · 통로 안 + 차량 있음 주의',font=f(16),fill=(190,204,222))
  if counts['UNKNOWN'] and len(drawn)<len(states):label(W*.66,Hh*.41,'박스 없음 · 위치 확인 불가: '+', '.join('P'+tid.split(':')[-1] for tid in states if tid not in drawn),colors['UNKNOWN'],16)
  row['displayed_person_states']=states;row['displayed_current_vehicle_ids']=list(vehicles)
 else:
  seen=set()
  for e in row['events']:
   ev=e.get('evidence',{});tid=ev.get('track_id');heads=ev.get('head_candidates',[])
   if ev.get('ppe_state')!='helmet_detected' or tid in seen:continue
   hs=[h for h in heads if h['class']=='helmeted_head']
   if not hs:continue
   seen.add(tid);h=max(hs,key=lambda h:h['confidence']);box(ev['person_bbox_xyxy'],'안전모 착용',(76,230,158));d.rectangle(h['bbox_xyxy'],outline=(76,230,158),width=round(3*s))
  label(W*.57,Hh*.83,f'안전모 착용 확인  {len(seen)}명',(76,230,158),24)
 d.rectangle((0,0,W,87*s),fill=(10,18,30,245));d.text((22*s,10*s),title,font=f(29),fill='white');d.text((22*s,48*s),sub,font=f(17),fill=(190,204,222));stamp=f'{t:.2f}s';d.text((W-115*s,24*s),stamp,font=f(22),fill=(190,204,222))
 a.convert('RGB').save(O/(stem+'_annotated.png'))
 meta.append(dict(feature=stem,source_video=str(src),frame_index=fi,timestamp_seconds=t,observation=row,display_policy='User corrected vehicle-lane rule: vehicle absent access NORMAL; dwell >=3 CAUTION cap; vehicle present access CAUTION, dwell >=3 DANGER. Historical severity not reused for ROI images. Video7 existing configured floor minus safe polygons; current confirmed vehicle detections and tracked person dwell are used. No vehicle-absence assumption.' if stem.startswith(('02','03')) else 'Existing observations'))
(Path.cwd()/'outputs/project_4_features_evidence.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
# A viewing aid, kept outside the eight-frame package.
sh=Image.new('RGB',(1600,2000),(235,239,245));sd=ImageDraw.Draw(sh)
for i,(stem,title,*_) in enumerate(specs):
 sd.text((18,i*500+10),title,font=ImageFont.truetype(font,25),fill=(20,30,45))
 for j,kind in enumerate(['original','annotated']):
  v=Image.open(O/(stem+'_'+kind+'.png'));v.thumbnail((785,440));sh.paste(v,(j*800+(800-v.width)//2,i*500+48))
sh.save(Path.cwd()/'outputs/project_4_features_comparison.jpg',quality=95)
with zipfile.ZipFile(Path.cwd()/'outputs/project_4_features_8_frames.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(O.glob('*.png')):z.write(p,p.name)
print('saved',len(list(O.glob('*.png'))),'frames')
