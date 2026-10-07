import unittest
from types import SimpleNamespace
import numpy as np
import torch
from src.ppe_tiled_inference import tile_starts,infer_tiled_heads

class Model:
    names={0:'helmeted_head',1:'no_helmet_head'}
    def predict(self,frame,**kwargs):
        boxes=[SimpleNamespace(cls=torch.tensor(c),conf=torch.tensor(.8),xyxy=torch.tensor([b])) for c,b in [(0,[80.,80.,130.,140.]),(1,[80.,80.,130.,140.]),(1,[0.,90.,50.,140.])]]
        return [SimpleNamespace(boxes=boxes)]
class TiledTests(unittest.TestCase):
    def test_edges_covered(self):
        self.assertEqual(tile_starts(720),[0,240,400])
        self.assertEqual(tile_starts(120),[0])
    def test_conflicting_classes_preserved(self):
        heads,_=infer_tiled_heads(np.zeros((300,300,3),np.uint8),Model())
        self.assertEqual({h['class'] for h in heads if h['bbox_xyxy'][0]==80},{'helmeted_head','no_helmet_head'})
    def test_internal_boundary_rejected(self):
        heads,rejected= infer_tiled_heads(np.zeros((320,600,3),np.uint8),Model())
        self.assertTrue(rejected)
        self.assertTrue(all(x['reason']=='internal_tile_boundary' for x in rejected))
        self.assertTrue(any(h['bbox_xyxy'][0]==0 for h in heads))
