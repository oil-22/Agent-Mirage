import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'flash-binary-gate-framework-20261113'))
from gate_core import Frame,GateController,ImageGate,Journal,Decision,digest
from wire_contract import REVISION
from gui_experiment import Bypass,LiveAdapter
CONTRACT='a'*64
class Environment:
    def __init__(self):self.current=b'new observed PNG';self.captures=0;self.steps=[];self.context=SimpleNamespace(pages=[1]);self.page=SimpleNamespace(wait_for_timeout=lambda _:None)
    def _get_obs(self):self.captures+=1;return self.current
    def step(self,p):self.steps.append(copy.deepcopy(p));return self.current,True,None,None,{}
class Transport:
    def __init__(self):self.bodies=[]
    def actor(self,body,*args):self.bodies.append(copy.deepcopy(body));return '{"type":"click","x":10,"y":20}'
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.env=Environment();self.t=Transport();self.log=Journal(self.root/'journal')
        self.a=LiveAdapter(self.env,b'first',{}, {'intent':'public task'},{'run_id':'new-run','condition':'stale_replace'}, {'messages':[{'role':'system','content':'native system'}],'temperature':0,'max_tokens':2048,'chat_template_kwargs':{'enable_thinking':False}},self.t,self.root,self.log,json.loads,lambda p:copy.deepcopy(p),lambda n:{'type':'tab','index':n},lambda x:x,lambda t:{'type':'stop','answer':t})
    def tearDown(self):self.tmp.cleanup()
    def test_stale_once_then_fresh_same_live_capture(self):
        self.a.step=2;self.a.last_image=b'old supplied';self.a.previous={'type':'click'};self.a.obs=b'new observed PNG'
        initial=self.a.initial_frame();self.assertEqual(initial.png,b'old supplied');self.assertTrue(self.a.fired)
        recapture=self.a.capture();self.assertEqual(recapture.png,b'new observed PNG');self.assertEqual(self.env.captures,1);self.assertEqual(self.env.steps,[])
        self.a.step=3;self.assertEqual(self.a.initial_frame().png,b'new observed PNG')
    def test_no_gate_control_never_calls_Flash_or_fabricates_model_yes(self):
        gate=Bypass(self.log);f=Frame.captured(b'exact');r=gate.acquire(f,None,cancelled=lambda:False)
        self.assertEqual(r['frame'],f);self.assertEqual(gate.calls,0);self.assertIsNone(r['decision'].request_id)
    def test_gate_passed_frame_and_complete_main_history(self):
        self.a.step=1
        class Checker:
            def decide(self,png):return Decision('YES',digest(png),'real-binding-fixture',REVISION,CONTRACT)
        c=GateController(ImageGate(Checker(),revision=REVISION,contract_sha256=CONTRACT,journal=self.log,recapture_seconds=0))
        first=c.step(Frame.captured(b'first accepted'),self.a.capture,self.a.actor,self.a.parse,self.a.execute,cancelled=lambda:False);self.a.commit(first)
        self.a.step=2;second=c.step(Frame.captured(b'second accepted'),self.a.capture,self.a.actor,self.a.parse,self.a.execute,cancelled=lambda:False);self.a.commit(second)
        self.assertEqual(len(self.t.bodies),2);self.assertEqual(self.t.bodies[1]['messages'][:3],self.t.bodies[0]['messages']+[{'role':'assistant','content':first['candidate']}]);self.assertEqual(len(self.env.steps),2)
    def test_invalid_native_action_has_no_environment_effect(self):
        self.a.native_parse=lambda _:(_ for _ in()).throw(ValueError('invalid native dialect'))
        with self.assertRaises(ValueError):self.a.parse('invalid')
        self.assertTrue(self.a.parser_failed);self.assertEqual(self.env.steps,[])
    def test_stop_separate_from_environment_action(self):
        self.a.main.pending={'reply':'native STOP'};r=self.a.execute({'type':'stop','answer':'done'})
        self.assertFalse(r['environment_action']);self.assertTrue(self.a.stopped);self.assertEqual(self.env.steps,[])
if __name__=='__main__':unittest.main(verbosity=2)
