"""Behavioral regression: a typing check must not erase an earlier factual conflict."""
import json,tempfile,unittest
from pathlib import Path
from defense.core import Controller,Journal,Limits
from test_native_direction_development import view,verdict,parse
from test_scoped_controller_integration import screen

class TypingConflict(unittest.TestCase):
    def run_case(self,text):
        with tempfile.TemporaryDirectory()as td:
            calls=[]
            def judge(system,v,candidate):
                calls.append('focus'if candidate is None else'verify')
                return screen(v)if candidate is None else verdict(v)
            ctl=Controller(judge,Journal(Path(td)/'journal'),'post_only',Limits(probe_current_targets=True),sleeper=lambda _:None)
            candidate=text+' <action>{"type":"type","text":"example"}</action>'
            out=ctl.decide(view(),lambda *_:candidate,parse,None)
            events=[json.loads(x)for x in(Path(td)/'journal/events.jsonl').read_text().splitlines()]
            return out,calls,events
    def test_negative_cue_typing_withheld_despite_usable_focus_read(self):
        out,calls,events=self.run_case('There is no visible focus cue. I will type.')
        self.assertEqual(out['status'],'blocked')
        self.assertEqual(out['reason'],'live_recapture_unavailable')
        self.assertEqual(calls,['focus','verify'])
        self.assertTrue(any(e['kind']=='focus_absence_consistency'and e['data']['reject']for e in events))
        self.assertFalse(any(e['kind']=='accepted'for e in events))
    def test_positive_typing_remains_eligible_under_same_checks(self):
        out,calls,events=self.run_case('An input has a visible focus cue. I will type.')
        self.assertEqual(out['status'],'accepted')
        self.assertEqual(calls,['verify','focus'])

if __name__=='__main__':unittest.main()
