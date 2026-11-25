import base64
import copy
import io
import json
from dataclasses import replace
import unittest
from PIL import Image
from defense.core import PublicView, VisibleImage, canonical, digest
from image_observer import *


class Log:
    def __init__(self): self.rows=[]
    def append(self,k,v):self.rows.append((k,copy.deepcopy(v)))


def frame(color='white'):
    out=io.BytesIO();Image.new('RGB',(80,60),color).save(out,format='PNG');return VisibleImage(out.getvalue())


def view(image=None,obs='obs-1'):
    blocks=[{'type':'text','text':'Task: task-secret. History and target remain primary only.'}]
    images=()
    if image:
        blocks.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(image.raw).decode()}})
        images=(image,)
    return PublicView(obs,[{'role':'system','content':'native-system'},{'role':'assistant','content':'secret-history'},
                          {'role':'user','content':blocks}],images,'secret-action','secret-feedback')


def body(v):return {'model':'original','temperature':0,'max_tokens':2048,
    'chat_template_kwargs':{'enable_thinking':False},'messages':copy.deepcopy(v.messages)}


class Fake:
    model=MODEL;revision=REVISION
    def __init__(self):self.requests=[];self.fail=False;self.bad=None
    def send_raw(self,raw):
        b=json.loads(raw);self.requests.append(b)
        if self.fail:raise RuntimeError('preserved-technical-failure')
        answers={}
        for key,q in QUESTIONS.items():
            opts=list(q['criteria']);chosen=opts[-1]
            answers[key]={'choice':chosen,'probabilities':{o:1.0 if o==chosen else 0.0 for o in opts}}
        r={'status':'ok','model':MODEL,'revision':REVISION,'request_id':b['request_id'],
           'request_sha256':digest(raw),'image_sha256':b['image_sha256'],'answers':answers,
           'usage':{'sequences':1},'generation_tokens':0}
        if self.bad:r[self.bad]='mismatch'
        return r


