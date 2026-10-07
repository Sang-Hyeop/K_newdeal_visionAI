import unittest
from src.detection_review_profile import select_review_objects
from src.proximity import Proximity

class ReviewedObjectProfileTests(unittest.TestCase):
    def test_oversized_vehicle_kept_for_review_not_used_for_distance(self):
        shelf={'class':'forklift','confidence':.89,'bbox_xyxy':[2,3,546,714]}
        real={'class':'forklift','confidence':.3,'bbox_xyxy':[636,35,723,205]}
        worker={'class':'person','confidence':.8,'bbox_xyxy':[555,185,603,319]}
        p={'baseline':[shelf],'supplement':[real],'supplement_highres':[real],'person_coco':[worker]}
        accepted,rejected=select_review_objects(p,(720,1280),{'maximum_vehicle_frame_area':.35})
        self.assertEqual(len(accepted),2)
        self.assertEqual(rejected[0]['review_reason'],'oversized_vehicle_requires_review')
        self.assertEqual(rejected[0]['bbox_xyxy'],shelf['bbox_xyxy'])
    def test_vehicle_mast_inside_full_box_is_not_a_second_vehicle(self):
        mast={'class':'forklift','confidence':.8,'bbox_xyxy':[30,10,50,40]}
        full={'class':'forklift','confidence':.4,'bbox_xyxy':[20,5,70,90]}
        p={'baseline':[],'supplement':[mast,full],'supplement_highres':[],'person_coco':[]}
        accepted,rejected=select_review_objects(p,(200,200),{'maximum_vehicle_frame_area':.35})
        self.assertEqual(accepted,[full])
        self.assertEqual(rejected[0]['review_reason'],'contained_vehicle_part_duplicate')

    def test_camera_adaptation_excludes_unselected_baseline_proposals(self):
        old={'class':'forklift','confidence':.9,'bbox_xyxy':[20,20,60,100]}
        p={'baseline':[old],'supplement':[],'supplement_highres':[],'person_coco':[]}
        accepted,_=select_review_objects(p,(200,200),{'maximum_vehicle_frame_area':.35,'vehicle_prediction_keys':['supplement','supplement_highres']})
        self.assertEqual(accepted,[])

    def test_empty_reliable_objects_do_not_create_safe_pair(self):
        p={key:[]for key in ('baseline','supplement','supplement_highres','person_coco')}
        accepted,_=select_review_objects(p,(720,1280),{'maximum_vehicle_frame_area':.35})
        self.assertEqual(Proximity().update(0,accepted,[],(720,1280)),[])
    def test_earlier_alert_bands_use_distance_not_timestamp(self):
        p={'track_id':'p','bbox_xyxy':[220,100,240,200]}
        f={'track_id':'f','bbox_xyxy':[300,100,400,200]}
        self.assertEqual(Proximity(1.5,.65).update(0,[p],[f],(500,500))[0]['severity'],'WARNING')
        p['bbox_xyxy']=[245,100,265,200]
        self.assertEqual(Proximity(1.5,.65).update(0,[p],[f],(500,500))[0]['severity'],'CRITICAL')
