"""Canonical output routing: a complete build replaces current; preview never does."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import handoff

class CurrentHandoffTests(unittest.TestCase):
 def fixture(self,root):
  (root/'configs').mkdir();(root/'configs/team-runtime-index.json').write_text(json.dumps({'videos':[{'presentation_video_number':3,'diagnostic_root':'outputs/diagnostics/current/video3'}]}))
 def fake_build(self,*args):
  dest=Path(args[args.index('--output')+1])/'video3';dest.mkdir(parents=True);(dest/'demo.mp4').write_bytes(b'current preview')
 def test_complete_run_promotes_current_and_removes_staging_folder(self):
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);self.fixture(root)
   with patch.object(handoff,'ROOT',root),patch.object(handoff,'call',side_effect=self.fake_build),patch.object(handoff,'promote_current')as promote:
    handoff.run_video(3);self.assertEqual(promote.call_count,1);self.assertEqual(promote.call_args.args[0],3)
   self.assertEqual(list((root/'outputs/runtime').iterdir()),[])
 def test_short_preview_does_not_overwrite_full_current_result(self):
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);self.fixture(root)
   with patch.object(handoff,'ROOT',root),patch.object(handoff,'call',side_effect=self.fake_build),patch.object(handoff,'promote_current')as promote:
    handoff.run_video(3,max_seconds=.4);promote.assert_not_called()
   self.assertEqual([p.name for p in(root/'outputs/runtime').iterdir()],['preview_video3.mp4'])

class FinalModelLockTests(unittest.TestCase):
 def test_same_size_weight_or_policy_tampering_is_rejected(self):
  for group in ['models','support_and_approved_policy']:
   with self.subTest(group=group),tempfile.TemporaryDirectory()as folder:
    root=Path(folder);(root/'configs').mkdir();asset=root/'asset';asset.write_bytes(b'good')
    lock={'models':[],'support_and_approved_policy':[]}
    lock[group]=[{'path':'asset','bytes':4,'sha256':hashlib.sha256(b'good').hexdigest()}]
    (root/'configs/final-model-lock.json').write_text(json.dumps(lock))
    with patch.object(handoff,'ROOT',root):
     handoff.check_final_models()
     asset.write_bytes(b'evil')
     with self.assertRaisesRegex(ValueError,'checksum mismatch'):handoff.check_final_models()
 def test_missing_final_lock_is_rejected(self):
  with tempfile.TemporaryDirectory()as folder,patch.object(handoff,'ROOT',Path(folder)):
   with self.assertRaisesRegex(ValueError,'Missing final model lock'):handoff.check_final_models()
