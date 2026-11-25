import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from defense.core import canonical,digest,InferenceFailure
from defense.http_backend import RemoteQwen
from online_transport import OnlineQwen
from image_observer import ObserverClient,wire,contract,REVISION,MODEL
from test_image_observer import Log,frame,view
from observer_launch_contract import validate_launch_inputs


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.token=self.root/'token';self.token.write_text('private-test-token-never-log')
        self.log=Log();self.q=OnlineQwen('http://127.0.0.1:12345',self.token)
        self.q.set_run('known-run',self.log)
    def tearDown(self):self.temp.cleanup()

    def post(self,url,data,headers,timeout):
        obj=json.loads(data)
        out={'request_id':obj['request_id'],'external_wire_sha256':digest(data)}
        if 'payload'in obj:out.update(payload_sha256=digest(canonical(obj['payload'])),text='native-action',verdict={'raw':'native'})
        return SimpleNamespace(ok=True,status_code=200,json=lambda:out,content=canonical(out))

    def test_primary_actor_judge_native_methods_identical(self):
        self.assertIs(OnlineQwen.actor,RemoteQwen.actor);self.assertIs(OnlineQwen.judge,RemoteQwen.judge)

    def test_lifecycle_and_actual_native_payload_bindings(self):
        with patch('online_transport.requests.post',side_effect=self.post)as send:
            self.q.begin_run();self.q.set_decision(1)
            native={'messages':[{'role':'user','content':'FULL original text'}],'max_tokens':2048}
            original=copy.deepcopy(native);self.assertEqual(self.q.actor(native),'native-action')
            self.assertEqual(native,original)
            self.q.end_run('completed','a'*64)
            self.assertEqual(send.call_count,3)
        row=next(v for k,v in self.log.rows if k=='actual_primary_wire_request')
        self.assertEqual(json.loads(row['wire_utf8'])['payload'],{'operation':'actor','body':native})
        self.assertNotIn('private-test-token',json.dumps(self.log.rows))

    def test_full_primary_judge_public_unchanged_by_outer_metadata(self):
        v=view(frame());before=digest(canonical(v.data()))
        with patch('online_transport.requests.post',side_effect=self.post):
            self.q.begin_run();self.q.set_decision(2);self.q.judge('strict-original',v,'original-candidate')
        row=next(v for k,v in self.log.rows if k=='actual_primary_wire_request')
        p=row['body']['payload']
        self.assertEqual(p['system'],'strict-original');self.assertEqual(p['candidate'],'original-candidate')
        self.assertEqual(p['view']['messages'],v.messages)
        self.assertEqual(digest(canonical(v.data())),before)
        self.assertNotIn('trajectory_id',p['view'])

    def test_no_online_call_without_active_run_or_with_budget_excess(self):
        with patch('online_transport.requests.post',side_effect=self.post)as send:
            with self.assertRaises(InferenceFailure):self.q.actor({})
            self.assertFalse(send.called)
            self.q.active=True;self.q.set_decision(1);self.q.attempts['actor']=70
            with self.assertRaises(InferenceFailure):self.q.actor({})
            self.assertFalse(send.called)
            with self.assertRaises(InferenceFailure):self.q.set_decision(51)

    def test_bad_actual_wire_response_rejected(self):
        def bad(*args,**kwargs):
            result=self.post(*args,**kwargs);result.json=lambda:{'request_id':'wrong','external_wire_sha256':'wrong'};return result
        with patch('online_transport.requests.post',side_effect=bad):
            with self.assertRaises(InferenceFailure):self.q.begin_run()
        self.assertFalse(self.q.active)

    def test_gate_false_readiness_rejects_before_any_input_access(self):
        p=self.root/'ready.json';p.write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'prerequisites'):
            validate_launch_inputs(SimpleNamespace(readiness=p))

    def test_gate_missing_concrete_preflight_is_fail_closed(self):
        p=self.root/'ready.json';p.write_text(json.dumps({'policy':'single-flash-image-observer-actor-v1','launch_ready':True}))
        plan=self.root/'plan.json';plan.write_text('{}')
        with self.assertRaises((KeyError,RuntimeError)):
            validate_launch_inputs(SimpleNamespace(readiness=p,plan=plan))

if __name__=='__main__':unittest.main(verbosity=2)
