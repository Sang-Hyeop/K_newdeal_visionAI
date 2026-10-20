# 역할: 구역 기능의 객체 표시 동작을 회귀 검증합니다.
import unittest
from unittest.mock import patch
import numpy as np
from src.scenario_render import render
class ZoneObjectRenderTests(unittest.TestCase):
 def test_object_first_keeps_lane_dwell_label(self):
  frame=np.zeros((300,400,3),dtype=np.uint8)
  event={'track_id':'p','severity':'WARNING','observation_status':'confirmed','person_bbox_xyxy':[40,100,100,240],'observed_dwell_seconds':7.3}
  with patch('src.scenario_render.cv2.putText',side_effect=lambda image,*a,**kw:image)as text:
   render(frame,{'zone_dwell':[event]},detections=[{'class':'person','confidence':.8,'bbox_xyxy':event['person_bbox_xyxy']}])
  labels=[c.args[1]for c in text.call_args_list];self.assertTrue(any('LANE WARNING 7.3s' in label for label in labels));self.assertTrue(any('PERSON' in label for label in labels))
