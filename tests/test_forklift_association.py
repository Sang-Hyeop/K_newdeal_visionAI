import unittest
from src.tracked_proximity import TrackedProximity
from src.person_tracker import PersonTracker

class ForkliftAssociationTests(unittest.TestCase):
    def test_vehicle_override_preserves_person_association_policy(self):
        cfg={'distance_mode':'image_plane','detection_scope':'full_frame','max_gap_seconds':1,'warning_ratio':1,'critical_ratio':.3,'hysteresis_ratio':.1,'tracker_fuse_score':True,'forklift_tracker_fuse_score':False}
        rule=TrackedProximity(cfg,5)
        self.assertTrue(rule.people.backend.args.fuse_score)
        self.assertFalse(rule.forklifts.backend.args.fuse_score)
    def test_geometry_preserves_identity_when_score_drops_during_motion(self):
        tracker=PersonTracker(5,target_class='forklift',fuse_score=False)
        first,_=tracker.update(0,[{'class':'forklift','confidence':.9,'bbox_xyxy':[100,100,200,200]}],(1080,1920))
        next_,_=tracker.update(.2,[{'class':'forklift','confidence':.26,'bbox_xyxy':[140,100,240,200]}],(1080,1920))
        self.assertEqual(len(next_),1)
        self.assertEqual(first[0]['track_id'],next_[0]['track_id'])
        lost,missing=tracker.update(.4,[],(1080,1920))
        self.assertEqual(lost,[])
        self.assertEqual(missing[0]['observation_status'],'unconfirmed')

class VehicleExtentAmbiguityTests(unittest.TestCase):
    def test_observed_duplicate_scope_cannot_generate_false_collision(self):
        from src.forklift_proximity import ForkliftProximity
        boxes=[[747.077,279.719,1144.435,541.063],[858.315,175.194,1221.900,563.745]]
        vehicles=[{'track_id':str(i),'bbox_xyxy':b}for i,b in enumerate(boxes)]
        event=ForkliftProximity().update(0,vehicles,(1080,1920))[0]
        self.assertIsNone(event['severity'])
        self.assertEqual(event['reason'],'merged_or_duplicate_vehicle_boxes')
    def test_distinct_close_vehicles_still_raise_critical(self):
        from src.forklift_proximity import ForkliftProximity
        vehicles=[{'track_id':'A','bbox_xyxy':[100,100,200,200]},{'track_id':'B','bbox_xyxy':[210,100,310,200]}]
        self.assertEqual(ForkliftProximity().update(0,vehicles,(1080,1920))[0]['severity'],'CRITICAL')
