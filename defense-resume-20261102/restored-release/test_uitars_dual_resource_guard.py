"""Boundary checks against accidental sharing, incomplete queries and wrong ownership."""
import unittest
from uitars_dual_resource_guard import resource_reasons

class GuardTests(unittest.TestCase):
 def setUp(self):
  self.g={i:{'free_mib':24214,'query_ok':True}for i in [1,3]};self.owners={1:1015,3:1015}
 def test_two_free(self):self.assertEqual(resource_reasons(self.g,[],self.owners),[])
 def test_foreign_context_even_small(self):self.assertTrue(resource_reasons(self.g,[{'physical_gpu':1,'uid':1001,'used_mib':1}],self.owners))
 def test_own_existing_job_not_preempted(self):self.assertTrue(resource_reasons(self.g,[{'physical_gpu':3,'uid':1015}],self.owners))
 def test_missing_gpu(self):self.g.pop(1);self.assertTrue(resource_reasons(self.g,[],self.owners))
 def test_wrong_gpu_pair(self):self.g[0]=self.g.pop(1);self.assertTrue(resource_reasons(self.g,[],self.owners))
 def test_low_headroom(self):self.g[1]['free_mib']=23022;self.assertTrue(resource_reasons(self.g,[],self.owners))
 def test_exact_limit_rejects(self):self.g[1]['free_mib']=23500;self.assertTrue(resource_reasons(self.g,[],self.owners))
 def test_failed_query(self):self.g[3]['query_ok']=False;self.assertTrue(resource_reasons(self.g,[],self.owners))
 def test_missing_query_flag(self):self.g[3].pop('query_ok');self.assertTrue(resource_reasons(self.g,[],self.owners))
 def test_unknown_free(self):self.g[1]['free_mib']=None;self.assertTrue(resource_reasons(self.g,[],self.owners))
 def test_foreign_lock_owner(self):self.owners[1]=1001;self.assertTrue(resource_reasons(self.g,[],self.owners))
 def test_missing_lock(self):self.owners.pop(3);self.assertTrue(resource_reasons(self.g,[],self.owners))

if __name__=='__main__':unittest.main()
