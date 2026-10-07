import unittest
from types import SimpleNamespace
import numpy as np,torch
from src.forklift_tiled_inference import infer_tiled_forklifts
class Model:
    names={0:'person',1:'forklift'}
    def __init__(self,box):self.box=box
    def predict(self,frame,**kw):return [SimpleNamespace(boxes=[SimpleNamespace(cls=torch.tensor([1]),conf=torch.tensor([.7]),xyxy=torch.tensor([self.box],dtype=torch.float32)),SimpleNamespace(cls=torch.tensor([0]),conf=torch.tensor([.9]),xyxy=torch.tensor([[10,10,20,20]],dtype=torch.float32))])]
class TileCoordinateTests(unittest.TestCase):
    def test_native_coordinates_shift_and_person_not_remapped(self):
        ds,_=infer_tiled_forklifts(np.zeros((100,200,3),np.uint8),Model([10,10,30,30]),size=100,stride=80)
        self.assertEqual({tuple(d['bbox_xyxy'])for d in ds},{(10,10,30,30),(90,10,110,30),(110,10,130,30)})
        self.assertTrue(all(d['class']=='forklift'for d in ds))
    def test_internal_edge_cut_rejected_but_real_camera_edge_allowed(self):
        ds,rejected=infer_tiled_forklifts(np.zeros((100,200,3),np.uint8),Model([0,10,30,30]),size=100,stride=80)
        self.assertEqual(len(ds),1);self.assertEqual(len(rejected),2);self.assertEqual(ds[0]['bbox_xyxy'][0],0)
    def test_empty_image_search_does_not_create_unknown_box(self):
        class Empty:
            names={0:'forklift'}
            def predict(self,frame,**kw):return [SimpleNamespace(boxes=[])]
        self.assertEqual(infer_tiled_forklifts(np.zeros((100,100,3),np.uint8),Empty(),size=100,stride=80),([],[]))
