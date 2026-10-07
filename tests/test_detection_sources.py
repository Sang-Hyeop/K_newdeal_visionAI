import unittest
from src.detection_sources import route_detections,model_version

class DetectionSourceTests(unittest.TestCase):
    def test_explicit_class_routing_preserves_forklift_and_avoids_person_union(self):
        objects=[{'class':'person','confidence':.9},{'class':'forklift','confidence':.3}]
        people=[{'class':'person','confidence':.4},{'class':'car','confidence':.8}]
        r=route_detections(objects,people)
        self.assertEqual([(d['class'],d['confidence']) for d in r],[('forklift',.3),('person',.4)])
        self.assertEqual(objects[0],{'class':'person','confidence':.9})
    def test_empty_secondary_source_does_not_silently_restore_unverified_people(self):
        self.assertEqual(route_detections([{'class':'person'}],[]),[])
    def test_default_source_and_hash_remain_compatible(self):
        self.assertEqual(route_detections([{'class':'person'}]),[{'class':'person'}])
        self.assertEqual(model_version('a'),'a')
        self.assertNotEqual(model_version('a','b'),model_version('a','c'))
        self.assertNotEqual(model_version('a','b'),model_version('b','a'))
