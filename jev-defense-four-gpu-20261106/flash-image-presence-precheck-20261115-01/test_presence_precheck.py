"""New CPU routing controls only: no Flash inference, real browser or scorer."""
import ast
import base64
import copy
import hashlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'source/flash'),str(HERE/'source')]
from gate_core import (Decision,Frame,GateController,ImageGate,Journal,
                       NativeHistoryActor,canonical,check_image_presence,digest)
from gui_experiment import LiveAdapter
from wire_contract import REVISION

PARENT=HERE.parent/'flash-late-corruption-defense-20261115-02'
FIXTURES=PARENT/'frame-loop-source-evidence-1794753474558377200/images'
GOOD=(FIXTURES/'682ca32fbaa1af4c27dbcc6859a08bcb7056cd3778cb8eb408a08191850b56b0.png').read_bytes()
WHITE=(FIXTURES/'e52ae68d052db9f6f16fb6b5d2498e83b09545c9daaf4579e6c406a5713ad11f.png').read_bytes()
assert digest(GOOD)=='682ca32fbaa1af4c27dbcc6859a08bcb7056cd3778cb8eb408a08191850b56b0'
assert digest(WHITE)=='e52ae68d052db9f6f16fb6b5d2498e83b09545c9daaf4579e6c406a5713ad11f'
ARRAY=np.array(Image.open(io.BytesIO(GOOD)))
CONTRACT=digest((HERE/'source/flash/gate-contract.json').read_bytes())
native_source=(HERE/'source/native-parser-source.py').read_text('utf8')
tree=ast.parse(native_source)
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['png','parse']]
native={'io':io,'Image':Image,'json':json,'re':re}
exec(compile(ast.Module(body=functions,type_ignores=[]),'original-native-png-and-parse','exec'),native)
NATIVE_GOOD=native['png']({'image':ARRAY})
NATIVE_WHITE=native['png']({'image':np.full_like(ARRAY,255)})
# The unchanged native encoder runs locally. Its PNG compression need not match
# a remote encoder byte for byte; its pixels and its own wire binding must match.
assert np.array_equal(np.array(Image.open(io.BytesIO(NATIVE_GOOD))),ARRAY)
assert np.array_equal(np.array(Image.open(io.BytesIO(NATIVE_WHITE))),np.full_like(ARRAY,255))


class FakeFlash:
    def __init__(self,answers):self.answers=iter(answers);self.calls=[]
    def decide(self,png):
        self.calls.append(png)
        return Decision(next(self.answers),digest(png),f'CPU-fixture-{len(self.calls)}',REVISION,CONTRACT)


class PresenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.journal=Journal(self.root/'controller')
    def tearDown(self):self.temp.cleanup()
    def gate(self,checker):
        return ImageGate(checker,revision=REVISION,contract_sha256=CONTRACT,
                         journal=self.journal,recapture_seconds=0)
    def events(self):
        rows=[json.loads(x) for x in (self.journal.root/'events.jsonl').read_bytes().splitlines()]
        head='0'*64
        for i,row in enumerate(rows):
            self.assertEqual((row['seq'],row['previous']),(i,head))
            self.assertEqual(row['sha256'],digest(canonical({k:v for k,v in row.items() if k!='sha256'})))
            head=row['sha256']
        return rows
    def adapter(self,obs,recaptures,*,step=1):
        observations=iter(recaptures)
        class Environment:
            calls=0
            def _get_obs(self):self.calls+=1;return next(observations)
        adapter=LiveAdapter.__new__(LiveAdapter)
        adapter.env=Environment();adapter.obs=obs;adapter.png=native['png']
        adapter.step=step;adapter.previous={'type':'click'};adapter.last_image=b'previous-frame'
        adapter.item={'condition':'late_white3'};adapter.root=self.root;adapter.log=self.journal
        return adapter

    def test_none_and_empty_return_explicit_precheck_NO(self):
        self.assertEqual((check_image_presence(None).value,check_image_presence(None).reason),('NO','missing_image'))
        self.assertEqual((check_image_presence(b'').value,check_image_presence(b'').reason),('NO','empty_image_data'))

    def test_file_absent_empty_and_existing(self):
        file=self.root/'capture.png'
        self.assertEqual(check_image_presence(Frame.from_file(file).png).value,'NO')
        file.write_bytes(b'')
        self.assertEqual(check_image_presence(Frame.from_file(file).png).value,'NO')
        file.write_bytes(GOOD)
        frame=Frame.from_file(file)
        self.assertEqual(frame.png,GOOD)
        self.assertEqual(check_image_presence(frame.png).value,'YES')

    def test_other_file_IO_errors_are_not_fabricated_missing_NO(self):
        with self.assertRaises(OSError):Frame.from_file(self.root)

    def test_white_image_exists_and_still_requires_Flash(self):
        fake=FakeFlash(['NO','YES']);gate=self.gate(fake)
        result=gate.acquire(Frame.captured(WHITE),lambda:Frame.captured(GOOD),cancelled=lambda:False)
        self.assertEqual(fake.calls,[WHITE,GOOD])
        self.assertEqual(result['precheck_NO_count'],0)
        self.assertEqual(result['model_calls'],2)

    def test_missing_empty_then_Flash_NO_then_YES_routes_only_present_images(self):
        fake=FakeFlash(['NO','YES']);gate=self.gate(fake)
        frames=iter([Frame.captured(b''),Frame.captured(WHITE),Frame.captured(GOOD)])
        main=[];actions=[];controller=GateController(gate)
        result=controller.step(Frame.captured(None),lambda:next(frames),
            lambda f:main.append(f.png)or'<action>{"type":"wait"}</action>',native['parse'],
            lambda p:actions.append(p)or{'environment_action':False,'CPU_fixture':True},cancelled=lambda:False)
        self.assertEqual(result['status'],'dispatched')
        self.assertEqual(fake.calls,[WHITE,GOOD]);self.assertEqual(main,[GOOD])
        self.assertEqual(actions,[{'type':'wait'}])
        self.assertEqual((result['gate']['precheck_NO_count'],gate.calls,gate.recaptures),(2,2,3))
        rows=self.events()
        prechecks=[r for r in rows if r['kind']=='precheck_decision']
        self.assertEqual(len(prechecks),2)
        self.assertTrue(all(r['data']['decision']=='NO' and r['data']['not_a_model_NO'] and not r['data']['Flash_called'] for r in prechecks))
        self.assertLess(max(r['seq'] for r in prechecks),min(r['seq'] for r in rows if r['kind']=='gate_decision'))
        self.assertEqual(len([r for r in rows if r['kind']=='main_image_forwarded']),1)

    def test_continuously_missing_images_stop_only_on_manual_cancellation(self):
        fake=FakeFlash([]);gate=self.gate(fake);captures=[];main=[];actions=[]
        def capture():captures.append(1);return Frame.captured(None)
        result=GateController(gate).step(Frame.captured(None),capture,
            lambda f:main.append(f),native['parse'],lambda p:actions.append(p),cancelled=lambda:len(captures)>=7)
        self.assertEqual(result['status'],'cancelled')
        self.assertEqual(len(captures),7);self.assertEqual(fake.calls,[])
        self.assertEqual(main,[]);self.assertEqual(actions,[])
        self.assertEqual(result['model_calls'],0)
        self.assertGreater(result['precheck_NO_count'],2)
        self.events()

    def test_missing_file_during_loop_is_recaptured_without_Flash_call(self):
        file=self.root/'capture.png';file.write_bytes(WHITE)
        initial=Frame.from_file(file);file.unlink()
        frames=[];fake=FakeFlash(['NO','YES']);gate=self.gate(fake)
        def capture():
            if not frames:
                frames.append('missing');return Frame.from_file(file)
            file.write_bytes(GOOD);frames.append('present');return Frame.from_file(file)
        result=gate.acquire(initial,capture,cancelled=lambda:False)
        self.assertEqual(result['status'],'accepted')
        self.assertEqual(fake.calls,[WHITE,GOOD]);self.assertEqual(result['precheck_NO_count'],1)
        self.assertEqual(result['recaptures'],2)

    def test_reused_missing_capture_id_cannot_spin_forever(self):
        frame=Frame.captured(None);fake=FakeFlash([])
        result=self.gate(fake).acquire(frame,lambda:frame,cancelled=lambda:False)
        self.assertEqual(result['status'],'technical_failure')
        self.assertEqual(result['reason'],'capture_callback_reused_an_old_capture_id')
        self.assertEqual(fake.calls,[])

    def test_Flash_failure_remains_technical_failure(self):
        class Broken:
            def decide(self,_):raise TimeoutError('fixture transport failure')
        captures=[];gate=self.gate(Broken())
        result=gate.acquire(Frame.captured(GOOD),lambda:captures.append(1),cancelled=lambda:False)
        self.assertEqual(result['status'],'technical_failure')
        self.assertEqual(result['precheck_NO_count'],0);self.assertEqual(captures,[])
        self.assertFalse(any(r['kind']=='precheck_decision' for r in self.events()))

    def test_nonempty_invalid_image_is_not_mislabelled_as_absent(self):
        class RejectInvalid:
            calls=[]
            def decide(self,png):self.calls.append(png);raise ValueError('Invalid PNG remains an error')
        checker=RejectInvalid();gate=self.gate(checker)
        result=gate.acquire(Frame.captured(b'not-a-valid-PNG'),None,cancelled=lambda:False)
        self.assertEqual(checker.calls,[b'not-a-valid-PNG'])
        self.assertEqual((result['status'],result['precheck_NO_count']),('technical_failure',0))

    def test_wrong_bound_Flash_reply_still_cannot_reach_main(self):
        class Wrong:
            def decide(self,_):return Decision('YES',digest(WHITE),'wrong',REVISION,CONTRACT)
        main=[];controller=GateController(self.gate(Wrong()))
        result=controller.step(Frame.captured(GOOD),None,lambda f:main.append(f),native['parse'],None,cancelled=lambda:False)
        self.assertEqual(result['status'],'technical_failure');self.assertEqual(main,[])

    def test_presence_YES_does_not_bypass_Flash_NO(self):
        fake=FakeFlash(['NO']);main=[];actions=[]
        result=GateController(self.gate(fake)).step(Frame.captured(GOOD),None,
            lambda f:main.append(f),native['parse'],lambda p:actions.append(p),cancelled=lambda:bool(fake.calls))
        self.assertEqual(result['status'],'cancelled');self.assertEqual(main,[]);self.assertEqual(actions,[])

    def test_native_missing_observation_never_reaches_original_encoder(self):
        adapter=self.adapter(None,[])
        calls=[];adapter.png=lambda obs:calls.append(obs)or GOOD
        for missing in [None,{}, {'image':None},{'image':b''},{'image':np.empty((0,0,3),dtype=np.uint8)}]:
            adapter.obs=missing
            self.assertEqual(check_image_presence(adapter.observation_png_or_missing()).value,'NO')
        self.assertEqual(calls,[])
        adapter.obs={'image':ARRAY}
        self.assertEqual(adapter.observation_png_or_missing(),GOOD)
        self.assertEqual(len(calls),1)

    def test_live_adapter_initial_missing_calls_same_capture_hook_then_Flash(self):
        adapter=self.adapter(None,[{'image':ARRAY}])
        fake=FakeFlash(['YES']);gate=self.gate(fake);main=[]
        result=GateController(gate).step(adapter.initial_frame(),adapter.capture,
            lambda f:main.append(f.png)or'<action>{"type":"wait"}</action>',native['parse'],
            lambda p:{'environment_action':False,'CPU_fixture':True},cancelled=lambda:False)
        self.assertEqual(result['status'],'dispatched')
        self.assertEqual(adapter.env.calls,1)
        self.assertEqual(fake.calls,main)
        self.assertEqual(len(main),1);self.assertEqual(digest(main[0]),digest(NATIVE_GOOD))
        self.assertEqual(adapter.corruption_episode.index,1)
        self.assertEqual(result['gate']['precheck_NO_count'],1)
        rows=self.events()
        self.assertEqual(len([r for r in rows if r['kind']=='acquisition_image_missing']),1)
        self.assertEqual(len([r for r in rows if r['kind']=='capture']),2)

    def test_missing_recapture_does_not_consume_image_injection_dose(self):
        adapter=self.adapter({'image':ARRAY},[None,{'image':ARRAY},{'image':ARRAY},{'image':ARRAY}],step=10)
        fake=FakeFlash(['NO','NO','NO','YES']);gate=self.gate(fake);main=[]
        result=GateController(gate).step(adapter.initial_frame(),adapter.capture,
            lambda f:main.append(f.png)or'<action>{"type":"wait"}</action>',native['parse'],
            lambda p:{'environment_action':False,'CPU_fixture':True},cancelled=lambda:False)
        self.assertEqual(result['status'],'dispatched')
        self.assertEqual([digest(p)for p in fake.calls],[digest(NATIVE_WHITE)]*3+[digest(NATIVE_GOOD)])
        self.assertEqual([digest(p)for p in main],[digest(NATIVE_GOOD)])
        self.assertEqual((adapter.env.calls,gate.recaptures,gate.calls,gate.precheck_no),(4,4,4,1))
        self.assertEqual((adapter.corruption_episode.used,adapter.corruption_episode.index),(3,4))
        rows=self.events()
        self.assertEqual(len([r for r in rows if r['kind']=='PRIVATE_capture_injection']),4)
        self.assertEqual(len([r for r in rows if r['kind']=='capture']),5)

    def test_missing_post_action_observation_reaches_next_precheck_and_recapture(self):
        adapter=self.adapter({'image':ARRAY},[{'image':ARRAY}],step=1)
        dispatched=[]
        adapter.action=lambda p:copy.deepcopy(p)
        adapter.main=type('OriginalActorState',(),{'pending':{'reply':'original native reply'}})()
        adapter.trajectory=[];adapter.environment_actions=0
        adapter.env.step=lambda action:dispatched.append(copy.deepcopy(action))or(None,True,False,False,{})
        execution=adapter.execute({'type':'click','x':50,'y':50})
        self.assertEqual(execution['ok'],True)
        self.assertEqual(adapter.environment_actions,1)
        self.assertEqual(dispatched,[{'type':'click','x':50,'y':50,'raw_prediction':'original native reply'}])
        adapter.step=2;fake=FakeFlash(['YES']);main=[]
        result=GateController(self.gate(fake)).step(adapter.initial_frame(),adapter.capture,
            lambda f:main.append(f.png)or'<action>{"type":"wait"}</action>',native['parse'],
            lambda p:{'environment_action':False,'CPU_fixture':True},cancelled=lambda:False)
        self.assertEqual(result['status'],'dispatched')
        self.assertEqual([digest(p)for p in main],[digest(NATIVE_GOOD)])
        self.assertEqual([digest(p)for p in fake.calls],[digest(NATIVE_GOOD)])
        self.assertEqual(adapter.env.calls,1)
        self.assertEqual(result['gate']['precheck_NO_count'],1)
        row=next(r for r in self.events()if r['kind']=='native_environment_action')
        self.assertEqual(row['data']['current_capture_sha256'],None)
        self.assertEqual(row['data']['current_image_present'],False)

    def test_full_native_actor_history_system_and_parameters_survive_missing_loop(self):
        template=json.loads((HERE/'source/actor-template.json').read_bytes())
        past=[{'role':'user','content':'complete prior native history'},{'role':'assistant','content':'uncertain earlier observation'}]
        bodies=[];reply='<action>{"type":"wait"}</action>'
        actor=NativeHistoryActor(template,lambda body:bodies.append(copy.deepcopy(body))or reply,
                                 past_messages=past,text_blocks=[{'type':'text','text':'original task'}])
        fake=FakeFlash(['YES']);controller=GateController(self.gate(fake))
        result=controller.step(Frame.captured(None),lambda:Frame.captured(GOOD),actor,native['parse'],
            lambda p:{'environment_action':False,'CPU_fixture':True},cancelled=lambda:False)
        actor.commit(result)
        self.assertEqual(len(bodies),1)
        body=bodies[0]
        self.assertEqual(body['messages'][0],template['messages'][0])
        self.assertEqual(body['messages'][1:3],past)
        self.assertEqual({k:v for k,v in body.items() if k!='messages'},
                         {k:v for k,v in template.items() if k!='messages'})
        image=body['messages'][-1]['content'][-1]['image_url']['url']
        self.assertEqual(base64.b64decode(image.split(',',1)[1]),GOOD)
        self.assertNotIn('precheck',json.dumps(body));self.assertEqual(controller.actor_calls,1)
        self.assertEqual(actor.history[-1],{'role':'assistant','content':reply})

    def test_capture_error_is_not_converted_to_missing_image_NO(self):
        fake=FakeFlash(['NO']);gate=self.gate(fake)
        def broken_capture():raise RuntimeError('browser capture failed')
        result=gate.acquire(Frame.captured(WHITE),broken_capture,cancelled=lambda:False)
        self.assertEqual((result['status'],result['reason']),('technical_failure','capture_failed'))
        self.assertEqual(result['precheck_NO_count'],0)


if __name__=='__main__':
    print(json.dumps({'CPU_fixture_images':{'archived_original_sha256':digest(GOOD),
          'archived_white_sha256':digest(WHITE),'local_native_original_sha256':digest(NATIVE_GOOD),
          'local_native_white_sha256':digest(NATIVE_WHITE),'original_pixels_preserved':True},
          'real_model_calls':0,'real_GUI_calls':0}))
    unittest.main(verbosity=2)
