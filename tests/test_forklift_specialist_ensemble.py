import unittest
from types import SimpleNamespace
import torch
from src.forklift_specialist_ensemble import ForkliftSpecialistEnsemble,supplement_forklift_records
class Model:
    def __init__(self,names,rows):self.names,self.rows=names,rows
    def predict(self,frame,**kwargs):return [SimpleNamespace(names=self.names,boxes=[SimpleNamespace(cls=torch.tensor([c]),conf=torch.tensor([s]),xyxy=torch.tensor([b],dtype=torch.float32))for c,s,b in self.rows])]
class SpecialistRoutingTests(unittest.TestCase):
    def test_single_class_zero_becomes_forklift_one_without_altering_person(self):
        base=Model({0:'person',1:'forklift'},[(0,.8,[1,2,5,12])]);specialist=Model({0:'forklift'},[(0,.6,[20,20,40,60])]);result=ForkliftSpecialistEnsemble(base,specialist).predict(None)[0]
        self.assertEqual([int(b.cls.item())for b in result.boxes],[0,1]);self.assertEqual(result.names[1],'forklift')
    def test_unknown_mapping_is_rejected(self):
        with self.assertRaises(ValueError):ForkliftSpecialistEnsemble(Model({0:'person',1:'forklift'},[]),Model({0:'person'},[]))
    def test_weaker_specialist_does_not_replace_confirmed_prior_box(self):
        base=Model({0:'person',1:'forklift'},[(1,.8,[20,20,40,60])]);specialist=Model({0:'forklift'},[(0,.3,[20,20,40,60])]);result=ForkliftSpecialistEnsemble(base,specialist).predict(None)[0];self.assertEqual(len(result.boxes),1);self.assertAlmostEqual(float(result.boxes[0].conf.item()),.8,places=5)
    def test_empty_specialist_does_not_fabricate_detection(self):
        self.assertEqual(ForkliftSpecialistEnsemble(Model({0:'person',1:'forklift'},[]),Model({0:'forklift'},[])).predict(None)[0].boxes,[])

class CachedSpecialistRoutingTests(unittest.TestCase):
    def test_weak_actual_proposal_is_upgraded_without_mutating_cached_evidence(self):
        old=[{'class':'forklift','confidence':.1,'bbox_xyxy':[10,10,50,80]},{'class':'person','confidence':.6,'bbox_xyxy':[10,10,50,80]}]
        observed=[{'class':'forklift','confidence':.7,'bbox_xyxy':[10,10,50,80]}]
        result=supplement_forklift_records(old,observed)
        self.assertEqual(old[0]['confidence'],.1)
        self.assertEqual([r['class']for r in result],['person','forklift'])
        self.assertEqual(result[-1]['model_source'],'factory_forklift_specialist')
    def test_observed_person_cannot_be_mislabeled_as_forklift(self):
        with self.assertRaises(ValueError):supplement_forklift_records([],[{'class':'person','confidence':.9,'bbox_xyxy':[10,10,50,80]}])
