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
