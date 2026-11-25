"""Regress the observed self-citation failure while retaining strict source fences."""
import copy,json,tempfile,unittest
from pathlib import Path
from test_controller import view,verdict,citation
from defense.core import Controller,Journal,validate_verdict,ValidationError,historical_report_records
from defense.prompts import FACTUAL_SOURCE_ROUTING

class FactualRoutingTests(unittest.TestCase):
    candidate="I cannot confirm absence; I've only viewed part. I will scroll."
    proposal={'name':'scroll','payload':{'type':'scroll','direction':'down'}}

    def bad(self):
        v=verdict(view());v['claims'][0].update(kind='history_report',text="I've only viewed part",evidence=[{'source':'candidate','span_id':'full'}])
        return v

    def test_self_cited_history_still_rejected_even_with_action_image(self):
        with self.assertRaisesRegex(ValidationError,'Candidate cannot prove'):
            validate_verdict(self.bad(),view(),self.candidate,self.proposal)

    def test_self_cited_gui_fact_still_rejected(self):
        v=self.bad();v['claims'][0]['kind']='gui_fact'
        with self.assertRaisesRegex(ValidationError,'Candidate cannot prove'):
            validate_verdict(v,view(),self.candidate,self.proposal)

    def test_diagnostic_preserves_inputs_raws_and_uncertainty(self):
        bad=self.bad();good=copy.deepcopy(bad);good['claims'][0].update(status='insufficient',evidence=[])
        seen=[]
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp)/'run'
            def judge(system,obs,candidate):
                seen.append((system,obs.data(),candidate));return json.dumps(bad if len(seen)==1 else good)
            c=Controller(judge,Journal(root),'post_only');v=c.inspect('verify',view(),self.candidate,self.proposal)
            self.assertEqual(v['claims'][0]['status'],'insufficient');self.assertEqual(c.verifier_calls,2)
            self.assertEqual(seen[0][1:],seen[1][1:]);self.assertIn(FACTUAL_SOURCE_ROUTING,seen[0][0]);self.assertIn('Factual-source diagnostic:',seen[1][0])
            events=[json.loads(l)for l in(root/'events.jsonl').read_text().splitlines()]
            self.assertEqual(json.loads(next(e['data']['response']for e in events if e['kind']=='verifier_raw')),bad)

    def test_repeated_self_citation_still_fails_after_original_retry_budget(self):
        with tempfile.TemporaryDirectory()as tmp:
            c=Controller(lambda *_:self.bad(),Journal(Path(tmp)/'run'),'post_only')
            with self.assertRaisesRegex(ValidationError,'Candidate cannot prove'):
                c.inspect('verify',view(),self.candidate,self.proposal)
            self.assertEqual(c.verifier_calls,2)

    def test_task_or_correction_cannot_prove_coverage(self):
        from dataclasses import replace
        for text in ['Task: inspect page 2. Previous observation request.','TASK-STATE CORRECTION. Page coverage unknown.']:
            obs=replace(view(),messages=[{'role':'user','content':text}]);v=self.bad();v['claims'][0]['evidence']=[{'message_index':0,'span_id':'full'}]
            with self.assertRaisesRegex(ValidationError,'Task or correction instructions'):
                validate_verdict(v,obs,self.candidate,self.proposal)

    def test_explicit_original_index_survives_interleaved_task_requests(self):
        from dataclasses import replace
        obs=replace(view(),messages=[{'role':'user','content':'Task: inspect'},
            {'role':'assistant','content':"I have only viewed part of page 2."},
            {'role':'user','content':'Task: inspect'}])
        self.assertEqual(historical_report_records(obs),[{'message_index':1,'role':'assistant','text':"I have only viewed part of page 2."}])
        v=self.bad();v['claims'][0]['evidence']=[{'message_index':1,'span_id':'full'}]
        validate_verdict(v,obs,self.candidate,self.proposal)

if __name__=='__main__':unittest.main()
