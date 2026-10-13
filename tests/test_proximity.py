import unittest
from src.proximity import Proximity
from src.person_tracker import PersonTracker


def person(x):return {'track_id':'p','bbox_xyxy':[x-10,100,x+10,200]}
FORK={'track_id':'f','bbox_xyxy':[300,100,400,200]}


class ProximityTests(unittest.TestCase):
    def test_safe_warning_critical_and_hysteresis(self):
        p=Proximity()
        for time,x,severity in [(0,150,'SAFE'),(.2,210,'WARNING'),(.4,280,'CRITICAL'),(.6,265,'CRITICAL'),(.8,250,'WARNING'),(1,180,'SAFE')]:
            self.assertEqual(p.update(time,[person(x)],[FORK],(500,500))[0]['severity'],severity)

    def test_missing_pair_is_unknown_and_empty_is_not_safe(self):
        p=Proximity();self.assertEqual(p.update(0,[],[],(500,500)),[])
        p.update(.2,[person(280)],[FORK],(500,500))
        self.assertIsNone(p.update(.4,[],[FORK],(500,500))[0]['severity'])

    def test_possible_driver_is_unknown(self):
        p=Proximity();driver={'track_id':'p','bbox_xyxy':[320,110,350,150]}
        r=p.update(0,[driver],[FORK],(500,500))[0]
        self.assertIsNone(r['severity']);self.assertEqual(r['reason'],'possible_operator_or_occluded_person')

    def test_overlapping_person_at_vehicle_bottom_is_unknown(self):
        # Actual v16 video regression: foot extends 0.31 px beyond the forklift box.
        p=Proximity()
        person_box={'track_id':'p','bbox_xyxy':[640.64,132.14,687.21,249.32]}
        vehicle={'track_id':'f','bbox_xyxy':[629.25,54.85,701.30,249.00]}
        r=p.update(0,[person_box],[vehicle],(720,1280))[0]
        self.assertIsNone(r['severity'])
        self.assertEqual(r['reason'],'possible_operator_or_occluded_person')

    def test_partial_overlap_pedestrian_remains_critical(self):
        # Nearby pedestrian is mostly outside vehicle; do not suppress every overlap.
        p=Proximity()
        r=p.update(0,[person(298)],[FORK],(500,500))[0]
        self.assertEqual(r['severity'],'CRITICAL')

    def test_clipped_foot_and_unscaled_meters(self):
        p=Proximity();r=p.update(0,[{'track_id':'p','bbox_xyxy':[200,100,230,500]}],[FORK],(500,500))[0]
        self.assertIsNone(r['severity']);self.assertIsNone(r['distance_meters'])

    def test_separate_class_trackers_have_independent_id_counters(self):
        a=PersonTracker(5,namespace='P');b=PersonTracker(5,target_class='forklift',namespace='F')
        d={'class':'person','bbox_xyxy':[100,100,160,260],'confidence':.9}
        p,_=a.update(0,[d],(500,500));f,_=b.update(0,[{**d,'class':'forklift'}],(500,500))
        self.assertEqual(p[0]['track_id'],'P0:1');self.assertEqual(f[0]['track_id'],'F0:1')
        b.reset()
        p2,_=a.update(.2,[d,{**d,'bbox_xyxy':[300,100,360,260]}],(500,500))
        p3,_=a.update(.4,[d,{**d,'bbox_xyxy':[300,100,360,260]}],(500,500))
        self.assertEqual({t['track_id'] for t in p3},{'P0:1','P0:2'})


if __name__=='__main__':unittest.main()

class RecentPedestrianOverlapTests(unittest.TestCase):
 def test_video1_expanding_box_preserves_observed_pedestrian_danger(self):
  rule=Proximity(1.6,.8,max_gap=1,recent_pedestrian_overlap=True)
  p={'track_id':'p','bbox_xyxy':[428,348,589,565]};f={'track_id':'f','bbox_xyxy':[492,146,733,492]}
  self.assertEqual(rule.update(10.64,[p],[f],(720,1280))[0]['severity'],'CRITICAL')
  p['bbox_xyxy']=[414,343,519,564];f['bbox_xyxy']=[351,156,733,556]
  event=rule.update(10.84,[p],[f],(720,1280))[0]
  self.assertEqual(event['severity'],'CRITICAL');self.assertTrue(event['recent_pedestrian_overlap_evidence'])
 def test_first_overlap_cannot_claim_pedestrian_role(self):
  rule=Proximity(1.6,.8,recent_pedestrian_overlap=True)
  p={'track_id':'p','bbox_xyxy':[414,343,519,564]};f={'track_id':'f','bbox_xyxy':[351,156,733,556]}
  self.assertIsNone(rule.update(0,[p],[f],(720,1280))[0]['severity'])
 def test_old_evidence_expires(self):
  rule=Proximity(1.6,.8,max_gap=1,recent_pedestrian_overlap=True)
  p={'track_id':'p','bbox_xyxy':[428,348,589,565]};f={'track_id':'f','bbox_xyxy':[492,146,733,492]};rule.update(0,[p],[f],(720,1280))
  p['bbox_xyxy']=[414,343,519,564];f['bbox_xyxy']=[351,156,733,556]
  self.assertIsNone(rule.update(2,[p],[f],(720,1280))[0]['severity'])
