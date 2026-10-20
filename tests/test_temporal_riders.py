# 역할: 시간에 따른 탑승 역할 확정과 해제 동작을 회귀 검증합니다.
import unittest
from src.operator_association import TemporalOperatorAssociation
from src.tracked_proximity import TrackedProximity

class TemporalRiderTests(unittest.TestCase):
 def data(self,x=0):
  return dict(track_id='p',bbox_xyxy=[140+x,120,190+x,180]),dict(track_id='v',bbox_xyxy=[100+x,100,240+x,300])
 def test_confirmation_gap_and_release(self):
  r=TemporalOperatorAssociation();p,v=self.data()
  self.assertEqual(r.update(0,[p],[v]),{});self.assertEqual(r.update(.2,[p],[v]),{})
  self.assertEqual(r.update(.4,[p],[v]),{'p':'v'})
  self.assertEqual(r.update(.6,[p],[dict(v,track_id='other',bbox_xyxy=[350,100,490,300])]),{'p':'v'})
  self.assertEqual(r.update(1.6,[p],[]),{})
 def test_person_departure_releases_even_with_owner_visible(self):
  r=TemporalOperatorAssociation();p,v=self.data()
  for t in [0,.2,.4]:r.update(t,[p],[v])
  p['bbox_xyxy']=[250,130,285,300]
  self.assertEqual(r.update(.6,[p],[v]),{})
 def test_walking_person_single_overlap_not_excluded(self):
  r=TemporalOperatorAssociation();p,v=self.data();p['bbox_xyxy']=[20,120,60,190]
  r.update(0,[p],[v]);p['bbox_xyxy']=[140,120,190,180]
  self.assertEqual(r.update(.2,[p],[v]),{})
 def test_all_vehicle_pairs_excluded_and_person_preserved(self):
  cfg=dict(distance_mode='image_plane',detection_scope='full_frame',max_gap_seconds=1,warning_ratio=1,critical_ratio=.3,hysteresis_ratio=.1,distance_geometry='bottom_center',associate_riders=True,temporal_riders=True,exclude_riders_from_all_proximity=True,camera_id='test')
  r=TrackedProximity(cfg,5);p,v=self.data()
  ds=[dict(p,**{'class':'person','confidence':.9}),dict(v,**{'class':'forklift','confidence':.9}),{'class':'forklift','confidence':.9,'bbox_xyxy':[300,100,440,300]}]
  for t in [0,.2,.4]:out=r.update(t,ds,(500,500))
  self.assertEqual(out['events'],[]);self.assertEqual(len(out['people']),1);self.assertEqual(len(out['excluded_rider_pairs']),2)
 def test_person_id_switch_preserves_confirmed_relation(self):
  r=TemporalOperatorAssociation();p,v=self.data()
  for t in [0,.2,.4]:r.update(t,[p],[v])
  p['track_id']='new';self.assertEqual(r.update(.6,[p],[v]),{'new':'v'})
 def test_scene_reset_removes_role(self):
  r=TemporalOperatorAssociation();p,v=self.data()
  for t in [0,.2,.4]:r.update(t,[p],[v])
  r.reset();self.assertEqual(r.update(.6,[p],[v]),{})

class PendingRoleTests(unittest.TestCase):
 def test_candidate_is_unknown_not_safe_or_alerting(self):
  cfg=dict(distance_mode='image_plane',detection_scope='full_frame',max_gap_seconds=1,warning_ratio=1,critical_ratio=.3,hysteresis_ratio=.1,distance_geometry='bottom_center',associate_riders=True,temporal_riders=True,exclude_riders_from_all_proximity=True,camera_id='test')
  r=TrackedProximity(cfg,5);ds=[{'class':'person','confidence':.9,'bbox_xyxy':[140,120,190,180]},{'class':'forklift','confidence':.9,'bbox_xyxy':[100,100,240,300]}]
  out=r.update(0,ds,(500,500));self.assertTrue(out['pending_rider_ids'])
  self.assertIsNone(out['events'][0]['severity']);self.assertFalse(out['events'][0]['distance_display_enabled'])
 def test_previously_outside_person_needs_matching_movement(self):
  r=TemporalOperatorAssociation();v={'track_id':'v','bbox_xyxy':[100,100,240,300]};p={'track_id':'p','bbox_xyxy':[20,120,60,180]}
  r.update(0,[p],[v]);p['bbox_xyxy']=[140,120,190,180]
  for t in [.2,.4,.6,.8]:self.assertEqual(r.update(t,[p],[v]),{})
 def test_coupled_movement_can_confirm_after_initial_vehicle_miss(self):
  r=TemporalOperatorAssociation();p={'track_id':'p','bbox_xyxy':[140,120,190,180]}
  r.update(0,[p],[])
  for i,t in enumerate([.2,.4,.6]):
   x=10*i;p['bbox_xyxy']=[140+x,120,190+x,180];v={'track_id':'v','bbox_xyxy':[100+x,100,240+x,300]};out=r.update(t,[p],[v])
  self.assertEqual(out,{'p':'v'})
