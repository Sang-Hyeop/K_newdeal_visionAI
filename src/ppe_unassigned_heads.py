"""Track real unassigned head evidence without inventing a person bounding box."""
from src.person_tracker import PersonTracker
from src.ppe_events import PPEEvents
from src.ppe_tiled_inference import iou
from src.ppe_person_crop import head_owner

class UnassignedHeadEvents:
    def __init__(self,fps,policy):
        self.tracker=PersonTracker(fps,target_class='head',namespace='H')
        self.events=PPEEvents(policy)
    def update(self,timestamp,heads,people,shape,scene_cut=False):
        groups=[]
        for head in sorted(heads,key=lambda r:r['confidence'],reverse=True):
            box=head['bbox_xyxy'];w,h=box[2]-box[0],box[3]-box[1]
            if w<=0 or h<=0 or not .4<=w/h<=2.5:continue
            match=next((g for g in groups if iou(g[0]['bbox_xyxy'],box)>=.35),None)
            if match is None:groups.append([head])
            else:match.append(head)
        groups=[g for g in groups if not any(head_owner(h['bbox_xyxy'],people,shape[0]) is not None for h in g)]
        detected=[{'class':'head','confidence':g[0]['confidence'],'bbox_xyxy':g[0]['bbox_xyxy']}for g in groups]
        tracks,missing=self.tracker.update(timestamp,detected,shape,scene_cut)
        for track in tracks:
            group=max(groups,key=lambda g:iou(g[0]['bbox_xyxy'],track['detected_bbox_xyxy']))
            classes={h['class']for h in group}
            state='no_helmet_candidate' if classes=={'no_helmet_head'} else 'conflicting_evidence' if len(classes)>1 else 'unknown'
            # An unlinked helmet cannot establish a person's SAFE state.
            track['ppe']={'state':state,'head_candidates':group}
        events,transitions=self.events.update(timestamp,tracks,missing,scene_cut)
        for item in events+transitions:
            if 'person_bbox_xyxy' in item:item['head_bbox_xyxy']=item.pop('person_bbox_xyxy')
            item.update(subject_type='head',person_link_status='unconfirmed',scope='unassigned_head_review_candidate_only')
            if item['reason']=='person_not_observed':item['reason']='head_not_observed'
        return events,transitions
