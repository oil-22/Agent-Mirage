"""Source isolation and original-budget invariants; no scripted semantic accuracy claim."""
import copy,json,tempfile,unittest
from pathlib import Path
from defense.core import Controller,Journal,Limits,ValidationError
from focus_history_scope import FOCUS_READ,CURRENT_SCOPE,CLAIM_SCOPE
from test_native_direction_development import view,verdict,candidate,parse
from test_scoped_controller_integration import screen

class ScopeIntegration(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def ctl(self,judge):return Controller(judge,Journal(self.root/'journal'),'joint',Limits(probe_observation_readiness=True),sleeper=lambda _:None)
    def test_focus_projection_hides_prior_claims_and_targets(self):
        original=view();before=copy.deepcopy(original.messages)
        def judge(system,v,c):
            self.assertTrue(system.startswith(FOCUS_READ));self.assertIsNone(c)
            self.assertNotIn('complete old history',json.dumps(v.messages));self.assertEqual(v.recent_action,'');self.assertEqual(v.execution_feedback,'')
            self.assertEqual(v.images[0].raw,original.images[0].raw);return screen(v)
        self.assertTrue(self.ctl(judge).check_current_focus(original)['agrees']);self.assertEqual(before,original.messages)
    def test_uncertain_focus_is_not_forced_usable(self):
        c=self.ctl(lambda _,v,__ :screen(v,'unknown'))
        self.assertFalse(c.check_current_focus(view())['agrees']);self.assertEqual(c.verifier_calls,1)
    def test_new_scope_is_instruction_without_hardcoded_picture_facts(self):
        for x in [FOCUS_READ,CURRENT_SCOPE,CLAIM_SCOPE]:
            self.assertNotIn('basketball',x);self.assertNotIn('Keyword',x);self.assertNotIn('copper',x)
    def test_main_verifier_keeps_full_history_and_proposal(self):
        v=view();original=copy.deepcopy(v.messages);text=candidate('I will scroll down.')
        def judge(system,p,c):
            self.assertIn(CLAIM_SCOPE,system);self.assertEqual(p.messages,original);self.assertEqual(c,text);return verdict(p)
        c=self.ctl(judge);self.assertEqual(c.inspect('verify',v,text,parse(text))['action']['status'],'supported');self.assertEqual(c.verifier_calls,1)
    def test_focus_bad_source_is_not_relabelled_or_forgiven(self):
        def judge(_,v,__):
            x=screen(v);x['reason']='Image 9 shows an input focus outline.';return x
        c=self.ctl(judge)
        with self.assertRaises(ValidationError):c.check_current_focus(view())
        self.assertEqual(c.verifier_calls,2)
if __name__=='__main__':unittest.main()
