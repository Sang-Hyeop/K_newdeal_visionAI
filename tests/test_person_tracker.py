import unittest
from src.person_tracker import PersonTracker


def person(x=100):
    return {'class':'person','bbox_xyxy':[x,100,x+60,260],'confidence':.9}


class TrackingTests(unittest.TestCase):
    def test_motion_and_short_gap_keep_identity_without_fabricated_detection(self):
        tracker=PersonTracker(5)
        first,_=tracker.update(0,[person()],(400,400))
        second,_=tracker.update(.2,[person(102)],(400,400))
        self.assertEqual(first[0]['track_id'],second[0]['track_id'])
        observed,missing=tracker.update(.4,[],(400,400))
        self.assertEqual(observed,[])
        self.assertEqual(missing[0]['ppe_state'],'unknown')
        recovered,_=tracker.update(.6,[person(104)],(400,400))
        self.assertEqual(recovered[0]['track_id'],first[0]['track_id'])

    def test_scene_change_never_reuses_old_identity(self):
        tracker=PersonTracker(5)
        first,_=tracker.update(0,[person()],(400,400))
        second,_=tracker.update(.2,[person()],(400,400),scene_cut=True)
        self.assertNotEqual(first[0]['track_id'],second[0]['track_id'])

    def test_large_timestamp_gap_resets_identity(self):
        tracker=PersonTracker(5)
        first,_=tracker.update(0,[person()],(400,400))
        second,_=tracker.update(2,[person()],(400,400))
        self.assertNotEqual(first[0]['track_id'],second[0]['track_id'])

    def test_nonmonotonic_timestamps_rejected(self):
        tracker=PersonTracker(5)
        tracker.update(0,[],(400,400))
        with self.assertRaises(ValueError):tracker.update(0,[],(400,400))


if __name__=='__main__':unittest.main()
