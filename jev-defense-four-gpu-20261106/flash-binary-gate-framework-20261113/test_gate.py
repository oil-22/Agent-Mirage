import base64,copy,io,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from gate_core import Decision,Frame,GateController,ImageGate,Journal,NativeHistoryActor,digest
from wire_contract import decode_request,native_request,REVISION

CONTRACT='a'*64
def png(color):
    b=io.BytesIO();Image.new('RGB',(64,48),color).save(b,format='PNG');return b.getvalue()
BAD=png('white');GOOD=png('navy')
class Fake:
    def __init__(self,answers):self.answers=iter(answers);self.calls=[]
    def decide(self,image):
        self.calls.append(image);return Decision(next(self.answers),digest(image),f'call{len(self.calls)}',REVISION,CONTRACT)
class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.journal=Journal(Path(self.temp.name)/'evidence')
    def tearDown(self):self.temp.cleanup()
    def gate(self,checker):return ImageGate(checker,revision=REVISION,contract_sha256=CONTRACT,journal=self.journal,recapture_seconds=0)
    def test_no_no_yes_forwards_only_yes_bytes_and_never_checker_context(self):
        fake=Fake(['NO','NO','YES']);gate=self.gate(fake);frames=iter([Frame.captured(BAD),Frame.captured(GOOD)])
        calls=[];executions=[]
        c=GateController(gate)
        result=c.step(Frame.captured(BAD),lambda:next(frames),lambda f:calls.append(f.png)or'{"type":"click","x":500,"y":500}',json.loads,lambda p:executions.append(p)or{'fixture':True},cancelled=lambda:False)
        self.assertEqual(result['status'],'dispatched');self.assertEqual(fake.calls,[BAD,BAD,GOOD]);self.assertEqual(calls,[GOOD]);self.assertEqual(result['gate']['recaptures'],2);self.assertEqual(len(executions),1)
    def test_continuous_mode_goes_past_old_two_recapture_cap(self):
        fake=Fake(['NO']*5+['YES']);result=self.gate(fake).acquire(Frame.captured(BAD),lambda:Frame.captured(GOOD),cancelled=lambda:False)
        self.assertEqual(result['status'],'accepted');self.assertEqual(result['recaptures'],5);self.assertEqual(result['model_calls'],6)
    def test_manual_stop_after_no_does_not_forward_or_execute(self):
        fake=Fake(['NO']);c=GateController(self.gate(fake));actor=[];execute=[]
        result=c.step(Frame.captured(BAD),lambda:Frame.captured(GOOD),lambda f:actor.append(f),json.loads,lambda p:execute.append(p),cancelled=lambda:bool(fake.calls))
        self.assertEqual(result['status'],'cancelled');self.assertEqual(actor,[]);self.assertEqual(execute,[])
    def test_stop_during_sleep_avoids_recapture(self):
        fake=Fake(['NO']);state={'stop':False};captures=[]
        gate=ImageGate(fake,revision=REVISION,contract_sha256=CONTRACT,journal=self.journal,recapture_seconds=0.5,sleeper=lambda _:state.update(stop=True))
        result=gate.acquire(Frame.captured(BAD),lambda:captures.append(1),cancelled=lambda:state['stop'])
        self.assertEqual(result['status'],'cancelled');self.assertEqual(captures,[])
    def test_error_is_not_no_and_not_automatically_retried(self):
        class Broken:
            calls=0
            def decide(self,_):self.calls+=1;raise TimeoutError('preserved')
        bad=Broken();captures=[];result=self.gate(bad).acquire(Frame.captured(BAD),lambda:captures.append(1),cancelled=lambda:False)
        self.assertEqual(result['status'],'technical_failure');self.assertEqual(bad.calls,1);self.assertEqual(captures,[])
    def test_wrong_image_response_cannot_reach_actor(self):
        class Wrong:
            def decide(self,_):return Decision('YES',digest(GOOD),'x',REVISION,CONTRACT)
        c=GateController(self.gate(Wrong()));calls=[]
        result=c.step(Frame.captured(BAD),lambda:Frame.captured(GOOD),lambda f:calls.append(f),json.loads,lambda p:None,cancelled=lambda:False)
        self.assertEqual(result['status'],'technical_failure');self.assertEqual(calls,[])
    def test_missing_image_is_recaptured_without_fake_checker_no(self):
        fake=Fake(['YES']);result=self.gate(fake).acquire(Frame.captured(None),lambda:Frame.captured(GOOD),cancelled=lambda:False)
        self.assertEqual(result['status'],'accepted');self.assertEqual(fake.calls,[GOOD]);self.assertEqual(result['recaptures'],1)
    def test_reusing_old_capture_object_fails_even_if_request_context_empty(self):
        initial=Frame.captured(BAD);fake=Fake(['NO','YES'])
        result=self.gate(fake).acquire(initial,lambda:initial,cancelled=lambda:False)
        self.assertEqual(result['status'],'technical_failure');self.assertEqual(len(fake.calls),1)
    def test_native_parser_error_never_executes(self):
        fake=Fake(['YES']);c=GateController(self.gate(fake));actions=[]
        result=c.step(Frame.captured(GOOD),None,lambda _: 'invalid native action',json.loads,lambda p:actions.append(p),cancelled=lambda:False)
        self.assertEqual(result['status'],'technical_failure');self.assertEqual(actions,[])
    def test_main_history_and_original_parameters_preserved_no_gate_text(self):
        past=[{'role':'user','content':'MAIN_HISTORY_SENTINEL'},{'role':'assistant','content':'earlier uncertain observation'}]
        template={'model':'original','messages':[{'role':'system','content':'ORIGINAL SYSTEM'}],'temperature':0,'max_tokens':2048,'chat_template_kwargs':{'enable_thinking':False}}
        bodies=[];driver=NativeHistoryActor(template,lambda body:bodies.append(copy.deepcopy(body))or'{"type":"wait"}',past_messages=past,text_blocks=[{'type':'text','text':'Original task and execution feedback'}])
        fake=Fake(['NO','YES']);c=GateController(self.gate(fake))
        result=c.step(Frame.captured(BAD),lambda:Frame.captured(GOOD),driver,json.loads,lambda p:{'fixture':True,'environment_action':False},cancelled=lambda:False);driver.commit(result)
        body=bodies[0];self.assertEqual(body['messages'][0],template['messages'][0]);self.assertEqual(body['messages'][1:3],past)
        self.assertEqual({k:v for k,v in body.items()if k!='messages'},{k:v for k,v in template.items()if k!='messages'})
        raw=base64.b64decode(body['messages'][-1]['content'][-1]['image_url']['url'].split(',')[1]);self.assertEqual(raw,GOOD)
        self.assertNotIn('probabilities',json.dumps(body));self.assertEqual(driver.history[-1]['content'],result['candidate'])
    def test_wire_rejects_main_context_and_prompt_override(self):
        valid={'request_id':'a'*32,'image_sha256':digest(GOOD),'image_png_base64':base64.b64encode(GOOD).decode()}
        for key in ['state','prompt','messages','history','candidate','task','images','options']:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):decode_request(json.dumps({**valid,key:'forbidden'}).encode())
        req,raw=decode_request(json.dumps(valid).encode());self.assertEqual(raw,GOOD)
    def test_duplicate_wire_field_rejected(self):
        with self.assertRaises(ValueError):decode_request(b'{"request_id":"a","request_id":"b"}')
    def test_native_request_is_one_image_fixed_question_each_time(self):
        contract={'state':'fixed','question':'fixed q','options':{'YES':'usable','NO':'unusable'}}
        first=native_request(contract,GOOD);second=native_request(contract,BAD)
        self.assertEqual(first['images'],[GOOD]);self.assertEqual(second['images'],[BAD]);self.assertEqual(first['state'],second['state']);self.assertEqual(len(first['questions']),1)
    def test_actor_step_budget_stays_separate_from_unlimited_gate_recaptures(self):
        c=GateController(self.gate(Fake(['YES'])),max_steps=0)
        self.assertEqual(c.step(Frame.captured(GOOD),None,None,None,None,cancelled=lambda:False)['status'],'step_budget_exhausted')
    def test_template_history_not_silently_dropped(self):
        body={'messages':[{'role':'system','content':'system'},{'role':'user','content':'all native history'}],'max_tokens':2048}
        seen=[];actor=NativeHistoryActor(body,lambda v:seen.append(copy.deepcopy(v))or 'STOP')
        actor(Frame.captured(GOOD));self.assertEqual(seen[0]['messages'][1],body['messages'][1])
    def test_transport_mutation_stops_before_execution(self):
        def mutate(body):body['messages'][0]['content']='changed';return '{}'
        actor=NativeHistoryActor({'messages':[{'role':'system','content':'original'}]},mutate)
        executed=[];c=GateController(self.gate(Fake(['YES'])))
        result=c.step(Frame.captured(GOOD),None,actor,json.loads,lambda p:executed.append(p),cancelled=lambda:False)
        self.assertEqual(result['status'],'technical_failure');self.assertEqual(executed,[])
    def test_stop_after_actor_reply_prevents_dispatch(self):
        stop=[];executed=[];c=GateController(self.gate(Fake(['YES'])))
        result=c.step(Frame.captured(GOOD),None,lambda f:stop.append(1)or '{}',json.loads,lambda p:executed.append(p),cancelled=lambda:bool(stop))
        self.assertEqual(result['status'],'cancelled');self.assertEqual(executed,[])

if __name__=='__main__':unittest.main(verbosity=2)
