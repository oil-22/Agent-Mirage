"""Isolation and recovery invariants; scripted results are not visual accuracy tests."""
import copy,json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from test_controller import view,screen,verdict,parse
from defense.core import Controller,Journal,Limits
from defense.prompts import READINESS,SCREEN,VERIFY

class ObservationReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
    def controller(self,judge,arm='joint'):
        return Controller(judge,Journal(self.root/'run'),arm,
                          Limits(probe_observation_readiness=True),sleeper=lambda _:None)
    def rich(self):
        return replace(view(),messages=[{'role':'system','content':'original actor instructions'},
            {'role':'assistant','content':'OLD_UNVERIFIED_TARGET: page 1 must already be open'},
            {'role':'user','content':[{'type':'text','text':'Task: find bike\nKeep exact task text.'},
                                      {'type':'text','text':'Current browser screenshot follows.'}]}],
            recent_action='{"type":"scroll","direction":"down"}',execution_feedback='attempt returned')
    def test_auxiliary_read_excludes_old_assertions_preserves_pixels_and_task(self):
        original=self.rich();saved=copy.deepcopy(original.messages)
        def judge(system,v,candidate):
            self.assertEqual(system,READINESS);self.assertIsNone(candidate)
            self.assertNotIn('OLD_UNVERIFIED_TARGET',json.dumps(v.messages))
            self.assertEqual(v.images[0].raw,original.images[0].raw)
            self.assertEqual(v.observation_id,original.observation_id)
            payload=json.loads(v.messages[0]['content'])
            self.assertIn('Task: find bike\nKeep exact task text.',payload['actual_current_user_text'])
            self.assertEqual(v.recent_action,original.recent_action)
            return screen(v)
        self.controller(judge).inspect('screen',original)
        self.assertEqual(original.messages,saved)
    def test_actor_and_main_keep_complete_original_context(self):
        original=self.rich();seen=[]
        def judge(system,v,candidate):
            if system==READINESS:return screen(v)
            self.assertTrue(system.startswith(VERIFY));seen.append('main')
            self.assertEqual(v.messages,original.messages)
            return verdict(v)
        def actor(v,c):
            seen.append('actor');self.assertEqual(v.messages,original.messages);return 'CLICK'
        result=self.controller(judge).decide(original,actor,parse,None)
        self.assertEqual(result['status'],'accepted');self.assertEqual(seen,['actor','main'])
    def test_focus_reader_does_not_inherit_readiness_permission(self):
        original=self.rich()
        def judge(system,v,candidate):
            self.assertTrue(system.startswith(SCREEN));self.assertIn('usable ONLY if',system)
            self.assertNotIn('OLD_UNVERIFIED_TARGET',json.dumps(v.messages))
            return screen(v,'limited')
        result=self.controller(judge).check_current_focus(original)
        self.assertFalse(result['agrees'])
    def test_unknown_scene_keeps_bounded_recapture_and_never_calls_actor(self):
        count=[]
        def capture():
            count.append(1);return replace(self.rich(),observation_id='fresh'+str(len(count)))
        c=self.controller(lambda _,v,candidate:screen(v,'unknown'),'pre_only')
        result=c.decide(self.rich(),lambda *_:self.fail('unusable image reached actor'),parse,capture)
        self.assertEqual(result['reason'],'observation_not_confirmed')
        self.assertEqual(len(count),2);self.assertEqual(c.actor_calls,0)
