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

class WeakProposalRoutingTests(unittest.TestCase):
    def test_weak_background_is_diagnostic_not_routed(self):
        real={'class':'forklift','confidence':.86,'bbox_xyxy':[600,80,700,400]}
        background={'class':'forklift','confidence':.34,'bbox_xyxy':[710,2,750,80]}
        low_person={'class':'person','confidence':.24,'bbox_xyxy':[900,2,1000,150]}
        worker={'class':'person','confidence':.41,'bbox_xyxy':[440,270,530,510]}
        p={'baseline':[],'supplement':[real],'supplement_highres':[background],'person_coco':[worker,low_person]}
        profile={'maximum_vehicle_frame_area':.35,'minimum_confidence_by_class':{'person':.25,'forklift':.4}}
        kept,rejected=select_review_objects(p,(720,1280),profile)
        self.assertEqual(kept,[worker,real])
        self.assertEqual(len(rejected),2)
        self.assertTrue(all(d['review_reason']=='low_confidence_requires_review' for d in rejected))
        self.assertEqual({d['confidence'] for d in rejected},{.34,.24})
    def test_two_strong_real_vehicles_at_start_are_preserved(self):
        vehicles=[{'class':'forklift','confidence':c,'bbox_xyxy':b} for c,b in [(.83,[686,10,727,94]),(.79,[639,66,718,203])]]
        p={'baseline':[],'supplement':[],'supplement_highres':vehicles,'person_coco':[]}
        kept,rejected=select_review_objects(p,(720,1280),{'maximum_vehicle_frame_area':.35,'minimum_confidence_by_class':{'forklift':.4}})
        self.assertEqual(len(kept),2);self.assertEqual(rejected,[])

class VehicleReviewSupportTests(unittest.TestCase):
    def test_supported_weak_vehicle_retained_and_strong_background_rejected(self):
        vehicle={'class':'forklift','confidence':.2,'bbox_xyxy':[600,80,700,400]}
        shelf={'class':'forklift','confidence':.61,'bbox_xyxy':[710,2,750,80]}
        p={'baseline':[],'supplement':[vehicle,shelf],'supplement_highres':[],'person_coco':[],'vehicle_support':[dict(vehicle,confidence=.15)]}
        kept,rejected=select_review_objects(p,(720,1280),{'maximum_vehicle_frame_area':.35,'vehicle_support_required':True})
        self.assertEqual(kept,[vehicle]);self.assertEqual(rejected[0]['review_reason'],'vehicle_not_supported_by_review_model')
    def test_absent_support_does_not_confirm_vehicle(self):
        d={'class':'forklift','confidence':.9,'bbox_xyxy':[20,20,50,100]}
        p={'baseline':[],'supplement':[d],'supplement_highres':[],'person_coco':[]}
        kept,rejected=select_review_objects(p,(200,200),{'maximum_vehicle_frame_area':.35,'vehicle_support_required':True})
        self.assertEqual(kept,[]);self.assertEqual(len(rejected),1)

class ReviewedPersonRoutingTests(unittest.TestCase):
 def test_seated_baseline_and_walking_coco_person_both_preserved(self):
  seated={'class':'person','confidence':.96,'bbox_xyxy':[1540,400,1670,600]}
  walking={'class':'person','confidence':.75,'bbox_xyxy':[380,50,440,200]}
  background={'class':'forklift','confidence':.32,'bbox_xyxy':[0,100,220,450]}
  vehicle={'class':'forklift','confidence':.6,'bbox_xyxy':[800,200,1400,900]}
  p={'baseline':[seated,background],'person_coco':[walking],'supplement':[],'supplement_highres':[vehicle]}
  kept,rejected=select_review_objects(p,(1080,1920),{'person_prediction_keys':['person_coco','baseline'],'vehicle_prediction_keys':['supplement_highres'],'maximum_vehicle_frame_area':.35})
  self.assertEqual(sum(d['class']=='person' for d in kept),2);self.assertIn(vehicle,kept);self.assertNotIn(background,kept)

class CameraRouteIsolationTests(unittest.TestCase):
 def test_two_camera_models_do_not_replace_shared_bundle(self):
  from types import SimpleNamespace
  from src.detection_review_profile import build_review_models
  base=SimpleNamespace(baseline='base',supplement='shared')
  first=build_review_models(base,{'vehicle_weights':'video1','vehicle_support_required':True,'vehicle_support_weights':'support'},lambda path:path)
  second=build_review_models(base,{'vehicle_weights':'video2'},lambda path:path)
  self.assertEqual(first.supplement,'video1');self.assertEqual(second.supplement,'video2');self.assertEqual(base.supplement,'shared');self.assertEqual(first.review_support,'support');self.assertFalse(hasattr(second,'review_support'))

class MultiVehicleEnvelopeTests(unittest.TestCase):
 def test_two_vehicle_proposals_not_dropped_inside_combined_box(self):
  full={'class':'forklift','confidence':.8,'bbox_xyxy':[10,20,110,100]}
  left={'class':'forklift','confidence':.4,'bbox_xyxy':[10,20,65,100]}
  right={'class':'forklift','confidence':.4,'bbox_xyxy':[55,20,110,100]}
  p={'baseline':[],'supplement':[full,left,right],'supplement_highres':[],'person_coco':[]}
  kept,rejected=select_review_objects(p,(400,400),{'maximum_vehicle_frame_area':.35,'review_multi_vehicle_envelopes':True})
  self.assertEqual(kept,[left,right]);self.assertEqual(rejected[0]['review_reason'],'multi_vehicle_envelope_requires_review')
