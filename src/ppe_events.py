"""Temporal PPE evidence per observed track; candidates are not proven violations."""
import math

class PPEEvents:
    def __init__(self,config):
        self.frames=config['minimum_consecutive_frames'];self.duration=config['minimum_confirmed_seconds'];self.gap=config['maximum_observation_gap_seconds'];self.conf=config['minimum_head_confidence']
        if self.frames<1 or not all(math.isfinite(v) for v in [self.duration,self.gap,self.conf]) or self.duration<0 or self.gap<=0 or not 0<self.conf<=1:raise ValueError('Invalid PPE policy')
        self.bare_conf=config.get('minimum_no_helmet_candidate_confidence',self.conf)
        if not math.isfinite(self.bare_conf) or not 0<self.bare_conf<=self.conf:raise ValueError('Invalid bare-head candidate threshold')
        self.conflict_warning=config.get('conflicting_bare_head_policy','unknown')=='warning_candidate'
        self.require_baseline=config.get('require_baseline_helmet_confirmation',False)
        self.history={};self.previous={};self.last=None
    def reset(self):self.history.clear();self.previous.clear();self.last=None
    def update(self,timestamp,tracks,missing=(),scene_cut=False):
        if self.last is not None and timestamp<=self.last or not math.isfinite(timestamp) or timestamp<0:raise ValueError('Increasing source times required')
        if scene_cut:self.reset()
        self.last=timestamp;events=[];seen=set()
        for track in tracks:
            key=track['track_id']
            if key in seen:raise ValueError('Duplicate track')
            seen.add(key);obs=track['ppe'];heads=obs['head_candidates'];state=obs['state']
            # Do not erase a conflict simply by removing the lower-confidence class.
            expected='helmeted_head' if state=='helmet_detected' else 'no_helmet_head' if state=='no_helmet_candidate' else None
            conflict_candidate=state=='conflicting_evidence' and self.conflict_warning
            if conflict_candidate:expected='no_helmet_head'
            threshold=self.bare_conf if expected=='no_helmet_head' else self.conf
            valid=expected is not None and any(h['class']==expected and h['confidence']>=threshold for h in heads)
            baseline_missing=expected=='helmeted_head' and self.require_baseline and not any(h['class']=='helmeted_head' and h['confidence']>=self.conf and 'baseline' in h.get('model_sources',[])for h in heads)
            if baseline_missing:valid=False
            confirmation_key=expected if self.conflict_warning else state
            weak_bare=expected=='no_helmet_head' and not any(h['class']==expected and h['confidence']>=self.conf for h in heads)
            if valid:
                old=self.history.get(key)
                if old is None or old['state']!=confirmation_key or timestamp-old['last']>self.gap:old={'state':confirmation_key,'first':timestamp,'count':0}
                old.update(last=timestamp,count=old['count']+1);self.history[key]=old
                stable=old['count']>=self.frames and timestamp-old['first']>=self.duration
                severity=('SAFE' if state=='helmet_detected' else 'WARNING') if stable else None
                reason='stable_low_confidence_ppe_requires_review' if stable and weak_bare else 'stable_conflicting_ppe_requires_review' if stable and conflict_candidate else 'stable_helmet_evidence' if stable and state=='helmet_detected' else 'stable_no_helmet_candidate_requires_review' if stable else 'pending_temporal_confirmation'
            else:
                self.history.pop(key,None);stable=False;severity=None;reason='supplement_only_helmet_unconfirmed' if baseline_missing else 'conflicting_or_missing_or_low_confidence_head'
            events.append({'event_type':'ppe','track_id':key,'timestamp_seconds':timestamp,'severity':severity,'observation_status':'confirmed' if stable else 'unconfirmed','ppe_state':state,'reason':reason,'person_bbox_xyxy':track.get('detected_bbox_xyxy',track['bbox_xyxy']),'head_candidates':heads,'violation_status':'not_verified','scope':'helmet_observation_for_this_person_only','classification_status':'unconfirmed' if conflict_candidate or weak_bare or baseline_missing or state=='unknown' else 'observed_candidate'})
        for key in set(self.history)-seen:self.history.pop(key,None)
        for track in missing:
            key=track['track_id']
            if key in seen:continue
            events.append({'event_type':'ppe','track_id':key,'timestamp_seconds':timestamp,'severity':None,'observation_status':'unconfirmed','ppe_state':'unknown','reason':'person_not_observed','violation_status':'not_verified'})
        transitions=[]
        for event in events:
            key=event['track_id'];value=(event['severity'],event['ppe_state'],event['reason'])
            if self.previous.get(key)!=value:transitions.append(event.copy())
            self.previous[key]=value
        self.previous={k:v for k,v in self.previous.items() if k in {e['track_id'] for e in events}}
        return events,transitions
