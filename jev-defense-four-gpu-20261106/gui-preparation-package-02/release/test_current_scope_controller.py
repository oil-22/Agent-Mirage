import json,tempfile,unittest
from pathlib import Path
from defense.core import Controller,Journal,Limits,ValidationError
from test_native_direction_development import view,verdict,candidate,parse
from test_scoped_controller_integration import screen
from current_only_history_scope import RETRY_SCOPE

class CurrentScopeController(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def ctl(self,judge):return Controller(judge,Journal(self.root/'journal'),'joint',Limits(probe_observation_readiness=True),sleeper=lambda _:None)
    def test_raw_bad_history_retained_then_existing_retry(self):
        seen=[]
        def judge(system,v,c):
            x=screen(v);seen.append(system)
            if len(seen)==1:x['limitations']=['Search has not been executed.']
            else:self.assertIn(RETRY_SCOPE,system)
            return x
        c=self.ctl(judge);self.assertEqual(c.inspect('screen',view())['status'],'usable');self.assertEqual(c.verifier_calls,2)
        events=[json.loads(l)for l in(self.root/'journal/events.jsonl').read_text().splitlines()]
        self.assertEqual(sum(e['kind']=='verifier_format_failure'for e in events),1)
        self.assertTrue(any('Search has not been executed.'in str(e['data'])for e in events if e['kind']=='verifier_raw'))
    def test_persistent_history_stops_at_one_format_retry(self):
        def judge(_,v,c):x=screen(v);x['reason']='The query has been submitted.';return x
        c=self.ctl(judge)
        with self.assertRaises(ValidationError):c.inspect('screen',view())
        self.assertEqual(c.verifier_calls,2)
    def test_candidate_full_history_is_not_under_current_only_guard(self):
        def judge(_,v,c):x=verdict(v);x['action']['reason']='The search has been performed.';return x
        c=self.ctl(judge);s=candidate('I will scroll down.');self.assertEqual(c.inspect('verify',view(),s,parse(s))['action']['status'],'supported');self.assertEqual(c.verifier_calls,1)
    def test_uncertain_source_does_not_spend_retry(self):
        def judge(_,v,c):x=screen(v);x['limitations']=['Cannot determine whether the search has been performed.'];return x
        c=self.ctl(judge);c.inspect('screen',view());self.assertEqual(c.verifier_calls,1)
    def test_focus_still_unknown_when_no_cue(self):
        c=self.ctl(lambda _,v,c:screen(v,'unknown'));self.assertFalse(c.check_current_focus(view())['agrees']);self.assertEqual(c.verifier_calls,1)
if __name__=='__main__':unittest.main()
