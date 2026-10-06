import unittest
from src.zone_dwell import ZoneDwell

def track(i=1, outside=False):
    return {'track_id':i,'bbox_xyxy':[20,20,40,40] if not outside else [120,20,140,40]}

class DwellTests(unittest.TestCase):
    def make(self):return ZoneDwell([[0,0],[100,0],[100,100],[0,100]])
    def test_thresholds_and_exit(self):
        z=self.make();events=[]
        for t in range(9):events=z.update(t,[track()])
        self.assertEqual(events[0]['severity'],'CRITICAL')
        self.assertEqual(z.update(9,[track(outside=True)])[0]['observed_dwell_seconds'],0)
        self.assertEqual(z.update(10,[track()])[0]['severity'],'SAFE')
        z=self.make()
        for t in [0,1,2,3]:e=z.update(t,[track()])[0]
        self.assertEqual(e['severity'],'SAFE')
        self.assertEqual(z.update(3.5,[track()])[0]['severity'],'WARNING')
    def test_missing_is_unknown_and_time_not_counted(self):
        z=self.make();z.update(0,[track()]);z.update(.5,[track()])
        self.assertIsNone(z.update(.75,[])[0]['severity'])
        self.assertEqual(z.update(1,[track()])[0]['observed_dwell_seconds'],.5)
        z.update(3,[])
        self.assertEqual(z.update(4,[track()])[0]['observed_dwell_seconds'],0)
    def test_ids_timestamp_and_reset(self):
        z=self.make();z.update(0,[track(1),track(2)])
        e=z.update(1,[track(1),track(2,outside=True)])
        self.assertEqual([r['observed_dwell_seconds'] for r in e],[1,0])
        with self.assertRaises(ValueError):z.update(.5,[track()])
        z.reset();self.assertEqual(z.update(0,[track()])[0]['observed_dwell_seconds'],0)

if __name__=='__main__':unittest.main()
