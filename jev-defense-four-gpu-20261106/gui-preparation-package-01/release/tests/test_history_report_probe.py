"""Evidence isolation and fail-closed control guarantees, not semantic accuracy."""
import copy,json,tempfile,unittest
from pathlib import Path
from test_controller import view,verdict
from defense.core import *
from defense.prompts import HISTORY_REPORT
from defense.prompts import COMPLETION,COMPLETION_RELATION
from test_controller import screen

def relation(status='supported',evidence=None):
    return {'claims':[],'action':{'status':status,'target_kind':'not_applicable','reason':'bounded report fixture',
            'evidence':evidence if evidence is not None else[{'message_index':0,'span_id':'full'}]},
            'pure_wait':False,'acknowledges_visual_deficit':True}

def history_relation(status='supported',evidence=None):
    return {'status':status,'reason':'bounded record relation','evidence':evidence if evidence is not None else[{'message_index':0,'span_id':'full'}]}

class HistoryReportTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def obs(self):
        return replace(view(),messages=[{'role':'assistant','content':'Earlier I reported page 2 and candidate X.'},*view().messages],recent_action='OLD_ACTION',execution_feedback='OLD_FEEDBACK')
    def ctl(self,judge,**limits):return Controller(judge,Journal(self.root/'run'),'post_only',Limits(probe_history_reports=True,**limits))
    def main(self,obs,kind='history_report'):
        result=verdict(obs);result['claims']=[{'id':'h1','kind':kind,'text':'I reported candidate X','status':'insufficient',
            'evidence':[{'source':'candidate','span_id':'full'}],'reason':'main lacks confirmation','dependent_decisions':['completion']}]
        return result
    def test_only_text_is_projected_indices_and_full_original_text_remain(self):
        obs=self.obs();obs=replace(obs,messages=obs.messages+[{'role':'user','content':[{'type':'text','text':'ALL_ORIGINAL_TEXT'},{'type':'image_url','image_url':{'url':'data:image/png;base64,AA=='}}]}])
        original=copy.deepcopy(obs.messages)
        def judge(system,v,candidate):
            self.assertTrue(system.startswith(HISTORY_REPORT));self.assertEqual(v.images,())
            self.assertEqual(v.recent_action,'');self.assertEqual(v.execution_feedback,'')
            self.assertEqual(len(v.messages),len(original));self.assertEqual(v.messages[0],original[0])
            self.assertIn('ALL_ORIGINAL_TEXT',str(v.messages));self.assertNotIn('image_url',str(v.messages))
            self.assertNotIn('main lacks confirmation',str(v.messages)+candidate)
            return history_relation()
        c=self.ctl(judge);result=c.resolve_history_reports(obs,'Limited report',self.main(obs),{})
        self.assertEqual(result['claims'][0]['status'],'supported');self.assertEqual(obs.messages,original)
    def test_candidate_only_cannot_support_past_report(self):
        obs=self.obs();c=self.ctl(lambda *_:history_relation(evidence=[{'source':'candidate','span_id':'full'}]),max_format_retries=0)
        with self.assertRaisesRegex(ValidationError,'earlier actor-message'):c.resolve_history_reports(obs,'report',self.main(obs),{})
    def test_task_and_correction_only_cannot_support_past_actor_report(self):
        obs=self.obs();c=self.ctl(lambda *_:history_relation(evidence=[{'message_index':1,'span_id':'full'}]),max_format_retries=0)
        with self.assertRaisesRegex(ValidationError,'earlier actor-message'):c.resolve_history_reports(obs,'report',self.main(obs),{})
    def test_gui_fact_never_promoted_by_history_reader(self):
        obs=self.obs();original=self.main(obs,'gui_fact');c=self.ctl(lambda *_:self.fail('GUI claim sent to text-only reader'))
        result=c.resolve_history_reports(obs,'field focused',original,{})
        self.assertEqual(result,original);self.assertEqual(c.verifier_calls,0)
    def test_text_reader_cannot_return_gui_claims(self):
        def judge(*_):
            r=history_relation();r['claims']=[{'id':'g','kind':'gui_fact'}];return r
        obs=self.obs();c=self.ctl(judge,max_format_retries=0)
        with self.assertRaisesRegex(ValidationError,'without GUI claims'):c.resolve_history_reports(obs,'report',self.main(obs),{})
    def test_unresolved_comparison_remains_bad_and_main_is_not_mutated(self):
        obs=self.obs();original=self.main(obs);before=copy.deepcopy(original)
        c=self.ctl(lambda *_:history_relation('insufficient',[{'source':'candidate','span_id':'full'}]))
        result=c.resolve_history_reports(obs,'No alternatives exist',original,{})
        self.assertEqual(result['claims'][0]['status'],'insufficient');self.assertEqual(original,before)
    def test_shares_original_verifier_budget(self):
        obs=self.obs();c=self.ctl(lambda *_:history_relation(),max_verifier_calls=0)
        with self.assertRaises(BudgetExhausted):c.resolve_history_reports(obs,'report',self.main(obs),{})
    def test_comparative_history_cannot_be_upgraded_by_prior_actor_prose(self):
        obs=self.obs();c=self.ctl(lambda *_:self.fail('Comparison sent to text-only override'))
        for text in ['This was the lowest-priced item I encountered','I saw no cheaper match','The minimum price was five dollars','这是我遇到的最低价']:
            main=self.main(obs);main['claims'][0]['text']=text
            self.assertEqual(c.resolve_history_reports(obs,text,main,{}),main)
        self.assertEqual(c.verifier_calls,0)
    def test_reference_indices_of_already_validated_main_are_not_reinterpreted(self):
        obs=self.obs();original=self.main(obs);original['action']['evidence'][0]['image_index']=5
        c=self.ctl(lambda *_:history_relation());result=c.resolve_history_reports(obs,'report',original,{})
        self.assertEqual(result['action'],original['action']);self.assertEqual(result['claims'][0]['status'],'supported')
    def test_history_support_does_not_bypass_independent_completion_veto(self):
        obs=self.obs()
        def judge(system,v,candidate):
            if system.startswith(HISTORY_REPORT):return history_relation()
            if system.startswith(COMPLETION_RELATION):return relation('contradicted',[{'source':'candidate','span_id':'full'}])
            if system.startswith(COMPLETION):return screen(v,'limited')
            result=self.main(v);result['action']['target_kind']='not_applicable';return result
        c=self.ctl(judge,probe_completion=True,max_regenerations=0)
        parse=lambda _:{'name':'stop','payload':{'type':'stop'},'parsed':True,'executor_fallback_wait':False}
        result=c.decide(obs,lambda *_:'Unsupported completion',parse,None)
        self.assertEqual(result['status'],'blocked');self.assertEqual(result['reason'],'regeneration_cap')
        events=[json.loads(line)for line in(self.root/'run/events.jsonl').read_text().splitlines()]
        self.assertTrue(any(e['kind']=='completion_crosscheck'and not e['data']['agrees']for e in events))
        self.assertFalse(any(e['kind']=='decision_accepted'for e in events))
    def test_resolving_history_does_not_clear_an_independent_gui_contradiction(self):
        obs=self.obs()
        def judge(system,v,candidate):
            if system.startswith(HISTORY_REPORT):return history_relation()
            result=self.main(v);gui=copy.deepcopy(result['claims'][0]);gui.update(id='gui',kind='gui_fact',status='contradicted',text='Wrong current page')
            gui['evidence']=[{'observation_id':v.observation_id,'image_index':0,'coordinate_space':'pixels','box_xyxy':[0,0,80,60],'description':'actual current image'}]
            result['claims'].append(gui);return result
        c=self.ctl(judge,max_regenerations=0)
        parse=lambda _:{'name':'click','parsed':True,'executor_fallback_wait':False}
        result=c.decide(obs,lambda *_:'Wrong current page',parse,None)
        self.assertEqual(result['status'],'blocked');self.assertEqual(result['reason'],'regeneration_cap')

if __name__=='__main__':unittest.main()
