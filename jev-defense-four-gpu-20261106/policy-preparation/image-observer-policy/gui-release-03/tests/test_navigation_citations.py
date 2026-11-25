"""Regression for actual candidate-only back verdict; no semantic accuracy claim."""
import copy,json,tempfile,unittest
from pathlib import Path
from test_controller import view,verdict,citation
from defense.core import Controller,Journal,ValidationError,validate_verdict
from defense.prompts import NATIVE_NAVIGATION

class NavigationCitationTests(unittest.TestCase):
    def proposal(self,name='back'):
        return {'name':name,'parsed':True,'executor_fallback_wait':False,
                'payload':{'type':name,**({'x':500,'y':500}if name=='click'else{})},'coordinate_space':'normalized_1000'}

    def test_candidate_only_back_remains_invalid(self):
        v=verdict(view());v['claims']=[];v['action']['target_kind']='not_applicable'
        v['action']['evidence']=[{'source':'candidate','span_id':'full'}]
        with self.assertRaisesRegex(ValidationError,'Candidate alone'):
            validate_verdict(v,view(),'Go back',self.proposal())

    def test_actual_image_cited_back_is_mechanically_valid(self):
        v=verdict(view());v['claims']=[];v['action']['target_kind']='not_applicable'
        validate_verdict(v,view(),'Go back',self.proposal())

    def test_task_instruction_cannot_be_cited_as_prior_navigation(self):
        from dataclasses import replace
        obs=replace(view(),messages=[{'role':'user','content':'Task: go back. Previous observation request.'},
            {'role':'assistant','content':'Open item. <action>{"type":"click","x":500,"y":500}</action>'}])
        v=verdict(obs);v['claims']=[];v['action']['evidence']=[citation(obs),{'message_index':0,'span_id':'full'}]
        with self.assertRaisesRegex(ValidationError,'actual earlier assistant navigation-capable action'):
            validate_verdict(v,obs,'Go back',self.proposal())
        v['action']['evidence']=[citation(obs),{'message_index':1,'span_id':'full'}]
        validate_verdict(v,obs,'Go back',self.proposal())

    def test_history_action_map_does_not_turn_scroll_into_navigation(self):
        from dataclasses import replace
        from defense.core import navigation_history_records,action_history_indices
        obs=replace(view(),messages=[{'role':'assistant','content':'Scroll. <action>{"type":"scroll","direction":"down"}</action>'},
            {'role':'assistant','content':'Click item. <action>{"type":"click","x":489,"y":236}</action>'}])
        self.assertEqual(action_history_indices(obs),[1])
        self.assertEqual(navigation_history_records(obs),[{'message_index':1,'native_action_attempt':{'type':'click','x':489,'y':236}}])
        v=verdict(obs);v['claims']=[];v['action']['evidence']=[citation(obs),{'message_index':0,'span_id':'full'}]
        with self.assertRaisesRegex(ValidationError,'or scroll'):validate_verdict(v,obs,'Go back',self.proposal())

    def test_navigation_guidance_is_scoped_to_native_navigation(self):
        for name in ['back','tab','click','type','stop']:
            with self.subTest(name=name),tempfile.TemporaryDirectory()as tmp:
                prompts=[]
                def judge(system,obs,candidate):
                    prompts.append(system);v=verdict(obs);v['claims']=[];return v
                c=Controller(judge,Journal(Path(tmp)/'run'),'post_only')
                c.inspect('verify',view(),'Go',self.proposal(name))
                self.assertEqual(NATIVE_NAVIGATION in prompts[0],name in {'back','tab'})

    def test_retry_keeps_inputs_and_does_not_repair_raw_verdict(self):
        obs=view();candidate='Go back';seen=[];bad=verdict(obs);bad['claims']=[]
        bad['action']['evidence']=[{'source':'candidate','span_id':'full'}]
        good=copy.deepcopy(bad);good['action']['evidence']=[citation(obs)]
        with tempfile.TemporaryDirectory()as tmp:
            def judge(system,v,raw):
                seen.append((system,v.data(),raw));return json.dumps(bad if len(seen)==1 else good)
            c=Controller(judge,Journal(Path(tmp)/'run'),'post_only')
            result=c.inspect('verify',obs,candidate,self.proposal())
            self.assertEqual(result['action']['status'],'supported');self.assertEqual(c.verifier_calls,2)
            self.assertEqual(seen[0][1:],seen[1][1:]);self.assertIn('action.evidence was candidate-only',seen[1][0])
            events=[json.loads(x)for x in(Path(tmp)/'run/events.jsonl').read_text().splitlines()]
            raws=[e['data']['response']for e in events if e['kind']=='verifier_raw']
            self.assertEqual(json.loads(raws[0]),bad)
            self.assertEqual(sum(e['kind']=='verifier_format_failure'for e in events),1)

    def test_reference_still_cannot_ground_current_click(self):
        from dataclasses import replace
        from defense.core import VisibleImage
        obs=replace(view(),images=(VisibleImage(view().images[0].raw,'reference'),))
        v=verdict(obs);v['claims']=[]
        with self.assertRaisesRegex(ValidationError,'Current click'):
            validate_verdict(v,obs,'Click',self.proposal('click'))

if __name__=='__main__':unittest.main()
