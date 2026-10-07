import unittest
from types import SimpleNamespace
import torch
from src.object_recall_ensemble import ObjectRecallEnsemble


class FakeModel:
    names = {0: 'person', 1: 'forklift'}

    def __init__(self, boxes):
        self.boxes = boxes

    def predict(self, frame, **kwargs):
        return [SimpleNamespace(boxes=[
            SimpleNamespace(cls=torch.tensor([c]), conf=torch.tensor([p]), xyxy=torch.tensor([b], dtype=torch.float32))
            for c, p, b in self.boxes
        ])]


class ObjectRecallEnsembleTests(unittest.TestCase):
    def test_baseline_boxes_survive_weaker_overlap(self):
        baseline = FakeModel([(1, 0.4, [10, 10, 50, 50]), (0, 0.3, [80, 10, 100, 40])])
        supplement = FakeModel([(1, 0.95, [12, 12, 48, 48]), (1, 0.9, [200, 20, 260, 90])])
        boxes = ObjectRecallEnsemble(baseline, supplement).predict(None)[0].boxes
        self.assertEqual(len(boxes), 3)
        kept_baseline = next(b for b in boxes if b.detection_source == 'v16_baseline' and int(b.cls.item()) == 1)
        self.assertAlmostEqual(kept_baseline.conf.item(), 0.4, places=5)
        self.assertTrue(any(b.detection_source == 'demo_adaptation' and int(b.cls.item()) == 1 and b.conf.item() > 0.8 for b in boxes))

    def test_uncovered_supplement_fills_gap(self):
        baseline = FakeModel([(0, 0.2, [0, 0, 10, 10])])
        supplement = FakeModel([(1, 0.8, [40, 40, 80, 80])])
        boxes = ObjectRecallEnsemble(baseline, supplement).predict(None)[0].boxes
        self.assertTrue(any(b.detection_source == 'demo_adaptation' and int(b.cls.item()) == 1 for b in boxes))

    def test_weak_overlapping_baseline_yields_to_stronger_supplement(self):
        baseline = FakeModel([(1, 0.2, [10, 10, 50, 50])])
        supplement = FakeModel([(1, 0.9, [12, 12, 48, 48])])
        boxes = ObjectRecallEnsemble(baseline, supplement).predict(None)[0].boxes
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].detection_source, 'demo_adaptation')
        self.assertAlmostEqual(boxes[0].conf.item(), 0.9, places=5)


if __name__ == '__main__':
    unittest.main()