class Tests(unittest.TestCase):
    def test_native_observer_payload_excludes_context(self):
        f=Fake();o=ActorObserver(f,True);v=view(frame());o.packet(v,Log());r=f.requests[0]
        self.assertEqual(set(r),{'request_id','image_base64','image_sha256','state','questions','provenance'})
        self.assertEqual(set(r['provenance']),{'observation_id','image_sha256'})
        for secret in ['task-secret','secret-history','secret-action','secret-feedback']:
            self.assertNotIn(secret,json.dumps(r))
        self.assertEqual(r['state'],STATE);self.assertEqual(r['questions'],QUESTIONS)

    def test_native_order_exact_frozen_file(self):
        raw=(Path(__file__).parent/'observer-contract.json').read_bytes()
        self.assertEqual(raw,wire(contract()));parsed=json.loads(raw)
        self.assertEqual(list(parsed['questions']),list(QUESTIONS))
        for k,q in QUESTIONS.items():self.assertEqual(list(parsed['questions'][k]['criteria']),list(q['criteria']))

    def test_baseline_zero_calls_no_image_information(self):
        f=Fake();p=ActorObserver(f,False).packet(view(frame()),Log())
        self.assertEqual(f.requests,[]);self.assertEqual(p['status'],'observer_not_run')
        self.assertFalse(p['observations']);self.assertNotIn('image_sha256',p)

    def test_no_frame_zero_calls_and_no_previous_prediction(self):
        f=Fake();o=ActorObserver(f,True);o.packet(view(frame()),Log())
        p=o.packet(view(None,'obs-2'),Log())
        self.assertEqual(o.calls,1);self.assertEqual(p['status'],'unavailable');self.assertFalse(p['observations'])

    def test_exact_native_input_reuse_rebinds_current_observation(self):
        o=ActorObserver(Fake(),True);im=frame();o.packet(view(im),Log())
        p=o.packet(view(im,'obs-2'),Log())
        self.assertEqual(o.calls,1);self.assertEqual(p['status'],'exact_native_input_reuse')
        self.assertEqual(p['observation_id'],'obs-2')

    def test_different_received_frame_is_new_input(self):
        o=ActorObserver(Fake(),True);o.packet(view(frame()),Log());o.packet(view(frame('black')),Log())
        self.assertEqual(o.calls,2)

    def test_failed_input_not_retried(self):
        f=Fake();f.fail=True;o=ActorObserver(f,True);v=view(frame())
        self.assertEqual(o.packet(v,Log())['status'],'technical_failure')
        self.assertEqual(o.packet(v,Log())['status'],'preserved_failure_no_retry')
        self.assertEqual(o.calls,1)

    def test_cap_exhaustion_zero_extra_calls(self):
        o=ActorObserver(Fake(),True,max_calls=1);o.packet(view(frame()),Log())
        p=o.packet(view(frame('black')),Log())
        self.assertEqual(p['status'],'auxiliary_budget_exhausted');self.assertEqual(o.calls,1)

    def test_budget_expansion_rejected(self):
        for cap in [61,True,-1,1.5]:
            with self.assertRaises(ValueError):ActorObserver(Fake(),True,cap)

    def test_identity_mismatch_withheld(self):
        for bad in ['model','revision','request_sha256','image_sha256','request_id']:
            f=Fake();f.bad=bad;p=ActorObserver(f,True).packet(view(frame()),Log())
            self.assertEqual(p['status'],'technical_failure');self.assertFalse(p['observations'])

    def test_probabilities_and_unknown_not_rewritten(self):
        p=ActorObserver(Fake(),True).packet(view(frame()),Log())
        self.assertEqual([r['model_prediction']for r in p['observations']],
            ['non_gui_or_unknown','unknown','unknown'])
        bad={'choice':'unknown','probabilities':{'unknown':float('nan')}}
        self.assertFalse(valid_answer(bad,{'unknown':''}))

    def test_shared_boundary_both_arms_preserve_history_images_and_params(self):
        v=view(frame());original=body(v);public_hash=digest(canonical(v.data()))
        before=copy.deepcopy(original)
        for enabled in [False,True]:
            log=Log();actual=ActorObserver(Fake(),enabled).augment(original,v,log)
            self.assertEqual(actual['messages'][:-1],before['messages'][:-1])
            self.assertEqual(actual['messages'][-1]['content'][:-1],before['messages'][-1]['content'])
            self.assertTrue(actual['messages'][-1]['content'][-1]['text'].startswith(SHARED_ACTOR_INSTRUCTIONS))
            self.assertEqual({k:v for k,v in actual.items()if k!='messages'},
                             {k:v for k,v in original.items()if k!='messages'})
            wire_row=next(r for k,r in log.rows if k=='actor_observer_native_payload')
            self.assertEqual(digest(wire_row['wire_utf8'].encode()),wire_row['wire_sha256'])
            self.assertEqual(json.loads(wire_row['wire_utf8']),{'operation':'actor','body':actual})
        self.assertEqual(original,before);self.assertEqual(digest(canonical(v.data())),public_hash)

    def test_declared_image_not_wire_image_rejected_before_call(self):
        f=Fake();v=view(frame());b=body(v);b['messages'][-1]['content'][1]['image_url']['url']='wrong'
        with self.assertRaises(ValueError):ActorObserver(f,True).augment(b,replace(v,messages=b['messages']),Log())
        self.assertFalse(f.requests)

    def test_real_controller_regeneration_tail_correction_and_latest_frame(self):
        old=frame('black');current=frame('white');v=view(current)
        earlier={'role':'user','content':[{'type':'image_url','image_url':{
            'url':'data:image/png;base64,'+base64.b64encode(old.raw).decode()}}]}
        correction={'role':'user','content':'TASK-STATE CORRECTION. Original strict correction retained.'}
        v=replace(v,messages=[v.messages[0],earlier]+v.messages[1:]+[correction])
        f=Fake();log=Log();actual=ActorObserver(f,True).augment(body(v),v,log)
        self.assertEqual(actual['messages'][-1],correction)
        self.assertEqual(actual['messages'][1],earlier)
        self.assertEqual(f.requests[0]['image_sha256'],digest(current.raw))
        self.assertNotEqual(f.requests[0]['image_sha256'],digest(old.raw))
        self.assertEqual(actual['messages'][-2]['content'][:-1],v.messages[-2]['content'])
        row=next(r for k,r in log.rows if k=='actor_observer_native_payload')
        self.assertEqual(row['current_user_message_index'],len(v.messages)-2)

    def test_body_must_preserve_full_public_messages(self):
        f=Fake();v=view(frame());b=body(v);b['messages'].pop(1)
        with self.assertRaises(ValueError):ActorObserver(f,True).augment(b,v,Log())
        self.assertFalse(f.requests)

    def test_no_strict_controller_subclass_or_verdict_override(self):
        self.assertNotIn('Controller',ActorObserver.__bases__[0].__name__)
        self.assertFalse(hasattr(ActorObserver,'decide'))
        self.assertFalse(hasattr(ActorObserver,'judge'))

if __name__=='__main__':unittest.main(verbosity=2)
