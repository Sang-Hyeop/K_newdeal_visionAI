import unittest
from types import SimpleNamespace
import numpy as np
import torch
from src.ppe_person_crop import infer_person_ppe


class FakeModel:
    names = {0: 'helmeted_head', 1: 'no_helmet_head'}

    def __init__(self, detections):
        self.detections = detections

    def predict(self, frame, **kwargs):
        boxes = [SimpleNamespace(xyxy=torch.tensor([xyxy]), cls=torch.tensor(cls),
                                 conf=torch.tensor(.8)) for cls, xyxy in self.detections]
        return [SimpleNamespace(boxes=boxes)]


class PPEAssignmentTests(unittest.TestCase):
    def observe(self, detections):
        return infer_person_ppe(np.zeros((300,300,3),dtype=np.uint8),
                                [[100,100,160,260]], FakeModel(detections))[0]

    def test_no_head_evidence_is_unknown(self):
        self.assertEqual(self.observe([])['state'], 'unknown')

    def test_body_box_cannot_confirm_helmet(self):
        row=self.observe([(0,[9,16,69,104])])
        self.assertEqual(row['state'],'unknown')
        self.assertEqual(len(row['rejected_candidates']),1)

    def test_crop_coordinates_return_to_original_frame(self):
        row=self.observe([(0,[20,16,45,40])])
        self.assertEqual(row['head_candidates'][0]['bbox_xyxy'],[111,100,136,124])
        self.assertEqual(row['state'],'helmet_detected')

    def test_mixed_classes_do_not_confirm_helmet(self):
        row=self.observe([(0,[20,16,45,40]),(1,[20,16,45,40])])
        self.assertEqual(row['state'],'conflicting_evidence')

    def test_no_helmet_is_candidate_not_violation(self):
        self.assertEqual(self.observe([(1,[20,16,45,40])])['state'],'no_helmet_candidate')

    def test_full_frame_head_survives_crop_miss(self):
        row=infer_person_ppe(np.zeros((300,300,3),dtype=np.uint8),[[100,100,160,260]],
                             FakeModel([]),full_frame_heads=[{'class':'helmeted_head',
                             'confidence':.8,'bbox_xyxy':[111,100,136,124]}])[0]
        self.assertEqual(row['state'],'helmet_detected')
        self.assertEqual(row['head_candidates'][0]['source'],'full_frame')

    def test_neighbor_helmet_cannot_confirm_foreground_person(self):
        rows=infer_person_ppe(np.zeros((800,1000,3),dtype=np.uint8),
             [[615,349,769,641],[656,278,740,425]],FakeModel([]),
             full_frame_heads=[{'class':'helmeted_head','confidence':.8,
                                'bbox_xyxy':[678,280,718,324]}])
        self.assertEqual(rows[0]['state'],'unknown')
        self.assertEqual(rows[1]['state'],'helmet_detected')


if __name__=='__main__':
    unittest.main()
