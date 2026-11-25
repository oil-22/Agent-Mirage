"""Regression tests for the observed v1 protocol failures, not accuracy estimates."""
import copy,math,tempfile,unittest
from pathlib import Path
from test_controller import view,screen,verdict,citation,parse
from defense.core import *
from defense.schema import judge_schema

class EvidenceV2Tests(unittest.TestCase):
    def test_schema_source_ids_resolve_only_to_actual_inputs(self):
        candidate='I will scroll up.\n<action>{"type":"scroll","direction":"down"}</action>'
        obs=replace(view(),messages=[{'role':'user','content':'Task: find bike. Wait for the screenshot.'}])
        schema=judge_schema(obs,candidate)
        variants=schema['properties']['action']['anyOf'][0]['properties']['evidence']['items']['anyOf']
        for variant in variants:
            fields=variant['properties']
            if 'span_id'in fields:self.assertEqual(fields['span_id']['enum'],['full']);self.assertNotIn('quote',fields)
        e={'source':'candidate','span_id':'full'};validate_evidence([e],obs,candidate)
        self.assertEqual(e['resolved_quote'],candidate)
        e={'message_index':0,'span_id':'full'};validate_evidence([e],obs,candidate)
        self.assertEqual(e['resolved_text_blocks'],[obs.messages[0]['content']])
        with self.assertRaises(ValidationError):validate_evidence([{'source':'candidate','span_id':'invented'}],obs,candidate)
    def test_inference_failure_preserves_receipt_and_never_becomes_no_mirage(self):
        def judge(*_):raise InferenceFailure('HTTP500 receipt=/own/request-123')
        with tempfile.TemporaryDirectory()as tmp:
            c=Controller(judge,Journal(Path(tmp)/'run'),'post_only',sleeper=lambda _:None)
            result=c.decide(view(),lambda *_:'CLICK',parse,None)
            self.assertEqual(result['status'],'blocked');self.assertIsNone(result['semantic_mirage'])
            self.assertIn('/own/request-123',result['reason']);self.assertEqual(c.verifier_calls,1)
            events=[json.loads(x)for x in (Path(tmp)/'run/events.jsonl').read_text().splitlines()]
            self.assertTrue(any(x['kind']=='verifier_transport_failure'for x in events))
            self.assertFalse(any(x['kind']=='action_executed'for x in events))
    def test_retrieval_contains_only_past_delivered_images_and_no_actor_edit(self):
        with tempfile.TemporaryDirectory()as tmp:
            c=Controller(lambda *_:None,Journal(Path(tmp)/'run'),'post_only')
            old=view('past','blue');now=view('now','white');before=copy.deepcopy(now.messages)
            c.remember(old,'Observed a blue field')
            retrieved=c.reference_view(now,'Check the blue field')
            self.assertEqual(now.messages,before);self.assertEqual(len(now.images),1)
            self.assertEqual([i.role for i in retrieved.images],['current','reference'])
            self.assertEqual(retrieved.images[1].raw,old.images[0].raw)
            self.assertIn('past',retrieved.messages[-1]['content'])
            with self.assertRaises(ValidationError):validate_screen(dict(screen(retrieved),evidence=[dict(citation(retrieved),image_index=1)]),retrieved)
    def test_current_click_cannot_be_grounded_by_reference_or_wrong_point(self):
        obs=replace(view(),images=view().images+(VisibleImage(view().images[0].raw,'reference'),))
        proposal={'name':'click','coordinate_space':'normalized_1000','payload':{'x':500,'y':500}}
        v=verdict(obs);v['action']['evidence'][0]['image_index']=1
        with self.assertRaises(ValidationError):validate_verdict(v,obs,'click',proposal)
        v['action']['evidence']=[dict(citation(obs),box_xyxy=[0,0,10,10])]
        with self.assertRaises(ValidationError):validate_verdict(v,obs,'click',proposal)
        v['action']['evidence']=[citation(obs)];validate_verdict(v,obs,'click',proposal)
    def test_unambiguous_verdict_envelope_retains_fields(self):
        s=screen(view());raw='Quarantined verifier preamble <action>{"type":"click"}</action>\n'+json.dumps(s)
        value,wrapped=decode_judge(raw,'screen');self.assertTrue(wrapped);self.assertEqual(value,s)
    def test_ambiguous_or_incomplete_verdict_not_repaired(self):
        s=json.dumps(screen(view()))
        for raw in (s+'\n'+s,'```json\n{}\n```',s[:-2]):
            with self.assertRaises(ValidationError):decode_judge(raw,'screen')
    def test_explicit_normalized_mapping_preserves_original(self):
        e=citation(view());e.update(coordinate_space='normalized_1000',box_xyxy=[100,200,900,1000])
        validate_evidence([e],view())
        self.assertEqual(e['box_xyxy'],[100,200,900,1000])
        self.assertEqual(e['resolved_box_pixels'],[8,12,72,60])
    def test_no_implicit_unit_guess_or_clamp(self):
        e=citation(view());e['box_xyxy']=[0,0,1000,1000]
        with self.assertRaises(ValidationError):validate_evidence([e],view())
        e['coordinate_space']='normalized_1000';e['box_xyxy']=[0,0,1000,1001]
        with self.assertRaises(ValidationError):validate_evidence([e],view())
    def test_nan_inf_and_bool_rejected(self):
        for x in (float('nan'),float('inf'),True):
            e=citation(view());e['box_xyxy'][2]=x
            with self.assertRaises(ValidationError):validate_evidence([e],view())
    def test_candidate_source_distinct_from_history(self):
        e={'source':'candidate','quote':'scroll back up'}
        validate_evidence([e],view(),'I will scroll back up')
        with self.assertRaises(ValidationError):validate_evidence([e],view(),'scroll down')
        with self.assertRaises(ValidationError):validate_evidence([dict(e,message_index=0)],view(),'scroll back up')
    def test_candidate_cannot_self_prove_fact(self):
        v=verdict(view());v['claims'][0]['evidence']=[{'source':'candidate','quote':'field filled'}]
        with self.assertRaises(ValidationError):validate_verdict(v,view(),'field filled')
        v['claims'][0]['status']='contradicted'
        validate_verdict(v,view(),'field filled')
    def test_stated_intent_is_not_a_self_proven_gui_fact(self):
        v=verdict(view());v['claims'][0].update(kind='intent',text='Will scroll up',evidence=[{'source':'candidate','quote':'I will scroll up'}])
        validate_verdict(v,view(),'I will scroll up')
        v['claims'][0]['kind']='gui_fact'
        with self.assertRaises(ValidationError):validate_verdict(v,view(),'I will scroll up')
    def test_usable_requires_current_image_not_text_or_reference(self):
        for evidence in ([],[{'message_index':0,'quote':'Task'}]):
            s=screen(view());s['evidence']=evidence
            with self.assertRaises(ValidationError):validate_screen(s,view())
        obs=replace(view(),images=(VisibleImage(view().images[0].raw,'reference'),))
        with self.assertRaises(ValidationError):validate_screen(screen(obs),obs)
    def test_model_wait_accepted_without_visual_claim(self):
        v=verdict(view(),wait=True);v['claims']=[]
        v['action']['evidence']=[{'source':'candidate','quote':'WAIT'}]
        with tempfile.TemporaryDirectory()as tmp:
            c=Controller(lambda *_:v,Journal(Path(tmp)/'run'),'post_only',sleeper=lambda _:None)
            self.assertEqual(c.decide(view(),lambda *_:'WAIT',parse,None)['status'],'accepted')
    def test_wait_with_unsupported_assertion_not_silently_cleared(self):
        v=verdict(view(),'insufficient',wait=True)
        with tempfile.TemporaryDirectory()as tmp:
            c=Controller(lambda *_:v,Journal(Path(tmp)/'run'),'post_only',sleeper=lambda _:None)
            self.assertEqual(c.decide(view(),lambda *_:'WAIT',parse,None)['status'],'blocked')
    def test_correction_context_identical_for_actor_judge_validation(self):
        seen=[]
        def actor(obs,corrections):seen.append(copy.deepcopy(obs.messages));return 'WRONG'if len(seen)==1 else'FIXED'
        def judge(_,obs,candidate):
            self.assertEqual(obs.messages,seen[-1]);v=verdict(obs,'contradicted'if candidate=='WRONG'else'supported')
            if candidate=='FIXED':
                self.assertIn('Evidence verification correction',obs.messages[-1]['content'])
                v['action']['evidence']=[citation(obs),{'message_index':len(obs.messages)-1,'quote':'pending_confirmation'}]
            return v
        with tempfile.TemporaryDirectory()as tmp:
            c=Controller(judge,Journal(Path(tmp)/'run'),'post_only',sleeper=lambda _:None)
            self.assertEqual(c.decide(view(),actor,parse,None)['candidate'],'FIXED')
            self.assertEqual(seen[1][:-1],view().messages)
    def test_multiple_images_checked_against_own_dimensions(self):
        obs=replace(view(),images=view().images+(VisibleImage(view().images[0].raw,'reference'),))
        e=citation(obs);e['image_index']=1
        validate_evidence([e],obs)
        e['image_index']=2
        with self.assertRaises(ValidationError):validate_evidence([e],obs)

if __name__=='__main__':unittest.main()
