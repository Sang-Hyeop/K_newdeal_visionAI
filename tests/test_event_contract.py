import json,tempfile,unittest
from pathlib import Path
from src.feature_status import feature_status
from src.event_contract import normalize_event,export_events
from src.tracked_proximity import TrackedProximity

CONTEXT=dict(camera_id='c',video='v.mp4',source_sha256='source',model_version='model',config_version='config')
CFG=dict(distance_mode='image_plane',detection_scope='full_frame',max_gap_seconds=1,warning_ratio=1,critical_ratio=.3,hysteresis_ratio=.1,camera_id='c')
DETS=[{'class':'person','bbox_xyxy':[110,100,130,200],'confidence':.9},{'class':'forklift','bbox_xyxy':[50,100,100,200],'confidence':.9}]
class EventTests(unittest.TestCase):
 def test_intrusion_critical_not_overwritten_by_dwell_safe(self):
  events=[{'severity':'SAFE','observation_status':'confirmed'},{'severity':'CRITICAL','observation_status':'confirmed'}]
  self.assertEqual(feature_status(events)['severity'],'CRITICAL')
 def test_safe_and_unknown_stays_unknown(self):
  self.assertIsNone(feature_status([{'severity':'SAFE','observation_status':'confirmed'},{'severity':None,'observation_status':'unconfirmed'}])['severity'])
  self.assertIsNone(feature_status([])['severity'])
 def test_warning_with_unknown_keeps_warning_and_partial_coverage(self):
  r=feature_status([{'severity':'WARNING','observation_status':'confirmed'},{'severity':None,'observation_status':'unconfirmed'}]);self.assertEqual(r['severity'],'WARNING');self.assertEqual(r['coverage'],'partial')
 def test_unconfirmed_cannot_be_safe(self):
  e=normalize_event(dict(event_type='zone_dwell',timestamp_seconds=0,severity='SAFE',observation_status='unconfirmed',track_id='p'),**CONTEXT)
  self.assertIsNone(e['severity']);self.assertEqual(e['track_ids'],['p'])
 def test_stable_id_changes_with_model_or_source(self):
  native=dict(event_type='zone_dwell',timestamp_seconds=0,severity='SAFE',observation_status='confirmed',track_id='p')
  a=normalize_event(native,**CONTEXT);self.assertEqual(a,normalize_event(native,**CONTEXT))
  self.assertNotEqual(a['event_id'],normalize_event(native,**{**CONTEXT,'model_version':'next'})['event_id'])
 def test_no_subjects_export_unknown_once_then_after_cut(self):
  records=[dict(timestamp_seconds=0,events=[],transitions=[],scene_id=0),dict(timestamp_seconds=.2,events=[],transitions=[],scene_id=0),dict(timestamp_seconds=.4,events=[],transitions=[],scene_id=1)]
  with tempfile.TemporaryDirectory() as d:
   rows=export_events(records,Path(d)/'events.jsonl',feature='proximity',context=CONTEXT)
  self.assertEqual(len(rows),2);self.assertTrue(all(r['severity'] is None for r in rows))
 def test_forbidden_roi_config_not_accepted_as_proximity(self):
  with self.assertRaises(ValueError):TrackedProximity({**CFG,'forklift_ground_roi_normalized':[[.5,0],[1,0],[1,1]]},5)
 def test_full_frame_left_pair_and_cut_continue(self):
  pipe=TrackedProximity(CFG,5);first=pipe.update(0,DETS,(500,500))
  self.assertEqual(first['events'][0]['severity'],'CRITICAL');self.assertFalse(first['zone_roi_used'])
  after=pipe.update(.2,DETS,(500,500),scene_cut=True)
  self.assertTrue(after['events']);self.assertNotEqual(first['people'][0]['track_id'],after['people'][0]['track_id'])
  self.assertTrue(all(e['person_track_id'].startswith('P1:') for e in after['events']))
 def test_meters_without_calibration_rejected(self):
  with self.assertRaises(ValueError):TrackedProximity({**CFG,'distance_mode':'meters'},5)
if __name__=='__main__':unittest.main()
