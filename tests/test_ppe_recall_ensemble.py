import unittest
from types import SimpleNamespace
import torch
from src.ppe_recall_ensemble import PPERecallEnsemble
from src.ppe_person_crop import infer_person_ppe
import numpy as np

class FakeModel:
    names={0:'helmeted_head',1:'no_helmet_head'}
    def __init__(self,boxes):self.boxes=boxes
    def predict(self,frame,**kwargs):
        return [SimpleNamespace(boxes=[SimpleNamespace(cls=torch.tensor([c]),conf=torch.tensor([p]),xyxy=torch.tensor([b],dtype=torch.float32)) for c,p,b in self.boxes])]

class RecallEnsembleTests(unittest.TestCase):
    def test_baseline_heads_survive_supplement(self):
        baseline=FakeModel([(0,.8,[1,1,8,8]),(1,.7,[20,1,28,8])])
        supplement=FakeModel([(0,.99,[40,1,48,8]),(1,.9,[21,1,29,8]),(1,.6,[50,1,58,8])])
        boxes=PPERecallEnsemble(baseline,supplement).predict(None)[0].boxes
        self.assertEqual(len(boxes),3)
        self.assertEqual(sum(int(b.cls.item())==0 for b in boxes),1)
        duplicate=next(b for b in boxes if 'demo_supplement' in b.model_sources and 'baseline' in b.model_sources)
        self.assertAlmostEqual(duplicate.conf.item(),.9,places=5)
    def test_union_preserves_baseline_coordinates_and_adds_both_classes(self):
        old=FakeModel([(0,.8,[1,1,8,8])]);new=FakeModel([(0,.9,[2,1,9,8]),(1,.7,[30,1,38,8])])
        boxes=PPERecallEnsemble(old,new,preserve_union=True).predict(None)[0].boxes
        self.assertEqual(len(boxes),3)
        self.assertEqual(boxes[0].xyxy[0].tolist(),[1,1,8,8])
        self.assertEqual(boxes[0].model_sources,['baseline'])
    def test_helmet_specialist_cannot_overwrite_bare_head_channel(self):
        specialist=FakeModel([(0,.9,[30,1,38,8]),(1,.99,[40,1,48,8])])
        boxes=PPERecallEnsemble(FakeModel([]),FakeModel([(1,.8,[1,1,8,8])]),preserve_union=True,helmet_specialist=specialist).predict(None)[0].boxes
        self.assertEqual(len(boxes),2)
        self.assertEqual(sum(int(b.cls.item())==1 for b in boxes),1)
        self.assertEqual(boxes[1].model_sources,['helmet_specialist'])
    def test_conflicting_models_stay_unknown(self):
        ensemble=PPERecallEnsemble(FakeModel([(0,.8,[10,10,20,20])]),FakeModel([(1,.9,[10,10,20,20])]))
        observation=infer_person_ppe(np.zeros((120,80,3),dtype=np.uint8),[[10,10,40,110]],ensemble)[0]
        self.assertEqual(observation['state'],'conflicting_evidence')
        self.assertEqual({r['class'] for r in observation['head_candidates']},{'helmeted_head','no_helmet_head'})
        self.assertTrue(all('model_sources' in r for r in observation['head_candidates']))

if __name__=='__main__':unittest.main()
