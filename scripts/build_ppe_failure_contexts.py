"""Short failure-specific refinement: real image contexts, no generated labels."""
from pathlib import Path
import json,shutil,cv2,hashlib,yaml
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'data/reviewed_pilot/ppe_remaining_v2';out=ROOT/'data/reviewed_pilot/ppe_failure_context_v3';review=ROOT/'data/training_review/ppe_remaining_v2'
 if out.exists():raise ValueError('Protected output')
 for s in ['train','val','test']:shutil.copytree(base/s,out/s)
 rows=json.loads((base/'manifest.json').read_text());labels=json.loads((ROOT/'configs/review/ppe-remaining-target-v3.json').read_text());oldlabels=json.loads((ROOT/'configs/review/ppe-remaining-target-v2.json').read_text());oldbyindex={x['index']:x for x in oldlabels};byindex={x['index']:x for x in labels};failed=json.loads((ROOT/'outputs/diagnostics/ppe_remaining_v2_last_crops/report.json').read_text());added=[]
 # Correct annotations only in the new dataset; historical inputs remain intact.
 for row in rows:
  if row.get('index') in byindex and row.get('source')=='5_PPE_Helmet.mp4' and row['image'].startswith('remaining_target_'):
   im=cv2.imread(str(out/'train/images'/row['image']));h,w=im.shape[:2];heads=byindex[row['index']]['boxes_xyxy'];(out/'train/labels'/Path(row['image']).with_suffix('.txt')).write_text('\n'.join(f'{c} {(x+x2)/2/w:.8f} {(y+y2)/2/h:.8f} {(x2-x)/w:.8f} {(y2-y)/h:.8f}'for c,x,y,x2,y2 in heads)+'\n');row['reviewed_boxes_xyxy']=heads;row['review_correction']='v3 native coordinate-grid visual audit: helmet crown and face, neighbouring heads'
 for record in failed['records']:
  source=byindex[record['index']];im=cv2.imread(str(review/source['image']));h,w=im.shape[:2]
  for number,miss in enumerate(record['misses']):
   oldbox=[miss['class_id'],*miss['bbox_xyxy']];oldhead=oldbyindex[record['index']]['boxes_xyxy'].index(oldbox);gt=source['boxes_xyxy'][oldhead];cls,x,y,x2,y2=gt;cx,cy=(x+x2)/2,(y+y2)/2
   for scale in [2.5,4.0]:
    size=max(x2-x,y2-y)*scale;l=max(0,int(cx-size/2));t=max(0,int(cy-size/2));r=min(w,round(cx+size/2));b=min(h,round(cy+size/2));crop=im[t:b,l:r];ch,cw=crop.shape[:2];heads=[]
    for c,a,v,z,q in source['boxes_xyxy']:
     aa,vv,zz,qq=max(a,l),max(v,t),min(z,r),min(q,b)
     if zz>aa and qq>vv and (zz-aa)*(qq-vv)/((z-a)*(q-v))>=.7:heads.append([c,aa-l,vv-t,zz-l,qq-t])
    if not heads:raise ValueError('No reviewed head')
    name=f"failure_context_{record['index']:03d}_{number}_{scale}.jpg";cv2.imwrite(str(out/'train/images'/name),crop);text='\n'.join(f'{c} {(a+z)/2/cw:.8f} {(v+q)/2/ch:.8f} {(z-a)/cw:.8f} {(q-v)/ch:.8f}'for c,a,v,z,q in heads)+'\n';(out/'train/labels'/Path(name).with_suffix('.txt')).write_text(text);row={**source,'image':name,'split':'train','training_eligible':True,'context_parent_image':source['image'],'context_crop_xyxy':[l,t,r,b],'context_scale':scale,'reviewed_boxes_xyxy':heads,'reason':'Fixed-threshold missed head; real pixel context, inherited manually reviewed boxes'};rows.append(row);added.append(row)
 (out/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'dataset.yaml').write_text(yaml.safe_dump({'path':str(out),'train':'train/images','val':'val/images','test':'test/images','names':{0:'helmeted_head',1:'no_helmet_head'}}));(out/'context_manifest.json').write_text(json.dumps(added,indent=2)+'\n');print({'new_real_contexts':len(added),'train':len(list((out/'train/images').glob('*.jpg'))),'native_label_corrections':'v3 reviewed target labels','demo_exposed':True,'old_holdout_bytes_preserved':True})
if __name__=='__main__':main()
