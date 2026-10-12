from pathlib import Path
import json, hashlib, collections
w=Path('/Users/sanghyeopkim/Desktop/workspace');p=w/'data/reviewed_pilot/forklift_cvat_prepared_v1';o=w/'outputs/diagnostics/forklift_preflight_2026-10-12'
def read(f):return json.loads(f.read_text())
def save(f,v):f.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
flags=read(o/'visual_review_flags.json');excluded={r['image'] for r in flags};rows=read(p/'manifest.json')
for r in rows:
 r['training_eligible']=r['image'] not in excluded
 if not r['training_eligible']:r['exclusion_reason']='동일 지게차의 좌우 마스트만 보이며 두 차량으로 라벨링됨. 차량 단위 학습에서 사진 전체 제외.'
active=[r for r in rows if r['training_eligible']]
assert len(active)==153 and len(excluded)==2
for split in ['train','val','test']:
 selected=[r for r in active if r['split']==split]
 (p/f'{split}.txt').write_text(''.join(r['path']+'\n' for r in selected))
 for r in selected:
  assert Path(r['path']).is_file() and Path(r['label']).is_file()
  assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
  assert '/labels/' in r['label'] and Path(r['label']).stem==Path(r['path']).stem
sets={s:{r['source_group'] for r in active if r['split']==s} for s in ['train','val','test']}
assert not sets['train']&sets['val'] and not sets['train']&sets['test'] and not sets['val']&sets['test']
counts=dict(collections.Counter(r['split'] for r in active));assert counts=={'train':131,'val':11,'test':11} or counts=={'val':11,'train':131,'test':11}
save(p/'manifest.json',rows)
for r in flags:r.update(resolved=True,decision='exclude_entire_image_from_training',labels_modified=False,automatically_excluded=True,resolution='차량 본체 없이 동일 차량의 마스트를 두 인스턴스로 표시한 사진. 원본 보관, 학습 목록에서 제외.')
save(o/'visual_review_flags.json',flags)
plan=read(p/'training_plan.json');plan.update(status='ready_not_started',requires_review=[],excluded_images=sorted(excluded),split_counts=counts);save(p/'training_plan.json',plan)
report=read(o/'preflight.json');report.update(active_images=153,active_boxes=sum(len(r['boxes']) for r in active),split_counts=counts,visual_review_flags=flags,ready_status='ready_not_started',training_started=False,excluded_mast_only_images=2,source_group_overlap=0);save(o/'preflight.json',report)
(w/'docs/forklift-preflight-2026-10-12.md').write_text('''# 지게차 학습 준비 완료 — 2026-10-12

원본 155장/155라벨/190박스 보존. Desktop과 workspace 내용 일치, 전체 파일의 좌표 형식 오류와 동일 파일 중복 없음.
대표 14장 육안 확인 후, 동일 지게차의 좌우 마스트만 두 차량으로 표시한 사진 2장을 원본 크기로 재확인하고 학습 대상에서 제외했다. 라벨을 지워 배경 사진으로 사용하지 않는다. 나머지 전체 사진을 육안 검수했다고 주장하지 않는다.

최종 사용 153장/186박스: 학습 131장, 검증 11장, 시험 11장. 라벨 없는 별도 2장도 검수 보류로 유지한다. 영상 원천 그룹 간 분할 중복 없음. 기존 학습 영상 및 원천을 확인하지 못한 스크린샷은 학습에만 사용한다. 같은 현장과 합성 영상이 포함되어 독립 현장 평가를 의미하지 않는다.

사람 라벨이 없으므로 단일 forklift 보완 모델로 준비했다. 기존 사람/지게차 모델과 기존 시험 50장은 유지한다. 데이터 로더와 초기 모델 클래스 검사 통과. 학습 미실행, 새 모델 자동 적용 없음.

설정: data/reviewed_pilot/forklift_cvat_prepared_v1/dataset.yaml
학습 계획: data/reviewed_pilot/forklift_cvat_prepared_v1/training_plan.json
검수 결과: outputs/diagnostics/forklift_preflight_2026-10-12/preflight.json
평가 기준 2·6·8: 데이터 정의 및 평가 분리, 검수 근거 보관에 기여한다. GitHub 업로드는 사용자 요청에 따라 보류한다.
''')
print(json.dumps({'status':'ready_not_started','images':len(active),'boxes':report['active_boxes'],'splits':counts,'excluded':sorted(excluded),'source_group_overlap':0},ensure_ascii=False))
