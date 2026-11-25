"""Control guarantees for same-kind/wrong-identity clicks, not model accuracy."""
import copy,json,tempfile,unittest
from pathlib import Path
from test_controller import view,verdict,citation
from test_point_probe import parse,point
from defense.core import *
from defense.prompts import ALIGN

def result(status='supported'):
    return {'claims':[], 'action':{'status':status,'target_kind':'not_applicable',
        'reason':'Candidate requests page 1; the frozen point reading names page 3.' if status!='supported' else 'The named target agrees.',
        'evidence':[{'message_index':0,'span_id':'full'}]},
        'pure_wait':False,'acknowledges_visual_deficit':False}

class AlignmentTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def ctl(self,judge,**limits):
        return Controller(judge,Journal(self.root/'run'),'post_only',
            Limits(probe_current_targets=True,probe_target_alignment=True,**limits),sleeper=lambda _:None)
    def test_comparison_cannot_read_history_gui_task_or_main_verdict(self):
        obs=replace(view(),messages=[{'role':'assistant','content':'old unsupported claim'}],recent_action='old action')
        def judge(system,v,c):
            self.assertTrue(system.startswith(ALIGN));self.assertEqual(v.images,())
            self.assertNotIn('old unsupported',str(v.messages));self.assertNotIn('old action',str(v.messages))
            self.assertEqual(v.recent_action,'');self.assertEqual(v.execution_feedback,'')
            pair=json.loads(v.messages[0]['content'])
            self.assertEqual(pair['independent_point_reading']['visible_text'],'3')
            self.assertEqual(json.loads(c),pair);return result('contradicted')
        c=self.ctl(judge);c.remember(view('old'),'old unsupported claim')
        p=point(obs,'button');p['visible_text']='3';before=copy.deepcopy(p)
        self.assertFalse(c.check_target_alignment(obs,'Click page 1',parse('CLICK'),p)['agrees'])
        self.assertEqual(p,before);self.assertEqual(c.verifier_calls,1)
    def test_same_kind_different_identity_is_not_executed_and_original_survives(self):
        answers=iter(['Click page 1','WAIT']);seen=[]
        def actor(v,correction):seen.append(copy.deepcopy(correction));return next(answers)
        def judge(system,v,c):
            if system.startswith(ALIGN):return result('contradicted')
            if isinstance(c,dict):
                p=point(v,'button');p['visible_text']='3';return p
            r=verdict(v,wait=c=='WAIT');r['claims']=[]
            r['action']['target_kind']='not_applicable' if c=='WAIT' else 'button';return r
        c=self.ctl(judge);out=c.decide(view(),actor,parse,lambda:view('fresh'))
        self.assertEqual(out['candidate'],'WAIT');self.assertEqual(out['recaptures'],1)
        self.assertIn('page 3',seen[-1][0]['reason'])
        events=[json.loads(x)for x in(self.root/'run/events.jsonl').read_text().splitlines()]
        self.assertEqual([e['data']['text']for e in events if e['kind']=='candidate'],['Click page 1','WAIT'])
        self.assertEqual(sum(e['kind']=='action_executed'for e in events),0)
    def test_matching_identity_can_continue(self):
        def judge(system,v,c):
            if system.startswith(ALIGN):return result()
            if isinstance(c,dict):return point(v,'button')
            r=verdict(v);r['claims']=[];r['action']['target_kind']='button';return r
        c=self.ctl(judge);self.assertEqual(c.decide(view(),lambda *_:'Click Search',parse,None)['status'],'accepted')
        self.assertEqual(c.verifier_calls,3)
    def test_uncertain_identity_requires_real_capture(self):
        c=self.ctl(lambda *_:result('uncertain'))
        self.assertTrue(c.check_target_alignment(view(),'Click it',parse('CLICK'),point(view()))['needs_evidence'])
    def test_extra_pass_shares_original_total_budget(self):
        def judge(system,v,c):
            if isinstance(c,dict):return point(v,'input')
            return verdict(v)
        c=self.ctl(judge,max_verifier_calls=2)
        out=c.decide(view(),lambda *_:'CLICK',parse,None)
        self.assertEqual(out['reason'],'alignment_verifier_error:verifier_call_cap')
        self.assertEqual(c.verifier_calls,2)
    def test_comparison_cannot_return_gui_claims(self):
        def judge(*_):
            r=result();r['claims']=[{'id':'c1','kind':'intent','text':'extra','status':'supported',
                'reason':'fixture','dependent_decisions':[],'evidence':[{'source':'candidate','span_id':'full'}]}];return r
        c=self.ctl(judge,max_format_retries=0)
        with self.assertRaisesRegex(ValidationError,'supplied targets only'):
            c.check_target_alignment(view(),'Click Search',parse('CLICK'),point(view()))
    def test_full_comparison_pair_is_a_valid_text_source_not_gui_self_proof(self):
        def judge(system,v,c):
            self.assertIn('independent_point_reading',json.loads(c))
            r=result();r['action']['evidence']=[{'source':'candidate','span_id':'full'}];return r
        c=self.ctl(judge)
        self.assertTrue(c.check_target_alignment(view(),'Click Search',parse('CLICK'),point(view()))['agrees'])

if __name__=='__main__':unittest.main()
