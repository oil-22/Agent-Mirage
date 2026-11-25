"""Bounded GUI-only transport wrapper; native actor/judge methods stay inherited."""
import copy,json,uuid
import requests
from defense.core import InferenceFailure,canonical,digest
from defense.http_backend import RemoteQwen
from image_observer import wire


class OnlineQwen(RemoteQwen):
    def set_run(self,trajectory_id,journal):
        self.trajectory_id,self.log=trajectory_id,journal
        self.context={'trajectory_id':trajectory_id,'decision_index':0,'observer_calls':0,'journal':journal}
        self.attempts={'actor':0,'judge':0};self.active=False

    def _post(self,path,body,kind):
        raw=wire(body)
        self.log.append(kind+'_request',{'path':path,'body':copy.deepcopy(body),
            'wire_utf8':raw.decode(),'wire_sha256':digest(raw)})
        try:r=requests.post(self.url.rstrip('/')+path,data=raw,
            headers={**self.headers,'Content-Type':'application/json'},timeout=(15,1800))
        except requests.RequestException as error:
            self.log.append(kind+'_transport_failure',{'error':str(error),'no_automatic_retry':True})
            raise InferenceFailure(str(error))from error
        try:data=r.json()
        except ValueError as error:raise InferenceFailure('Non-JSON bounded GUI transport response')from error
        self.log.append(kind+'_response',{'http_status':r.status_code,'body':copy.deepcopy(data),
            'response_sha256':digest(canonical(data))})
        if not r.ok:raise InferenceFailure(json.dumps({'http_status':r.status_code,'response':data,'semantic_mirage':None}))
        if data.get('external_wire_sha256')!=digest(raw)or data.get('request_id')!=body['request_id']:
            raise InferenceFailure('Actual online wire/request ID response binding mismatch')
        return data

    def begin_run(self):
        data=self._post('/begin',{'trajectory_id':self.trajectory_id,'request_id':uuid.uuid4().hex},'online_run_begin')
        self.active=True
        return data

    def end_run(self,status,terminal_receipt_sha256):
        if not self.active:return
        data=self._post('/end',{'trajectory_id':self.trajectory_id,'request_id':uuid.uuid4().hex,
            'status':status,'terminal_receipt_sha256':terminal_receipt_sha256},'online_run_end')
        self.active=False
        return data

    def set_decision(self,index):
        if type(index)is not int or not 1<=index<=50:raise InferenceFailure('Original decision cap exceeded')
        self.context['decision_index']=index

    def call(self,body):
        op=body['operation'];self.attempts[op]+=1
        cap={'actor':70,'judge':140}[op]
        if not self.active or not 1<=self.attempts[op]<=cap or not 1<=self.context['decision_index']<=50:
            raise InferenceFailure('Native GUI role/run/budget context unavailable')
        envelope={'trajectory_id':self.trajectory_id,'decision_index':self.context['decision_index'],
            'attempt_index':self.attempts[op],'request_id':uuid.uuid4().hex,'payload':body}
        data=self._post('/',envelope,'actual_primary_wire')
        self.calls.append({k:v for k,v in data.items()if k not in {'text','verdict'}})
        if data.get('payload_sha256')!=digest(canonical(body)):
            raise InferenceFailure('Original full native payload response binding mismatch')
        return data


assert OnlineQwen.actor is RemoteQwen.actor and OnlineQwen.judge is RemoteQwen.judge
