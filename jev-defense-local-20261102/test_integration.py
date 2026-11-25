"""Control-flow tests only. No model-accuracy claim."""
import copy, io, json, pathlib, sys, tempfile, unittest
from PIL import Image
from defense.core import Controller,Journal,PublicView,VisibleImage,Limits,canonical
from jev_auxiliary import JevAuxiliary,JevAssistedController
from jev_auxiliary import LocalDecisionClient,REVISIONS,QUESTIONS
from unittest.mock import patch
import hashlib
from serve_local import resource_snapshot
def view():
    out=io.BytesIO();Image.new('RGB',(80,60),'white').save(out,format='PNG')
    return PublicView('test',[{'role':'user','content':'Full legal history remains here'}],(VisibleImage(out.getvalue()),))
def screen(v):return {'status':'usable','visible':['test fixture'],'limitations':[],'loading':'not_observed','evidence':[{'observation_id':v.observation_id,'image_index':0,'coordinate_space':'pixels','box_xyxy':[0,0,80,60],'description':'fixture'}],'reason':'contract fixture only'}
class Client:
    model='jev_style'
    def __init__(self,fail=False):self.fail=fail;self.n=0
    def decide(self,image,key,source):
        self.n+=1
        if self.fail:raise RuntimeError('Preserved test failure')
        return {'answer':'unknown','probabilities':{'unknown':1},'image_sha256':source['image_sha256']}
class Tests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_controller_full_input_result_and_original_budget_unchanged(self):
        v=view();before=canonical(v.data());seen=[]
        def judge(system,obs,candidate):seen.append((system,canonical(obs.data()),candidate));return screen(obs)
        base=Controller(judge,Journal(self.root/'base'));expected=base.inspect('screen',v);base_seen=seen[-1]
        aux=JevAuxiliary([Client()]);c=JevAssistedController(judge,Journal(self.root/'aux'),jev_auxiliary=aux)
        self.assertEqual(c.inspect('screen',v),expected);self.assertEqual(seen[-1],base_seen)
        self.assertEqual(c.verifier_calls,base.verifier_calls);self.assertEqual(before,canonical(v.data()));self.assertEqual(aux.calls,1)
    def test_wait_has_zero_auxiliary_calls(self):
        aux=JevAuxiliary([Client()]);self.assertEqual(aux.observe('verify',view(),{'name':'wait'},Journal(self.root/'j')),[]);self.assertEqual(aux.calls,0)
    def test_failed_auxiliary_does_not_relax_or_break_original_gate(self):
        aux=JevAuxiliary([Client(True)]);c=JevAssistedController(lambda _,v,c:screen(v),Journal(self.root/'j'),jev_auxiliary=aux)
        self.assertEqual(c.inspect('screen',view())['status'],'usable');self.assertEqual(aux.calls,1)
    def test_exact_image_question_reuse_binds_new_observation(self):
        aux=JevAuxiliary([Client()]);j=Journal(self.root/'j');v=view();aux.observe('screen',v,None,j)
        v2=PublicView('later',v.messages,v.images);r=aux.observe('screen',v2,None,j)
        self.assertEqual(aux.calls,1);self.assertEqual(r[0]['status'],'exact_input_reuse');self.assertEqual(r[0]['source']['observation_id'],'later')
    def test_failed_condition_is_not_automatically_retried(self):
        aux=JevAuxiliary([Client(True)]);j=Journal(self.root/'j');v=view();aux.observe('screen',v,None,j);r=aux.observe('screen',v,None,j)
        self.assertEqual(aux.calls,1);self.assertEqual(r[0]['status'],'preserved_failure_no_retry')
    def test_auxiliary_call_cap_is_separate_and_enforced(self):
        aux=JevAuxiliary([Client()],max_calls=1);r=aux.observe('verify',view(),{'name':'click'},Journal(self.root/'j'))
        self.assertEqual(aux.calls,1);self.assertEqual(sum(x['status']=='auxiliary_budget_exhausted' for x in r),2)
    def test_main_invalid_verdict_still_rejected(self):
        from defense.core import ValidationError
        c=JevAssistedController(lambda *_:{},Journal(self.root/'j'),jev_auxiliary=JevAuxiliary([Client()]),limits=Limits(max_format_retries=0))
        with self.assertRaises(ValidationError):c.inspect('screen',view())
    def test_reference_not_presented_as_current(self):
        aux=JevAuxiliary([Client()]);v=view();v=PublicView(v.observation_id,v.messages,(v.images[0],VisibleImage(v.images[0].raw,'reference')))
        rows=aux.observe('history_report',v,None,Journal(self.root/'j'))
        self.assertTrue(any(r['source']['role']=='reference' for r in rows));self.assertTrue(all(r['source']['history_verified']==False for r in rows))
    def check_transport(self,corrupt=False):
        token=self.root/'token';token.write_text('local-test-only')
        def response(request,**kwargs):
            req=json.loads(request.data);keys=list(QUESTIONS['readability'][1])
            out={'status':'ok','model':'jev_style','revision':REVISIONS['jev_style'],'image_sha256':req['image_sha256'] if not corrupt else 'wrong','request_id':req['request_id'],'request_sha256':hashlib.sha256(request.data).hexdigest(),'probabilities':{k:1/len(keys) for k in keys},'answer':keys[0]}
            return io.BytesIO(json.dumps(out).encode())
        with patch('urllib.request.urlopen',side_effect=response):return LocalDecisionClient('jev_style','http://127.0.0.1:18221',token).decide(view().images[0],'readability',{})
    def test_real_client_parses_and_binds_response(self):self.assertEqual(self.check_transport()['status'],'ok')
    def test_real_client_rejects_wrong_image_binding(self):
        with self.assertRaises(ValueError):self.check_transport(True)
    def test_late_foreign_gpu_process_disables_admission(self):
        with patch('subprocess.check_output',return_value='GPU-a, 123\nGPU-a, 456\n'):
            self.assertFalse(resource_snapshot('GPU-a',123)['exclusive_gpu'])
    def test_other_gpu_process_does_not_block_owned_card(self):
        with patch('subprocess.check_output',return_value='GPU-a, 123\nGPU-b, 456\n'):
            self.assertTrue(resource_snapshot('GPU-a',123)['exclusive_gpu'])
    def test_absent_model_process_does_not_claim_ownership(self):
        with patch('subprocess.check_output',return_value='GPU-a, 456\n'):
            self.assertFalse(resource_snapshot('GPU-a',123)['exclusive_gpu'])
if __name__=='__main__':unittest.main()
