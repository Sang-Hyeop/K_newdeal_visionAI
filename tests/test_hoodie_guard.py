import unittest
from src.hoodie_guard import apply_hood_guard

class HoodGuardTests(unittest.TestCase):
    def event(self,state='SAFE'):
        return {'severity':state,'observation_status':'confirmed','person_bbox_xyxy':[0,0,100,200]}
    def detection(self,cls=0,conf=.8,box=None):
        return {'class_id':cls,'confidence':conf,'bbox_xyxy':box or [0,0,100,200]}
    def test_hood_vetoes_safe_without_mutating_input(self):
        source=self.event();out=apply_hood_guard([source],[self.detection()])[0]
        self.assertIsNone(out['severity']);self.assertEqual(source['severity'],'SAFE');self.assertEqual(out['observation_status'],'unconfirmed')
    def test_normal_never_establishes_ppe_safe(self):
        self.assertIsNone(apply_hood_guard([self.event(None)],[self.detection(1)])[0]['severity'])
    def test_hood_does_not_erase_bare_warning(self):
        self.assertEqual(apply_hood_guard([self.event('WARNING')],[self.detection()])[0]['severity'],'WARNING')
    def test_other_person_or_weak_hood_does_not_veto(self):
        for d in [self.detection(conf=.2),self.detection(box=[200,0,300,200])]:
            self.assertEqual(apply_hood_guard([self.event()],[d])[0]['severity'],'SAFE')
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):apply_hood_guard([],[],minimum_confidence=float('nan'))
