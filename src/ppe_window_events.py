"""User-approved rolling evidence policy; no stale body boxes or invented heads."""
import math
from collections import deque

class WindowPPEEvents:
    def __init__(self, config):
        self.config = config
        self.window = config['window_seconds']
        self.minimum = config['minimum_valid_observations']
        self.fraction = config['minimum_class_fraction']
        self.hold = config['maximum_state_hold_seconds']
        self.thresholds = {'helmeted_head': config['helmet_evidence_confidence'], 'no_helmet_head': config['no_helmet_evidence_confidence']}
        if not all(math.isfinite(v) for v in [self.window,self.hold,self.fraction,*self.thresholds.values()]) or self.window<=0 or not 0<=self.hold<=self.window or not .5<self.fraction<=1 or self.minimum<1 or not all(0<v<=1 for v in self.thresholds.values()):
            raise ValueError('Invalid rolling PPE policy')
        self.history={}; self.previous={}; self.last=None
    def reset(self):
        self.history.clear(); self.previous.clear(); self.last=None
    def update(self, timestamp, tracks, missing=(), scene_cut=False):
        if not math.isfinite(timestamp) or timestamp<0 or self.last is not None and timestamp<=self.last:
            raise ValueError('Increasing source times required')
        if scene_cut:self.reset()
        self.last=timestamp;events=[];seen=set()
        for track in tracks:
            key=track['track_id']
            if key in seen:raise ValueError('Duplicate track')
            seen.add(key);obs=track['ppe'];heads=obs['head_candidates']
            supported={cls for cls,threshold in self.thresholds.items() if any(h['class']==cls and h['confidence']>=threshold and (cls!='helmeted_head' or not self.config.get('require_baseline_helmet_confirmation',True) or 'baseline' in h.get('model_sources',[])) for h in heads)}
            vote=next(iter(supported)) if len(supported)==1 else 'conflict' if supported else None
            state=self.history.setdefault(key,{'votes':deque(),'confirmed':None,'last_valid':None})
            votes=state['votes']
            while votes and timestamp-votes[0][0]>self.window+1e-9:votes.popleft()
            if vote is not None:votes.append((timestamp,vote));state['last_valid']=timestamp
            opposite=state['confirmed'] is not None and vote is not None and vote!=state['confirmed']
            if opposite:state['confirmed']=None
            counts={cls:sum(v==cls for _,v in votes) for cls in self.thresholds}
            winner=max(counts,key=counts.get)
            age=timestamp-state['last_valid'] if state['last_valid'] is not None else None
            enough=len(votes)>=self.minimum and counts[winner]/len(votes)>=self.fraction
            # Current contrary evidence always wins over an old window majority.
            can_confirm=not opposite and enough and age is not None and age<=self.hold+1e-9 and (vote==winner or vote is None and state['confirmed']==winner)
            if can_confirm:state['confirmed']=winner
            held=vote is None and state['confirmed'] is not None and age is not None and age<=self.hold+1e-9
            confirmed=(can_confirm or held) and not opposite
            if not confirmed:state['confirmed']=None
            kind=state['confirmed'] if confirmed else vote
            pstate='helmet_detected' if kind=='helmeted_head' else 'no_helmet_candidate' if kind=='no_helmet_head' else 'conflicting_evidence' if kind=='conflict' else 'unknown'
            reason='held_recent_ppe_evidence' if confirmed and vote is None else 'stable_helmet_evidence' if confirmed and kind=='helmeted_head' else 'stable_no_helmet_candidate_requires_review' if confirmed else 'pending_temporal_confirmation' if vote is not None or votes and age is not None and age<=self.hold+1e-9 else 'conflicting_or_missing_or_low_confidence_head'
            event={'event_type':'ppe','track_id':key,'timestamp_seconds':timestamp,'severity':('SAFE' if kind=='helmeted_head' else 'WARNING') if confirmed else None,'observation_status':'confirmed' if confirmed else 'unconfirmed','ppe_state':pstate,'reason':reason,'person_bbox_xyxy':track.get('detected_bbox_xyxy',track['bbox_xyxy']),'head_candidates':heads,'violation_status':'not_verified','scope':'helmet_observation_for_this_person_only','classification_status':'observed_candidate' if confirmed else 'unconfirmed','observation_held':confirmed and vote is None,'last_valid_head_age_seconds':age,'window_valid_observations':len(votes),'window_winner_fraction':counts[winner]/len(votes) if votes else None}
            events.append(event)
        # A body must remain currently observed. Missing person/scene/ID ends hold.
        for key in set(self.history)-seen:self.history.pop(key,None)
        for track in missing:
            if track['track_id'] not in seen:events.append({'event_type':'ppe','track_id':track['track_id'],'timestamp_seconds':timestamp,'severity':None,'observation_status':'unconfirmed','ppe_state':'unknown','reason':'person_not_observed','violation_status':'not_verified'})
        transitions=[]
        for event in events:
            key=event['track_id'];value=(event['severity'],event['ppe_state'],event['reason'])
            if self.previous.get(key)!=value:transitions.append(event.copy())
            self.previous[key]=value
        self.previous={k:v for k,v in self.previous.items() if k in {e['track_id'] for e in events}}
        return events,transitions
