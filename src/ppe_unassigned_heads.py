"""Track real head evidence independently of body IDs; never invent a body box."""
from src.person_tracker import PersonTracker
from src.ppe_events import PPEEvents
from src.ppe_tiled_inference import iou
from src.ppe_person_crop import head_owner

class UnassignedHeadEvents:
    def __init__(self,fps,policy):
        self.tracker=PersonTracker(fps,target_class='head',namespace='H',expose_current_candidates=policy.get('head_candidate_continuity',False),fuse_score=not policy.get('head_candidate_continuity',False))
        self.events=PPEEvents(policy);self.context_continuity=policy.get('head_candidate_continuity',False)
    def update(self,timestamp,heads,people,shape,scene_cut=False,body_events=None):
        groups=[]
        for head in sorted(heads,key=lambda r:((r.get('source')!='weak_head_context_recheck') if self.context_continuity else True,r['confidence']),reverse=True):
            box=head['bbox_xyxy'];w,h=box[2]-box[0],box[3]-box[1]
            if w<=0 or h<=0 or not .4<=w/h<=2.5:continue
            match=next((g for g in groups if iou(g[0]['bbox_xyxy'],box)>=.35),None)
            if match is None:groups.append([head])
            else:match.append(head)
        detected=[{'class':'head','confidence':g[0]['confidence'],'bbox_xyxy':g[0]['bbox_xyxy']}for g in groups]
        tracks,missing=self.tracker.update(timestamp,detected,shape,scene_cut)
        owned_ids=set()
        for track in tracks:
            group=max(groups,key=lambda g:iou(g[0]['bbox_xyxy'],track['detected_bbox_xyxy']))
            if any(head_owner(h['bbox_xyxy'],people,shape[0]) is not None for h in group):owned_ids.add(track['track_id'])
            classes={h['class']for h in group}
            state='no_helmet_candidate' if classes=={'no_helmet_head'} else 'conflicting_evidence' if len(classes)>1 else 'unknown'
            # An unlinked helmet cannot establish a person's SAFE state.
            track['ppe']={'state':state,'head_candidates':group}
        events,transitions=self.events.update(timestamp,tracks,missing,scene_cut)
        # Keep real head history across body-track loss, but suppress duplicate
        # events while a compatible body is currently observed.
        def retained(e):
            if e['track_id'] not in owned_ids:return True
            if body_events is None or e['severity']!='WARNING':return False
            return not any(b['severity']=='WARNING' and any(iou(a['bbox_xyxy'],h['bbox_xyxy'])>=.35 for a in b.get('head_candidates',[]) for h in e.get('head_candidates',[])) for b in body_events)
        events=[e for e in events if retained(e)]
        transitions=[e for e in transitions if retained(e)]
        for item in events+transitions:
            if 'person_bbox_xyxy' in item:item['head_bbox_xyxy']=item.pop('person_bbox_xyxy')
            item.update(subject_type='head',person_link_status='unconfirmed',scope='independent_head_review_candidate_only' if item['track_id'] in owned_ids else 'unassigned_head_review_candidate_only')
            if item['reason']=='person_not_observed':item['reason']='head_not_observed'
        return events,transitions
