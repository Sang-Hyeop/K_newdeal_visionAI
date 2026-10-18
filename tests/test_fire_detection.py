import unittest
from src.fire_detection import FireTemporal, deduplicate
from src.event_contract import normalize_event

POLICY = dict(window_seconds=1,minimum_observations=3,minimum_span_seconds=.4,hold_seconds=.6,association_gap_seconds=1.5,association_iou=.1)
def detection(x=10):return {'class':'fire','confidence':.8,'bbox_xyxy':[x,10,x+50,60]}
class FireTests(unittest.TestCase):
 def test_nested_fire_regions_are_one_target(self):
  large={'class':'fire','confidence':.7,'bbox_xyxy':[0,0,200,200]}
  self.assertEqual(len(deduplicate([large,detection()])),1)
 def test_single_flash_is_not_alarm(self):
  rule=FireTemporal(POLICY)
  self.assertIsNone(rule.update(0,[detection()])[0]['severity'])
  self.assertTrue(all(e['severity']is None for e in rule.update(.2,[])))
 def test_multiple_boxes_in_same_frame_do_not_confirm(self):
  rule=FireTemporal(POLICY)
  self.assertTrue(all(e['severity']is None for e in rule.update(0,[detection()]*5)))
 def test_spatially_separate_flashes_do_not_accumulate(self):
  rule=FireTemporal(POLICY)
  for t,x in [(0,10),(.2,300),(.4,600)]:self.assertTrue(all(e['severity']is None for e in rule.update(t,[detection(x)])))
 def test_hold_has_no_ghost_box_and_loss_is_not_safe(self):
  rule=FireTemporal(POLICY)
  for t in [0,.2,.4]:events=rule.update(t,[detection()])
  self.assertEqual(events[0]['severity'],'CRITICAL')
  held=rule.update(.6,[])[0]
  self.assertEqual(held['severity'],'CRITICAL');self.assertFalse(held['current_detection']);self.assertIsNone(held['fire_bbox_xyxy'])
  lost=rule.update(1.2,[])[0];self.assertIsNone(lost['severity']);self.assertEqual(lost['reason'],'fire_not_observed')
 def test_scene_reset_requires_fresh_evidence(self):
  rule=FireTemporal(POLICY)
  for t in [0,.2,.4]:rule.update(t,[detection()])
  self.assertIsNone(rule.update(.6,[detection()],reset=True)[0]['severity'])
 def test_nonmonotonic_source_time_rejected(self):
  rule=FireTemporal(POLICY);rule.update(1,[])
  with self.assertRaises(ValueError):rule.update(.5,[])
 def test_fire_contract_does_not_call_pending_safe(self):
  event=FireTemporal(POLICY).update(0,[detection()])[0]
  record=normalize_event(event,camera_id='parking',video='test.mp4',source_sha256='a',model_version='b',config_version='c')
  self.assertEqual(record['event_type'],'fire');self.assertFalse(record['alert_eligible']);self.assertIsNone(record['severity'])
 def test_clock_overlay_change_resets_without_timestamp_schedule(self):
  import numpy as np
  from src.fire_detection import SceneBoundary
  rule=SceneBoundary(dict(scene_difference=.9,clock_roi_normalized=[0,0,.5,.5],clock_binary_threshold=170,clock_change_fraction=.03))
  frame=np.zeros((100,100,3),dtype=np.uint8)
  self.assertIsNone(rule.update(frame))
  frame[:50,:50]=255
  self.assertEqual(rule.update(frame),'clock_overlay_changed')
 def test_fire_backend_round_trip(self):
  import tempfile
  from pathlib import Path
  from src.event_contract import export_events
  from backend_v1.backend import Store
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp);logs=root/'fire';logs.mkdir();rule=FireTemporal(POLICY);records=[]
   for t in [0,.2,.4]:
    ev=rule.update(t,[detection()]);records.append(dict(timestamp_seconds=t,frame_index=round(t*30),events=ev,transitions=ev if t in(0,.4)else[]))
   export_events(records,logs/'events_v1.jsonl',feature='fire',context=dict(camera_id='parking',video='fire.mp4',source_sha256='a',model_version='b',config_version='c'))
   store=Store(root/'test.sqlite3');result=store.ingest(logs)
   self.assertEqual(result['inserted'],dict(events=2,observations=3))
   self.assertEqual(store.latest({'camera_id':'parking'})['count'],1)
