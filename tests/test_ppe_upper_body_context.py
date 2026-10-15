import unittest
from types import SimpleNamespace
import numpy as np
import torch
from src.ppe_final_detector import FinalPPEDetector
from src.ppe_person_crop import head_owner

class UpperBodyContextTests(unittest.TestCase):
 def detector(self,box):
  calls=[]
  class Model:
   def predict(self,frame,**kwargs):
    calls.append((frame.shape,kwargs));return [SimpleNamespace(boxes=[SimpleNamespace(xyxy=torch.tensor([box]),cls=torch.tensor(1),conf=torch.tensor(.8))])]
  d=object.__new__(FinalPPEDetector);d.model=Model();d.filter=lambda heads,**kwargs:heads
  return d,calls
 def test_crop_offsets_and_unchanged_proposal_threshold(self):
  d,calls=self.detector([40.,20.,60.,40.]);heads=d.predict_upper_body_context(np.zeros((300,300,3),np.uint8),[[100,100,160,260]])
  self.assertEqual(heads[0]['box'],[116.,96.,136.,116.]);self.assertEqual(calls[0][0],(120,108,3));self.assertEqual(calls[0][1]['conf'],.15);self.assertEqual(calls[0][1]['imgsz'],640)
  self.assertEqual(head_owner(heads[0]['box'],[[100,100,160,260]],300),0)
 def test_internal_crop_edge_cannot_fabricate_partial_head(self):
  d,_=self.detector([0.,0.,20.,20.]);self.assertEqual(d.predict_upper_body_context(np.zeros((300,300,3),np.uint8),[[100,100,160,260]]),[])
 def test_invalid_person_box_rejected(self):
  d,_=self.detector([2.,2.,20.,20.])
  with self.assertRaises(ValueError):d.predict_upper_body_context(np.zeros((300,300,3),np.uint8),[[100,100,90,260]])
