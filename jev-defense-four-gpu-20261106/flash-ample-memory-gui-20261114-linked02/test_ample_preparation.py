"""New storage, capacity-history and resource-boundary checks; no inference."""
import copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'flash-gated-full-gui-20261113/package-linked02/flash')]
from capacity_gate import fifty_image_load,image_count
from expanded_guard import validate_compute
from evidence_store import store

class Tests(unittest.TestCase):
 def source(self):
  m=[{'role':'system','content':'frozen native system'}]
  for i in range(15):
   if i:m.append({'role':'assistant','content':'actual prior native action '+str(i)})
   m.append({'role':'user','content':[{'type':'text','text':'actual task/history block'},{'type':'image_url','image_url':{'url':'data:image/png;base64,exact-'+str(i)}}]})
  return {'messages':m,'max_tokens':2048,'temperature':0}
 def test_fifty_images_preserve_whole_source_and_no_mutation(self):
  source=self.source();before=copy.deepcopy(source);result=fifty_image_load(source)
  self.assertEqual(source,before);self.assertEqual(image_count(result),50);self.assertEqual(result['messages'][:30],source['messages']);self.assertEqual(len(result['messages']),100)
 def test_malformed_source_rejected(self):
  x=self.source();x['messages'].pop()
  with self.assertRaises(ValueError):fifty_image_load(x)
 def test_foreign_compute_on_one_primary_gpu_rejected(self):
  cards={i:{'uuid':str(i)}for i in range(8)};compute=[{'uuid':str(i),'pid':10}for i in range(7)]+[{'uuid':'7','pid':11},{'uuid':'2','pid':99}]
  with self.assertRaises(RuntimeError):validate_compute(cards,compute,{**{i:10 for i in range(7)},7:11})
 def test_late_foreign_on_Flash_rejected(self):
  with self.assertRaises(RuntimeError):validate_compute({7:{'uuid':'7'}},[{'uuid':'7','pid':99}],{7:11})
 def test_empty_GPU_requires_no_compute_even_same_UID(self):
  with self.assertRaises(RuntimeError):validate_compute({0:{'uuid':'0'}},[{'uuid':'0','pid':10}],{0:None})
 def test_verified_primary_and_Flash_accepted(self):
  validate_compute({i:{'uuid':str(i)}for i in range(8)},[{'uuid':str(i),'pid':10 if i<7 else 11}for i in range(8)],{**{i:10 for i in range(7)},7:11})
 def test_tensor_link_requires_actual_byte_equality(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);(p/'prepared').write_bytes(b'original actual bytes');mode=store(p/'forward',b'original actual bytes',p/'prepared')
   self.assertEqual(mode,'full-byte-verified-hardlink');self.assertEqual((p/'forward').read_bytes(),(p/'prepared').read_bytes());self.assertEqual((p/'forward').stat().st_ino,(p/'prepared').stat().st_ino)
 def test_different_actual_forward_saved_independently(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);(p/'prepared').write_bytes(b'original');mode=store(p/'forward',b'different',p/'prepared')
   self.assertEqual(mode,'independent-raw-bytes');self.assertEqual((p/'forward').read_bytes(),b'different');self.assertEqual((p/'prepared').read_bytes(),b'original')
 def test_existing_evidence_cannot_be_overwritten(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'terminal';p.write_bytes(b'sealed')
   with self.assertRaises(FileExistsError):store(p,b'new')
   self.assertEqual(p.read_bytes(),b'sealed')
if __name__=='__main__':unittest.main(verbosity=2)
