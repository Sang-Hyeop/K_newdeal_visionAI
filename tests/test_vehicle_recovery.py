import unittest
import numpy as np
from src.vehicle_recovery import VehicleRecovery

class RecoveryTests(unittest.TestCase):
 def engine(self,primary,support):
  r=VehicleRecovery(None,None,{'maximum_vehicle_frame_area':.35})
  r.primary='primary';r.support='support';r.predict=lambda model,image,offset=(0,0),size=960:primary if model=='primary' else support
  return r
 def box(self,score=.6):return {'class':'forklift','confidence':score,'bbox_xyxy':[100,100,200,250]}
 def test_two_models_required_for_new_vehicle(self):
  r=self.engine([self.box()],[]);ds,diag=r.update(np.zeros((500,500,3),np.uint8),[],0)
  self.assertEqual(ds,[])
 def test_current_image_consensus_records_real_scores(self):
  r=self.engine([self.box(.3)],[self.box(.5)]);ds,diag=r.update(np.zeros((500,500,3),np.uint8),[],0)
  self.assertEqual(len(ds),1);self.assertEqual(ds[0]['confidence'],.3)
 def test_history_never_emits_a_missing_vehicle(self):
  r=self.engine([],[]);r.history=[(0,[100,100,200,250])]
  ds,diag=r.update(np.zeros((500,500,3),np.uint8),[],.2)
  self.assertEqual(ds,[]);self.assertTrue(diag['history_used_for_search_only'])
 def test_current_vehicle_not_duplicated(self):
  r=self.engine([self.box()],[self.box()]);ds,diag=r.update(np.zeros((500,500,3),np.uint8),[self.box()],0)
  self.assertEqual(len(ds),1);self.assertEqual(diag['accepted'],[])

class ConsensusReviewTests(unittest.TestCase):
 def test_person_like_weak_agreement_is_not_promoted(self):
  from src.vehicle_recovery import review_recovered_vehicles
  d={'class':'forklift','confidence':.23,'bbox_xyxy':[100,100,180,220],'model_source':'vehicle_recovery_current_image','recovery_support':{'confidence':.29,'bbox_xyxy':[100,100,180,220]}}
  kept,rejected=review_recovered_vehicles([d],(720,1280));self.assertFalse(kept);self.assertEqual(len(rejected),1)
 def test_merged_body_is_removed_but_separate_pedestrian_retained(self):
  from src.vehicle_person_cleanup import separate_merged_vehicle_people
  v={'class':'forklift','bbox_xyxy':[380,190,520,360]};merged={'class':'person','bbox_xyxy':[388,212,481,436]};p={'class':'person','bbox_xyxy':[390,289,435,430]}
  kept,rejected=separate_merged_vehicle_people([v,merged,p]);self.assertIn(p,kept);self.assertNotIn(merged,kept);self.assertEqual(len(rejected),1)
 def test_high_confidence_stockpile_without_person_not_added(self):
  from src.vehicle_recovery import review_recovered_vehicles
  d={'class':'forklift','confidence':.8,'bbox_xyxy':[640,280,780,440],'model_source':'vehicle_recovery_current_image','recovery_support':{'confidence':.8,'bbox_xyxy':[640,280,780,440]}}
  kept,rejected=review_recovered_vehicles([d],(720,1280));self.assertFalse(kept);self.assertEqual(rejected[0]['review_reason'],'recovery_without_current_person_context')
 def test_current_rider_context_allows_recovery(self):
  from src.vehicle_recovery import review_recovered_vehicles
  d={'class':'forklift','confidence':.6,'bbox_xyxy':[310,250,490,420],'model_source':'vehicle_recovery_current_image','recovery_support':{'confidence':.6,'bbox_xyxy':[310,250,490,420]}}
  person={'class':'person','confidence':.8,'bbox_xyxy':[330,260,400,340]}
  kept,rejected=review_recovered_vehicles([d,person],(720,1280));self.assertEqual(len(kept),2);self.assertFalse(rejected)
