import unittest
from types import SimpleNamespace
import numpy as np
from src.ppe_head_context import refine_weak_heads
class EmptyModel:
 def __init__(self):self.calls=[]
 def predict(self,image,**kwargs):self.calls.append(image.shape);return [SimpleNamespace(boxes=[])]
class ContextTests(unittest.TestCase):
 def test_only_observed_weak_bare_candidates_are_rechecked(self):
  model=EmptyModel();frame=np.zeros((200,300,3),dtype=np.uint8)
  heads=[{'class':'helmeted_head','confidence':.3,'bbox_xyxy':[20,20,40,40]}, {'class':'no_helmet_head','confidence':.7,'bbox_xyxy':[100,100,120,120]}]
  self.assertEqual(refine_weak_heads(frame,heads,model),[]);self.assertFalse(model.calls)
  heads.append({'class':'no_helmet_head','confidence':.3,'bbox_xyxy':[1,1,21,21]})
  refine_weak_heads(frame,heads,model);self.assertEqual(len(model.calls),2)
  self.assertTrue(all(s[0]>0 and s[1]>0 for s in model.calls))
 def test_duplicate_candidates_do_not_repeat_crop_work(self):
  model=EmptyModel();head={'class':'no_helmet_head','confidence':.3,'bbox_xyxy':[20,20,40,40]}
  refine_weak_heads(np.zeros((200,300,3),dtype=np.uint8),[head,dict(head)],model);self.assertEqual(len(model.calls),2)
