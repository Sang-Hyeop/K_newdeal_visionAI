"""Current PPE runtime: approved evidence window, stable IDs and guarded upper-body search."""
from pathlib import Path
import json,copy
from src.ppe_person_crop import head_owner
from src.detection_review_profile import exclude_confirmed_equipment
from src.scenario_selection import presentation_detections
ROOT=Path(__file__).resolve().parents[1]

def runtime_config():
 return json.loads((ROOT/'configs/demo-ppe-model.json').read_text())['runtime']

def runtime_version(video=None):
 cfg=runtime_config()
 return cfg.get('fixed_context_version',cfg['version'])if video in cfg.get('fixed_context_videos',[])else cfg['version']

def load_policy():
 policy=json.loads((ROOT/runtime_config()['policy']).read_text())
 return {**policy,'require_baseline_helmet_confirmation':True}

def display_detections(video, detections):
 specs=json.loads((ROOT/'configs/demo-scenarios.json').read_text())['scenarios']
 spec=next(s for s in specs if s['video_number']==video)
 return presentation_detections(detections,spec)

def tracks_from_row(row):
 if row.get('ppe_tracks'):return copy.deepcopy(row['ppe_tracks'])
 tracks=[]
 for e in row['feature_events'].get('ppe', []):
  if e.get('reason')=='person_not_observed' or not e.get('person_bbox_xyxy'):continue
  tracks.append({'track_id':e['track_id'],'detected_bbox_xyxy':list(e['person_bbox_xyxy']),'bbox_xyxy':list(e['person_bbox_xyxy']),'ppe':{'state':e.get('ppe_state','unknown'),'head_candidates':copy.deepcopy(e.get('head_candidates',[])),'rejected_candidates':[]}})
 return tracks

def assign_head_observations(tracks, heads, frame_height):
 updated=copy.deepcopy(tracks);boxes=[t['detected_bbox_xyxy'] for t in updated]
 for i,track in enumerate(updated):
  selected=[copy.deepcopy(q) for q in heads if head_owner(q['bbox_xyxy'],boxes,frame_height,upper_fraction=.35)==i]
  classes={q['class'] for q in selected}
  track['ppe']={'head_candidates':selected,'rejected_candidates':[],'state':'helmet_detected' if classes=={'helmeted_head'} else 'no_helmet_candidate' if classes=={'no_helmet_head'} else 'conflicting_evidence' if len(classes)>1 else 'unknown'}
 return updated

def save_ppe_observations(row, tracks, heads):
 # The persisted cache must contain the exact observations passed into the rule.
 row['ppe_tracks']=copy.deepcopy(tracks)
 row['head_detections']=copy.deepcopy(heads)

def detect_current_heads(model, frame, boxes, policy, review, tag):
 def proposals(raw, source):
  heads=[{'class':model.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'source':source,'model_sources':['baseline',tag]} for q in raw]
  return exclude_confirmed_equipment(heads,frame.shape[:2],review,frame)[0] if review else heads
 fresh=proposals(model.predict(frame),f'{tag}_full_frame');insufficient=[]
 for i,box in enumerate(boxes):
  hs=[q for q in fresh if head_owner(q['bbox_xyxy'],boxes,frame.shape[0],upper_fraction=.35)==i]
  valid={q['class'] for q in hs if q['confidence']>=policy['helmet_evidence_confidence' if q['class']=='helmeted_head' else 'no_helmet_evidence_confidence']}
  if len(valid)!=1:insufficient.append(box)
 if insufficient:fresh+=proposals(model.predict_person_context(frame,insufficient),f'{tag}_person_context')
 return fresh

def conservative_extra_heads(original_heads, extended_heads):
 # Extra crops may add reviewable no-helmet evidence, but cannot alone certify a helmet.
 kept=copy.deepcopy(original_heads);blocked=[]
 for head in extended_heads:
  if head in original_heads:continue
  if head.get('source') not in ('v6_upper_body','experimental_v6_upper_body'):continue
  if head['class']=='helmeted_head':blocked.append(copy.deepcopy(head))
  else:kept.append(copy.deepcopy(head))
 return kept,blocked

def infer_runtime_heads(model,frame,boxes,policy,review,video):
 heads=detect_current_heads(model,frame,boxes,policy,review,'final_v6')
 if video not in runtime_config()['guarded_upper_body_videos']:return heads,[]
 insufficient=[]
 for i,box in enumerate(boxes):
  current=[h for h in heads if head_owner(h['bbox_xyxy'],boxes,frame.shape[0],upper_fraction=.35)==i]
  supported={h['class']for h in current if h['confidence']>=policy['helmet_evidence_confidence'if h['class']=='helmeted_head'else'no_helmet_evidence_confidence']}
  if len(supported)!=1:insufficient.append(box)
 extra=[{'class':model.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'source':'v6_upper_body','model_sources':['baseline','final_v6']}for q in model.predict_upper_body_context(frame,insufficient)]if insufficient else[]
 if review:extra,_=exclude_confirmed_equipment(extra,frame.shape[:2],review,frame)
 kept,blocked=conservative_extra_heads(heads,heads+extra)
 if video in runtime_config().get('fixed_context_videos',[]):
  # Recheck only people still lacking valid evidence after the preceding scale.
  searches=runtime_config().get('fixed_context_search',[{'context_size':320,'imgsz':640,'source':'v6_fixed_context'}])
  for search in searches:
   missing=[]
   for i,box in enumerate(boxes):
    current=[q for q in kept if head_owner(q['bbox_xyxy'],boxes,frame.shape[0],upper_fraction=.35)==i]
    if search.get('requires_head_candidate') and not current:continue
    if not any(q['confidence']>=policy['helmet_evidence_confidence'if q['class']=='helmeted_head'else'no_helmet_evidence_confidence']for q in current):missing.append(box)
   fixed=[]
   for box in missing:
    owner=boxes.index(box)
    for q in model.predict_fixed_context(frame,[box],context_size=search['context_size'],imgsz=search['imgsz']):
     if head_owner(q['box'],boxes,frame.shape[0],upper_fraction=.35)!=owner:continue
     fixed.append({'class':model.model.names[q['class']],'confidence':q['confidence'],'bbox_xyxy':q['box'],'source':search['source'],'model_sources':['baseline','final_v6']})
   if review:fixed,_=exclude_confirmed_equipment(fixed,frame.shape[:2],review,frame)
   # New context alone must never certify helmet wearing.
   blocked.extend(q for q in fixed if q['class']=='helmeted_head')
   kept.extend(q for q in fixed if q['class']=='no_helmet_head')
 return kept,blocked
