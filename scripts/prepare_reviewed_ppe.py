"""66개 PPE 후보의 시각 검수 결정을 적용한 별도 시험셋 생성."""
from pathlib import Path
import json, shutil
from collections import Counter
import yaml
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/pilot_v1/ppe'; OUT=ROOT/'data/reviewed_pilot/ppe'
HOLDS={321:'background heads missing',142:'background bare heads missing',358:'blurred background head completeness uncertain',17:'tiny background head missing',90:'left-edge partial helmet missing',139:'bare head mislabeled as helmet and additional heads missing',229:'same scene as val P360',324:'same scene candidate as test P359',359:'blurred head and scene-duplicate candidate',277:'small blurred heads',259:'small blurred heads',315:'extremely small head',81:'second helmet missing and cut boundary ambiguous'}
def main():
 if OUT.exists():raise SystemExit(f'Existing output protected: {OUT}')
 rows=json.loads((SRC/'manifest.json').read_text());decisions=[]
 for r in rows:
  r={**r,'review_method':'640px image views with label overlays; human visual audit','training_eligible':r['id'] not in HOLDS,'reason':HOLDS.get(r['id'],'visible heads and class labels accepted for pilot')}
  if r['training_eligible']:
   for folder in ['images','labels']:(OUT/r['split']/folder).mkdir(parents=True,exist_ok=True)
   shutil.copy2(SRC/r['split']/'images'/r['image'],OUT/r['split']/'images'/r['image'])
   label=SRC/r['split']/'labels'/(Path(r['image']).stem+'.txt');lines=label.read_text().splitlines()
   if r['id']==61:
    assert len(lines)==1 and lines[0].startswith('0 ')
    lines[0]='1 '+lines[0].split(' ',1)[1];r['reason']='corrected bare head class 0 to class 1';r['label_changed']=True
   (OUT/r['split']/'labels'/label.name).write_text('\n'.join(lines)+'\n')
  decisions.append(r)
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'manifest.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2))
 (OUT/'dataset.yaml').write_text(yaml.safe_dump({'path':str(OUT),'train':'train/images','val':'val/images','test':'test/images','names':{0:'helmeted_head',1:'no_helmet_head'}}))
 print(Counter(r['split'] for r in decisions if r['training_eligible']))
if __name__=='__main__':main()
