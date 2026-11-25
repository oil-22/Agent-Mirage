import base64,copy,json,sys,unittest,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'runtime-package'),str(HERE/'runtime-package/release')]
from protocol import RunBudget

class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((HERE/'runtime-package/plan.json').read_bytes())
        self.b=RunBudget(self.plan);self.run=self.plan['queue'][0]['run_id']
    def body(self,**kw):return {'trajectory_id':self.run,'request_id':uuid.uuid4().hex,**kw}
    def begin(self):self.b.admit('/begin',self.body())
    def infer(self,op='actor',index=1,decision=1):return self.body(decision_index=decision,attempt_index=index,payload={'operation':op})
    def test_no_infer_before_begin(self):
        with self.assertRaises(AssertionError):self.b.admit('/',self.infer())
    def test_duplicate_begin_rejected(self):
        v=self.body();self.b.admit('/begin',v)
        with self.assertRaises(AssertionError):self.b.admit('/begin',v)
    def test_no_observer_arm_cannot_infer_auxiliary(self):
        self.begin()
        with self.assertRaises(AssertionError):self.b.admit('/evidence',self.infer('evidence'))
    def test_order_and_no_counter_gap(self):
        self.begin()
        with self.assertRaises(AssertionError):self.b.admit('/',self.infer(index=2))
        v=self.infer();v['trajectory_id']='foreign'
        with self.assertRaises(AssertionError):self.b.admit('/',v)
        self.b.admit('/',self.infer())
        self.assertEqual(self.b.counts['actor'],1)
    def test_native_caps_unchanged(self):
        self.begin()
        for i in range(1,71):self.b.admit('/',self.infer(index=i))
        with self.assertRaises(AssertionError):self.b.admit('/',self.infer(index=71))
        for i in range(1,141):self.b.admit('/',self.infer('judge',i))
        with self.assertRaises(AssertionError):self.b.admit('/',self.infer('judge',141))
    def test_step_cap(self):
        self.begin()
        for d in [0,51,True]:
            with self.assertRaises(AssertionError):self.b.admit('/',self.infer(decision=d))
    def test_technical_failure_is_terminal(self):
        self.begin();self.b.admit('/end',self.body(status='technical_failure',terminal_receipt_sha256='1'*64))
        self.assertTrue(self.b.terminal)
        with self.assertRaises(AssertionError):self.b.admit('/begin',self.body())
    def test_completed_runs_advance_once(self):
        self.begin();self.b.admit('/end',self.body(status='completed',terminal_receipt_sha256='1'*64))
        self.assertEqual(self.b.index,1);self.assertFalse(self.b.terminal)
        with self.assertRaises(AssertionError):self.b.admit('/begin',self.body())

class WiringTests(unittest.TestCase):
    def test_real_actor_interface_inherited(self):
        from gui_transport import GUIQwen
        from defense.http_backend import RemoteQwen
        self.assertIs(GUIQwen.actor,RemoteQwen.actor);self.assertIs(GUIQwen.judge,RemoteQwen.judge)
    def test_both_arms_preserve_full_messages_and_current_image(self):
        import io
        from PIL import Image
        from defense.core import PublicView,VisibleImage
        from image_evidence import canonical,digest,SCHEMA_VERSION
        from evidence_observer import NeutralEvidenceObserver
        f=io.BytesIO();Image.new('RGB',(17,13),'white').save(f,format='PNG');raw=f.getvalue()
        msgs=[{'role':'system','content':'Original system'},{'role':'assistant','content':'Original complete history'},
              {'role':'user','content':[{'type':'text','text':'Current task, not for auxiliary'},
              {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(raw).decode()}}]},
              {'role':'user','content':'Original trailing recovery correction'}]
        view=PublicView('fresh',copy.deepcopy(msgs),(VisibleImage(raw),));body={'messages':msgs,'max_tokens':2048,'temperature':0}
        reading={'schema_version':SCHEMA_VERSION,'coordinate_space':'normalized_1000',
            'frame':{'kind':'unknown','summary':'CPU mock only','limitations':[]},'text_spans':[],'elements':[],'uncertain_regions':[]}
        requests=[]
        def backend(request):
            requests.append(request)
            self.assertNotIn('Current task',json.dumps(request));self.assertNotIn('Original complete history',json.dumps(request))
            return {'request_sha256':digest(canonical(request)),'image_sha256':digest(raw),'model':request['model'],
                    'revision':request['revision'],'raw_output':json.dumps(reading),'natural_eos':True}
        for enabled in [False,True]:
            obs=NeutralEvidenceObserver(backend,model='mock',revision='f'*40,enabled=enabled)
            actual=obs.augment(copy.deepcopy(body),view)
            self.assertEqual(actual['messages'][:2],msgs[:2]);self.assertEqual(actual['messages'][-1],msgs[-1])
            self.assertEqual(actual['messages'][2]['content'][:-1],msgs[2]['content'])
            self.assertEqual(actual['max_tokens'],2048);self.assertEqual(body['messages'],msgs)
        self.assertEqual(len(requests),1)

if __name__=='__main__':unittest.main()
