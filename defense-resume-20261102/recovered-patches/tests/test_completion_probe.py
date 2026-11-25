"""Information isolation, budget and recovery guarantees; not vision accuracy."""
import copy,json,tempfile,unittest
from pathlib import Path
from test_controller import view,screen,verdict
from defense.core import *
from defense.prompts import COMPLETION,COMPLETION_RELATION

def relation(status='contradicted'):
    return {'claims':[],'action':{'status':status,'target_kind':'not_applicable',
        'reason':'scope fixture','evidence':[{'source':'candidate','span_id':'full'}]},
        'acknowledges_visual_deficit':False,'pure_wait':False}

def parse(text):
    return {'name':'wait'if text=='WAIT'else'stop','payload':{'type':'wait'if text=='WAIT'else'stop'},
        'parsed':True,'executor_fallback_wait':False}

class CompletionProbeTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def ctl(self,judge,arm='post_only',**limits):
        return Controller(judge,Journal(self.root/'run'),arm,Limits(probe_completion=True,**limits),sleeper=lambda _:None)
    def test_blind_input_keeps_every_native_image_and_no_narrative(self):
        obs=replace(view('now'),messages=[{'role':'assistant','content':'OLD_NARRATIVE'},*view().messages],
                    recent_action='OLD_ACTION',execution_feedback='OLD_FEEDBACK')
        frozen=copy.deepcopy(obs.messages)
        def judge(system,v,candidate):
            self.assertTrue(system.startswith(COMPLETION));self.assertIsNone(candidate)
            for forbidden in ['OLD_NARRATIVE','OLD_ACTION','OLD_FEEDBACK','OLD_CANDIDATE','NEW_CANDIDATE']:
                self.assertNotIn(forbidden,str(v.messages))
            self.assertEqual(v.recent_action,'');self.assertEqual(v.execution_feedback,'')
            self.assertEqual(len(v.images),6)
            self.assertEqual([im.raw for im in v.images],[obs.images[0].raw]+[view(color=color).images[0].raw for color in ['red','blue','green','yellow','purple']])
            return screen(v)
        c=self.ctl(judge)
        for i,color in enumerate(['red','blue','green','yellow','purple']):c.remember(view('past'+str(i),color),'OLD_CANDIDATE')
        out=c.check_completion(obs,'NEW_CANDIDATE')
        self.assertTrue(out['agrees']);self.assertIsNone(out['task_recovered']);self.assertEqual(obs.messages,frozen)
    def test_limited_read_frozen_before_text_only_scope_comparison(self):
        frozen=[]
        def judge(system,v,candidate):
            if system.startswith(COMPLETION):
                value=screen(v,'limited');value['reason']='specific unestablished prerequisite';frozen.append(copy.deepcopy(value));return value
            self.assertTrue(system.startswith(COMPLETION_RELATION));self.assertEqual(v.images,())
            self.assertEqual(v.recent_action,'');self.assertEqual(v.execution_feedback,'')
            pair=json.loads(candidate);self.assertEqual(pair['candidate'],'Task complete')
            self.assertEqual(pair['independent_image_only_completion'],frozen[0])
            self.assertNotIn('OLD_NARRATIVE',str(v.messages));return relation()
        c=self.ctl(judge);obs=replace(view(),messages=[*view().messages,{'role':'assistant','content':'OLD_NARRATIVE'}])
        out=c.check_completion(obs,'Task complete');self.assertFalse(out['agrees']);self.assertEqual(c.verifier_calls,2)
        self.assertNotIn('specific unestablished prerequisite',out['reason'])
    def test_veto_recaptures_and_preserves_first_candidate(self):
        answers=iter(['Task complete','WAIT']);actor_history=[]
        def judge(system,v,candidate):
            if system.startswith(COMPLETION):return screen(v,'limited')
            if system.startswith(COMPLETION_RELATION):return relation()
            r=verdict(v,wait=candidate=='WAIT');r['claims']=[];r['action']['target_kind']='not_applicable';return r
        def actor(v,patch):actor_history.append(copy.deepcopy(v.messages));return next(answers)
        obs=replace(view(),messages=[{'role':'assistant','content':'ORIGINAL_HISTORY'},*view().messages])
        c=self.ctl(judge);out=c.decide(obs,actor,parse,lambda:view('fresh'))
        self.assertEqual(out['candidate'],'WAIT');self.assertEqual(out['recaptures'],1)
        self.assertEqual(actor_history[0],obs.messages)
        events=[json.loads(x)for x in(self.root/'run/events.jsonl').read_text().splitlines()]
        self.assertEqual([e['data']['text']for e in events if e['kind']=='candidate'],['Task complete','WAIT'])
        self.assertFalse(any(e['kind']=='action_executed'for e in events))
    def test_qualified_report_compatibility_is_not_proven_task_recovery(self):
        def judge(system,v,candidate):
            return screen(v,'limited')if system.startswith(COMPLETION)else relation('supported')
        out=self.ctl(judge).check_completion(view(),'Cannot confirm all prerequisites')
        self.assertTrue(out['agrees']);self.assertEqual(out['image_only_assessment']['status'],'limited')
        self.assertIsNone(out['task_recovered']);self.assertIsNone(out['semantic_mirage'])
    def test_probe_shares_original_total_budget(self):
        def judge(system,v,candidate):
            r=verdict(v);r['claims']=[];r['action']['target_kind']='not_applicable';return r
        c=self.ctl(judge,max_verifier_calls=1)
        out=c.decide(view(),lambda *_:'Task complete',parse,None)
        self.assertEqual(out['reason'],'completion_verifier_error:verifier_call_cap');self.assertEqual(c.verifier_calls,1)
    def test_native_baseline_does_not_call_probe(self):
        c=self.ctl(lambda *_:self.fail('Baseline must not call verifier'),'baseline')
        self.assertEqual(c.decide(view(),lambda *_:'Task complete',parse,None)['status'],'accepted')
        self.assertEqual(c.verifier_calls,0)
    def test_completion_scope_acknowledgment_preserved_but_not_used_to_allow_action(self):
        def judge(*_):
            r=relation('contradicted');r['acknowledges_visual_deficit']=True;return r
        c=self.ctl(judge)
        result=c.inspect('completion_relation',replace(view(),images=()),'comparison pair')
        self.assertTrue(result['acknowledges_visual_deficit']);self.assertEqual(result['action']['status'],'contradicted')
    def test_completion_scope_still_cannot_return_gui_claims(self):
        def judge(*_):
            r=relation('supported');r['acknowledges_visual_deficit']=True
            r['claims']=[{'id':'c1','kind':'gui_fact','text':'invented','status':'supported','evidence':[{'source':'candidate','span_id':'full'}],'reason':'fixture','dependent_decisions':[]}];return r
        c=self.ctl(judge,max_format_retries=0)
        with self.assertRaisesRegex(ValidationError,'without GUI claims'):
            c.inspect('completion_relation',replace(view(),images=()),'comparison pair')

if __name__=='__main__':unittest.main()
