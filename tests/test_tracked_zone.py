import unittest
from src.tracked_zone import TrackedZone

CONFIG={'camera_id':'test','roi_id':'test','roi_purpose':'demonstration_only',
        'polygon_normalized':[[0,0],[.5,0],[.5,1],[0,1]],'safe_seconds':3,
        'critical_seconds':8,'max_gap_seconds':1}


def person():return {'class':'person','bbox_xyxy':[30,30,70,170],'confidence':.9}


class IntegrationTests(unittest.TestCase):
    def test_detect_track_roi_time_and_event_transitions(self):
        pipeline=TrackedZone(CONFIG,(200,200),5);transitions=[]
        for i in range(46):
            r=pipeline.update(i/5,[person()],(200,200));transitions.extend(r['transitions'])
        confirmed=[e for e in transitions if e['observation_status']=='confirmed']
        self.assertEqual([e['severity'] for e in confirmed],['SAFE','WARNING','CRITICAL'])
        self.assertEqual(confirmed[0]['observed_dwell_seconds'],0)
        self.assertAlmostEqual(confirmed[-1]['observed_dwell_seconds'],8)
        self.assertEqual(len({e['track_id'] for e in confirmed}),1)

    def test_empty_is_not_global_safe_and_missing_does_not_count(self):
        p=TrackedZone(CONFIG,(200,200),5)
        empty=p.update(0,[],(200,200));self.assertEqual(empty['events'],[])
        self.assertEqual(empty['zone_observation_status'],'unconfirmed')
        p.update(.2,[person()],(200,200));p.update(.4,[person()],(200,200))
        missing=p.update(.6,[],(200,200));self.assertIsNone(missing['events'][0]['severity'])
        recovered=p.update(.8,[person()],(200,200))
        self.assertAlmostEqual(recovered['events'][0]['observed_dwell_seconds'],0)

    def test_scene_change_disables_old_roi(self):
        p=TrackedZone(CONFIG,(200,200),5);p.update(0,[person()],(200,200))
        r=p.update(.2,[person()],(200,200),scene_cut=True)
        self.assertFalse(r['roi_active']);self.assertEqual(r['events'],[])

    def test_access_and_dwell_are_independent_event_scopes(self):
        c={**CONFIG,'access_enabled':True,'approach_margin_ratio':.05}
        p=TrackedZone(c,(200,200),5);r=p.update(0,[person()],(200,200))
        events={e['event_type']:e for e in r['events']}
        self.assertEqual(events['zone_dwell']['severity'],'SAFE')
        self.assertEqual(events['zone_access']['severity'],'CRITICAL')
        self.assertFalse(events['zone_access']['entry_observed'])
        self.assertEqual(len(r['transitions']),2)
        self.assertEqual(p.update(.2,[person()],(200,200))['transitions'],[])
        self.assertEqual(p.update(.4,[person()],(200,200),scene_cut=True)['events'],[])

    def test_bottom_clipped_person_cannot_fabricate_zone_exit(self):
        c={**CONFIG,'access_enabled':True,'approach_margin_ratio':.05}
        p=TrackedZone(c,(200,200),5);p.update(0,[person()],(200,200))
        clipped={'class':'person','bbox_xyxy':[30,30,70,200],'confidence':.9}
        r=p.update(.2,[clipped],(200,200))
        self.assertTrue(r['invalid_anchor_track_ids'])
        for e in r['events']:
            self.assertIsNone(e['severity'])
            if e['event_type']=='zone_access':self.assertFalse(e['exit_observed'])


if __name__=='__main__':unittest.main()
