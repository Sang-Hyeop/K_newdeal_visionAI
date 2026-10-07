"""Common event envelopes for observed rule transitions, never global safety."""
import hashlib,json,math
from .feature_status import feature_status

def normalize_event(event,*,camera_id,video,source_sha256,model_version,config_version):
    timestamp=event['timestamp_seconds'];severity=event.get('severity');status=event.get('observation_status','unconfirmed')
    if not math.isfinite(timestamp) or timestamp<0:raise ValueError('Invalid source timestamp')
    if severity not in {None,'SAFE','WARNING','CRITICAL'}:raise ValueError('Invalid severity')
    if status not in {'confirmed','unconfirmed'}:raise ValueError('Invalid observation status')
    if status!='confirmed':severity=None
    kind={'forklift_forklift_proximity':'forklift_proximity','person_forklift_proximity':'proximity','zone_access':'zone_access','zone_dwell':'zone_dwell','feature_status':'status','ppe':'ppe'}.get(event['event_type'])
    if kind is None:raise ValueError('Unsupported event type')
    identities=[event[k] for k in ['track_id','person_track_id','forklift_track_id'] if k in event]
    identities+=event.get('forklift_track_ids',[])
    evidence={k:v for k,v in event.items() if k not in {'event_type','timestamp_seconds','severity','observation_status','camera_id'}}
    envelope={'schema_version':'1.0','camera_id':camera_id,'video':video,'source_sha256':source_sha256,
              'timestamp_seconds':timestamp,'event_type':kind,'severity':severity,'observation_status':status,
              'track_ids':identities,'evidence':evidence,'model_version':model_version,'config_version':config_version,
              'scope':'observed_subjects_for_this_feature_only'}
    envelope['event_id']=hashlib.sha256(json.dumps(envelope,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return envelope

def export_events(records,path,*,feature,context):
    """Export transitions; emit UNKNOWN on empty observations, not SAFE."""
    result=[];snapshots=[];previous_empty=None
    for record in records:
        snapshots.append({'schema_version':'1.0','feature':feature,'camera_id':context['camera_id'],'video':context['video'],'timestamp_seconds':record['timestamp_seconds'],'frame_index':record.get('frame_index'),'scene_id':record.get('scene_id',0),'global_safety_status':'not_evaluated','feature_status':feature_status(record['events']),'observation_status':'confirmed' if any(e.get('observation_status')=='confirmed' for e in record['events']) else 'unconfirmed','events':[normalize_event(e,**context) for e in record['events']]})
        for event in record['transitions']:result.append(normalize_event(event,**context))
        empty=not record['events']
        state=(empty,record.get('scene_id',0),record.get('roi_active',True))
        if empty and state!=previous_empty:
            result.append(normalize_event({'event_type':'feature_status','timestamp_seconds':record['timestamp_seconds'],
                'severity':None,'observation_status':'unconfirmed','feature':feature,'reason':'roi_inactive' if not record.get('roi_active',True) else 'no_observed_subject_pair_or_person'},**context))
        previous_empty=state
    path.with_name('observations_v1.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in snapshots))
    path.write_text(''.join(json.dumps(e,ensure_ascii=False,allow_nan=False)+'\n' for e in result))
    return result
