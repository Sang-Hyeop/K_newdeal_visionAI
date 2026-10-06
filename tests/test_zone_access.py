import unittest
from src.zone_access import ZoneAccess


def track(x,y=50):return {'track_id':'p1','bbox_xyxy':[x-5,y-20,x+5,y]}


class AccessTests(unittest.TestCase):
    def make(self):return ZoneAccess([[0,0],[100,0],[100,100],[0,100]],10)

    def test_outside_approach_boundary_inside_exit(self):
        p=self.make();self.assertEqual(p.update(0,[track(120)])[0]['severity'],'SAFE')
        self.assertEqual(p.update(.2,[track(110)])[0]['severity'],'WARNING')
        r=p.update(.4,[track(100)])[0];self.assertEqual(r['severity'],'CRITICAL');self.assertTrue(r['entry_observed'])
        r=p.update(.6,[track(105)])[0];self.assertTrue(r['exit_observed']);self.assertEqual(r['severity'],'WARNING')

    def test_first_inside_is_presence_not_proven_entry(self):
        r=self.make().update(0,[track(50)])[0]
        self.assertFalse(r['entry_observed']);self.assertEqual(r['authorization_status'],'not_assessed')

    def test_missing_cannot_invent_entry_or_safe(self):
        p=self.make();p.update(0,[track(120)])
        missing=p.update(.2,[])[0];self.assertIsNone(missing['severity'])
        r=p.update(.4,[track(50)])[0];self.assertFalse(r['entry_observed'])

    def test_long_gap_cannot_prove_crossing(self):
        p=self.make();p.update(0,[track(120)])
        self.assertFalse(p.update(2,[track(50)])[0]['entry_observed'])


if __name__=='__main__':unittest.main()
