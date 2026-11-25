"""Containment failures stay rejected and consume only original recovery budgets."""
import json,tempfile,unittest
from pathlib import Path
from test_controller import view,verdict,citation
from test_point_probe import parse
from defense.core import *

class PointRecoveryTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.log=Journal(Path(self.tmp.name)/'run')
    def tearDown(self):self.tmp.cleanup()
    def events(self):return[json.loads(x)for x in(self.log.root/'events.jsonl').read_text().splitlines()]
    def judge(self,system,v,candidate):
        if isinstance(candidate,dict):
            e=citation(v);e.update(coordinate_space='pixels',box_xyxy=[0,0,10,10])
            return {'kind':'button','visible_text':'uncertified fixture','reason':'wrong region fixture','evidence':[e]}
        r=verdict(v,wait=candidate=='WAIT');r['claims']=[];return r
    def ctl(self,judge=None,**limits):return Controller(judge or self.judge,self.log,'post_only',Limits(probe_current_targets=True,**limits),sleeper=lambda _:None)
    def test_rejected_reading_can_only_redecide_after_fresh_evidence(self):
        calls=[];answers=iter(['CLICK','WAIT']);captures=[]
        def actor(v,cs):calls.append(cs);return next(answers)
        def fresh():captures.append(1);return view('fresh')
        c=self.ctl();r=c.decide(view(),actor,parse,fresh)
        self.assertEqual(r['candidate'],'WAIT');self.assertEqual((r['recaptures'],r['regenerations']),(1,1))
        self.assertEqual(c.verifier_calls,4);self.assertEqual(len(captures),1)
        es=self.events();self.assertEqual(sum(e['kind']=='verifier_format_failure'for e in es),2)
        event=next(e['data']for e in es if e['kind']=='point_evidence_unavailable')
        self.assertTrue(event['invalid_point_reading_not_accepted']);self.assertFalse(event['gui_fact_or_target_inferred'])
        self.assertEqual(event['candidate_sha256'],digest(b'CLICK'))
        self.assertFalse(any(e['kind']=='action_executed'for e in es))
        self.assertNotIn('uncertified fixture',str(calls[-1]))
    def test_repeated_failure_stops_at_original_regeneration_cap(self):
        c=self.ctl();i=iter(['new1','new2']);r=c.decide(view(),lambda *_:'CLICK',parse,lambda:view(next(i)))
        self.assertEqual(r['reason'],'regeneration_cap');self.assertEqual(c.actor_calls,3)
        self.assertEqual((r['recaptures'],r['regenerations']),(2,2));self.assertEqual(c.verifier_calls,9)
        self.assertFalse(any(e['kind']=='decision_accepted'for e in self.events()))
    def test_absent_live_capture_never_accepts_bad_point(self):
        r=self.ctl().decide(view(),lambda *_:'CLICK',parse,None)
        self.assertEqual(r['reason'],'live_recapture_unavailable')
        self.assertIsNone(r['semantic_mirage'])
    def test_transport_failure_still_stops_without_using_recovery(self):
        def judge(s,v,c):
            if isinstance(c,dict):raise InferenceFailure('transport fixture')
            return self.judge(s,v,c)
        r=self.ctl(judge).decide(view(),lambda *_:'CLICK',parse,lambda:self.fail('Transport is not containment'))
        self.assertIn('point_verifier_error:Verifier transport failure',r['reason'])

if __name__=='__main__':unittest.main()
