import unittest
from types import SimpleNamespace
import torch
from src.object_recall_ensemble import ObjectRecallEnsemble,object_bundle_version

class ObjectModel:
    def __init__(self,boxes):self.boxes=boxes
    def predict(self,frame,**kwargs):
        return [SimpleNamespace(boxes=[SimpleNamespace(cls=torch.tensor([c]),conf=torch.tensor([p]),xyxy=torch.tensor([b],dtype=torch.float32)) for c,p,b in self.boxes])]
    names={0:'person',1:'forklift'}

class ObjectRecallTests(unittest.TestCase):
    def test_established_baseline_box_not_replaced_by_new_high_score(self):
        model=ObjectRecallEnsemble(ObjectModel([(1,.3,[10,10,30,40])]),ObjectModel([(1,.9,[12,10,32,40])]))
        boxes=model.predict(None)[0].boxes
        self.assertEqual(len(boxes),1)
        self.assertEqual(boxes[0].xyxy[0].tolist(),[10,10,30,40])
        self.assertEqual(boxes[0].detection_source,'v16_baseline')
    def test_supplement_can_start_tracking_when_old_proposal_is_weak(self):
        model=ObjectRecallEnsemble(ObjectModel([(1,.11,[10,10,30,40])]),ObjectModel([(1,.9,[12,10,32,40])]))
        boxes=model.predict(None)[0].boxes
        self.assertEqual(len(boxes),1)
        self.assertGreater(boxes[0].conf.item(),.25)
        self.assertEqual(boxes[0].detection_source,'demo_adaptation')
    def test_new_region_and_other_class_do_not_erase_baseline(self):
        model=ObjectRecallEnsemble(ObjectModel([(1,.8,[10,10,30,40])]),ObjectModel([(0,.9,[10,10,30,40]),(1,.9,[100,10,130,40])]))
        self.assertEqual(len(model.predict(None)[0].boxes),3)
    def test_bundle_hash_includes_both_models(self):
        self.assertNotEqual(object_bundle_version('a','b'),object_bundle_version('a','c'))
        self.assertNotEqual(object_bundle_version('a','b'),object_bundle_version('b','a'))
        self.assertEqual(object_bundle_version('a'),'a')

if __name__=='__main__':unittest.main()
