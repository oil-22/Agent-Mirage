"""Original RemoteQwen actor/judge interface with sealed bounded transport."""
import base64, copy, json, uuid
from pathlib import Path
import requests
from defense.core import InferenceFailure, canonical, digest
from defense.http_backend import RemoteQwen
from evidence_observer import NeutralEvidenceObserver

def wire(body): return json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

class GUIQwen(RemoteQwen):
    def set_run(self, run_id, journal):
        self.run_id,self.log=run_id,journal; self.active=False; self.decision=0
        self.attempts={'actor':0,'judge':0,'evidence':0}
        self.context={}

    def _post(self,path,body,kind):
        raw=wire(body)
        self.log.append(kind+'_request',{'path':path,'body':copy.deepcopy(body),'wire_sha256':digest(raw)})
        try:
            r=requests.post(self.url.rstrip('/')+path,data=raw,headers={**self.headers,'Content-Type':'application/json'},timeout=(15,1800))
        except requests.RequestException as e:
            self.log.append(kind+'_transport_failure',{'error':str(e),'no_automatic_retry':True});raise InferenceFailure(str(e)) from e
        self.log.append(kind+'_raw_response',{'http_status':r.status_code,'raw_base64':base64.b64encode(r.content).decode(),'raw_sha256':digest(r.content)})
        try: value=r.json()
        except ValueError as e: raise InferenceFailure('Non-JSON GUI response') from e
        if not r.ok: raise InferenceFailure(json.dumps({'http_status':r.status_code,'response':value,'semantic_mirage':None}))
        if value.get('external_wire_sha256')!=digest(raw) or value.get('request_id')!=body['request_id']:
            raise InferenceFailure('External wire/request identity binding mismatch')
        self.log.append(kind+'_response',{'body':copy.deepcopy(value)})
        return value

    def begin_run(self):
        result=self._post('/begin',{'trajectory_id':self.run_id,'request_id':uuid.uuid4().hex},'online_run_begin')
        self.active=True;return result

    def end_run(self,status,terminal_receipt_sha256):
        if not self.active:return
        result=self._post('/end',{'trajectory_id':self.run_id,'request_id':uuid.uuid4().hex,'status':status,
                                 'terminal_receipt_sha256':terminal_receipt_sha256},'online_run_end')
        self.active=False;return result

    def set_decision(self,index):
        assert type(index)is int and 1<=index<=50
        self.decision=index

    def _call(self,path,payload,op):
        assert self.active and 1<=self.decision<=50
        self.attempts[op]+=1; assert self.attempts[op]<={'actor':70,'judge':140,'evidence':60}[op]
        body={'trajectory_id':self.run_id,'decision_index':self.decision,'attempt_index':self.attempts[op],
              'request_id':uuid.uuid4().hex,'payload':payload}
        result=self._post(path,body,'actual_'+op+'_wire')
        assert result['payload_sha256']==digest(canonical(payload))
        return result

    def call(self,body):
        result=self._call('/',body,body['operation'])
        self.calls.append({k:v for k,v in result.items() if k not in ['text','verdict','evidence_response']})
        return result

    def evidence(self,request):return self._call('/evidence',request,'evidence')['evidence_response']

assert GUIQwen.actor is RemoteQwen.actor and GUIQwen.judge is RemoteQwen.judge

class BoundObserver:
    def __init__(self,model,enabled):
        self.model,self.enabled=model,enabled;self.observer=None;self.client=None;self.failures=[];self.max_calls=60
    @property
    def calls(self):return self.observer.calls if self.observer else 0
    def augment(self,body,view,log):
        if self.observer is None:
            self.observer=NeutralEvidenceObserver(self.model.evidence,model='Qwen/Qwen3.5-9B',
                revision='c202236235762e1c871ad0ccb60c8ee5ba337b9a',enabled=self.enabled,max_calls=60,emit=log.append)
        result=self.observer.augment(body,view)
        self.failures=[v for v in self.observer.terminals.values() if v['status']=='preserved_technical_or_contract_failure_no_retry']
        return result

def validate_launch_inputs(a):
    import hashlib,time
    package=Path(__file__).resolve().parent
    m=json.loads((package/'manifest.json').read_bytes())
    for n,h in m['files'].items():
        assert hashlib.sha256((package/n).read_bytes()).hexdigest()==h,n
    assert a.root==Path(m['GUI_output']) and not a.root.exists()
    assert a.plan==package/'plan.json' and a.actor_template==package/'actor-template.json'
    assert a.model_url==m['model_url'] and a.token_file==package/'private.token'
    assert a.token_file.is_file() and a.token_file.stat().st_mode&0o077==0
    proof=json.loads(a.readiness.read_bytes())
    assert proof['phase']=='ready_gui' and proof['manifest_sha256']==hashlib.sha256((package/'manifest.json').read_bytes()).hexdigest()
    assert 0<=time.time()-proof['time_unix']<=300
    assert proof['source_SHA_matches'] and proof['resource_ownership_actual'] and proof['new_model_calls']==0
