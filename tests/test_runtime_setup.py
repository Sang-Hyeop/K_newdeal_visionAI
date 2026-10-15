import hashlib,importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('setup_runtime',Path(__file__).resolve().parents[1]/'scripts/setup_runtime.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RuntimeSetupTests(unittest.TestCase):
 def fixture(self,folder):
  payload=b'test model';archive=folder/'asset.zip'
  with zipfile.ZipFile(archive,'w')as z:z.writestr('models/demo.pt',payload)
  return archive,{'bytes':archive.stat().st_size,'sha256':m.digest(archive),'files':[{'path':'models/demo.pt','bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}]}
 def test_verified_install_and_idempotent_repeat(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);a,c=self.fixture(root);self.assertEqual(m.install_archive(root,c,a),(1,0));self.assertEqual(m.install_archive(root,c,a),(0,1))
 def test_existing_changed_model_is_preserved(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);a,c=self.fixture(root);(root/'models').mkdir();p=root/'models/demo.pt';p.write_bytes(b'local edits')
   with self.assertRaisesRegex(ValueError,'preserved'):m.install_archive(root,c,a)
   self.assertEqual(p.read_bytes(),b'local edits')
 def test_corrupt_archive_is_rejected_before_install(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);a,c=self.fixture(root);a.write_bytes(b'corrupt')
   with self.assertRaisesRegex(ValueError,'checksum'):m.install_archive(root,c,a)
   self.assertFalse((root/'models').exists())
 def test_path_traversal_and_source_code_targets_are_rejected(self):
  for name in ['../escape','models/../../escape','src/proximity.py','/tmp/file','models/README.md']:
   with self.subTest(name=name),self.assertRaises(ValueError):m.targets(Path.cwd(),{'files':[{'path':name}]})

class RuntimePresentationPathTests(unittest.TestCase):
 def fixture(self,root):
  old='outputs/diagnostics/review/video7/detections.jsonl';new='outputs/diagnostics/review/video5/detections.jsonl';payload=b'real detection cache';archive=root/'asset.zip'
  with zipfile.ZipFile(archive,'w')as z:z.writestr(old,payload)
  item={'archive_path':old,'path':new,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
  return archive,{'bytes':archive.stat().st_size,'sha256':m.digest(archive),'files':[item]},old,new,payload
 def test_original_release_member_installs_to_current_path(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);a,c,old,new,data=self.fixture(root);self.assertEqual(m.install_archive(root,c,a),(1,0));self.assertEqual((root/new).read_bytes(),data);self.assertFalse((root/old).exists());self.assertEqual(m.install_archive(root,c,a),(0,1))
 def test_matching_legacy_cache_removed_after_new_path_verified(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);a,c,old,new,data=self.fixture(root);(root/old).parent.mkdir(parents=True);(root/old).write_bytes(data);m.install_archive(root,c,a);self.assertFalse((root/old).parent.exists());self.assertEqual((root/new).read_bytes(),data)
 def test_changed_legacy_cache_is_preserved(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);a,c,old,new,data=self.fixture(root);(root/old).parent.mkdir(parents=True);(root/old).write_bytes(b'local changes');m.install_archive(root,c,a);self.assertEqual((root/old).read_bytes(),b'local changes');self.assertEqual((root/new).read_bytes(),data)
 def test_conflicting_new_path_preserves_both_local_files(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);a,c,old,new,data=self.fixture(root)
   for name,payload in [(old,data),(new,b'local changes')]:
    (root/name).parent.mkdir(parents=True,exist_ok=True);(root/name).write_bytes(payload)
   with self.assertRaisesRegex(ValueError,'preserved'):m.install_archive(root,c,a)
   self.assertEqual((root/old).read_bytes(),data);self.assertEqual((root/new).read_bytes(),b'local changes')
 def test_archive_member_traversal_is_rejected(self):
  for name in ['../escape','outputs/../../escape','src/proximity.py','/tmp/file','outputs\\escape']:
   with self.subTest(name=name),self.assertRaises(ValueError):m.targets(Path.cwd(),{'files':[{'path':'outputs/good.json','archive_path':name}]})
 def test_two_members_cannot_overwrite_same_destination(self):
  with self.assertRaisesRegex(ValueError,'Duplicate'):m.targets(Path.cwd(),{'files':[{'path':'outputs/current.json','archive_path':'outputs/old1.json'},{'path':'outputs/current.json','archive_path':'outputs/old2.json'}]})
 def test_migration_source_cannot_be_another_install_destination(self):
  with self.assertRaisesRegex(ValueError,'overlaps'):m.targets(Path.cwd(),{'files':[{'path':'outputs/current.json','archive_path':'outputs/old.json'},{'path':'outputs/old.json','archive_path':'outputs/older.json'}]})
