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
    def test_conflicting_models_stay_unknown(self):
        ensemble=PPERecallEnsemble(FakeModel([(0,.8,[10,10,20,20])]),FakeModel([(1,.9,[10,10,20,20])]))
        observation=infer_person_ppe(np.zeros((120,80,3),dtype=np.uint8),[[10,10,40,110]],ensemble)[0]
        self.assertEqual(observation['state'],'conflicting_evidence')
        self.assertEqual({r['class'] for r in observation['head_candidates']},{'helmeted_head','no_helmet_head'})
        self.assertTrue(all('model_sources' in r for r in observation['head_candidates']))

if __name__=='__main__':unittest.main()
