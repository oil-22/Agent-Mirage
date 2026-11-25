import copy
import hashlib
import unittest
from native_direction_feedback_origin import attribute_direction_feedback

class Origins(unittest.TestCase):
    def setUp(self):
        self.patch={'reason':'explicit direction conflict','verifier_assessment':'supported','rejected_native_proposal':{'payload':{'type':'scroll','direction':'down'}}}
        self.original={'reason':'original judge reasoning','status':'supported'}
        self.guard={'reject':True,'reason':self.patch['reason'],'candidate_sha256':'a'*64}
    def test_separate_sources_and_hashes(self):
        p=attribute_direction_feedback(self.patch,self.original,self.guard)
        self.assertEqual(p['feedback_reason_source'],'native_direction_consistency')
        self.assertEqual(p['raw_verifier_reason_sha256'],hashlib.sha256(self.original['reason'].encode()).hexdigest())
        self.assertEqual(p['feedback_reason_sha256'],hashlib.sha256(self.patch['reason'].encode()).hexdigest())
        self.assertEqual(p['original_verifier_assessment'],'supported')
    def test_inputs_and_native_action_unchanged(self):
        old=copy.deepcopy([self.patch,self.original,self.guard]);p=attribute_direction_feedback(self.patch,self.original,self.guard)
        self.assertEqual(old,[self.patch,self.original,self.guard]);self.assertEqual(p['rejected_native_proposal'],self.patch['rejected_native_proposal'])
    def test_mismatched_feedback_not_attributed(self):
        self.patch['reason']='different'
        with self.assertRaises(AssertionError):attribute_direction_feedback(self.patch,self.original,self.guard)
    def test_nonrejected_guard_not_attributed(self):
        self.guard['reject']=False
        with self.assertRaises(AssertionError):attribute_direction_feedback(self.patch,self.original,self.guard)

if __name__=='__main__':unittest.main()
