import unittest
from test_controller import view
from defense.core import *

class StatePatchTests(unittest.TestCase):
    def claim(self,text):return {'id':'c1','text':text,'reason':'global comparison unverified','dependent_decisions':['completion']}
    def test_repeated_judge_claim_is_not_injected_into_actor_feedback(self):
        candidate='I reached the book. This is the cheapest item. The task is complete.'
        raw='This is the cheapest item. '+('The task is complete. '*15)
        patch=pending_claim_patch(candidate,self.claim(raw),view())
        a,b=patch['source_span'];self.assertEqual(patch['claim'],candidate[a:b])
        self.assertLessEqual(patch['claim'].count('The task is complete'),1)
        self.assertNotIn(raw,correction_message([patch])['content'])
        self.assertEqual(patch['source_candidate_sha256'],digest(candidate.encode()))
    def test_unlocatable_paraphrase_falls_back_to_original_candidate_not_invented_text(self):
        candidate='Observed a blue field.';patch=pending_claim_patch(candidate,self.claim('unrelated invented claim'),view())
        self.assertEqual(patch['claim'],candidate);self.assertEqual(patch['source_span'],[0,len(candidate)])
    def test_exact_short_claim_and_confirmed_observations_are_preserved(self):
        known=[{'text':'book price is5','source_observation':'o1'}]
        patch=pending_claim_patch('Focused. Type.',self.claim('Focused.'),view(),known)
        self.assertEqual(patch['claim'],'Focused.');self.assertEqual(patch['status'],'pending_confirmation')
        self.assertEqual(patch['confirmed_current_observations'],known)
        self.assertEqual(patch['replacement_state']['truth'],'unknown')
        known[0]['text']='mutated';self.assertNotEqual(patch['confirmed_current_observations'],known)
    def test_checker_explanation_cannot_become_a_new_visual_observation(self):
        raw='The screenshots never showed six of the listings.'
        claim={**self.claim('The result is cheapest.'),'reason':raw,'status':'insufficient'}
        patch=pending_claim_patch('The result is cheapest.',claim,view())
        self.assertNotIn(raw,correction_message([patch])['content'])
        self.assertEqual(patch['raw_verifier_reason_sha256'],digest(raw.encode()))
        self.assertEqual(patch['verifier_assessment'],'insufficient')
        self.assertIn('not a new observation',correction_message([patch])['content'])

if __name__=='__main__':unittest.main()
