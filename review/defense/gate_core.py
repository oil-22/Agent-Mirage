"""Flash-only observation gate. The checker receives bytes, never agent context."""
import base64,copy,hashlib,json,os,time,uuid
from dataclasses import dataclass
from pathlib import Path

def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

@dataclass(frozen=True)
class Frame:
    png:bytes|None
    capture_id:str
    captured_at:float
    receipt:dict|None=None
    expected:dict|None=None
    def __post_init__(self):
        if not isinstance(self.capture_id,str) or not self.capture_id:raise ValueError('Fresh capture ID required')
        if self.png is not None and not isinstance(self.png,bytes):raise TypeError('Immutable original image bytes required')
    @classmethod
    def captured(cls,png):return cls(png,uuid.uuid4().hex,time.time())
    @classmethod
    def from_file(cls,path):
        """Missing file becomes a missing frame; other I/O failures stay errors."""
        try:png=Path(path).read_bytes()
        except FileNotFoundError:png=None
        return cls.captured(png)
    @property
    def sha256(self):return None if self.png is None else digest(self.png)

@dataclass(frozen=True)
class Decision:
    value:str
    image_sha256:str
    request_id:str
    revision:str
    contract_sha256:str

@dataclass(frozen=True)
class ImagePresenceDecision:
    value:str
    reason:str
    byte_length:int

def check_image_presence(png):
    """Deterministic existence check; image quality remains Flash's decision."""
    if png is None:return ImagePresenceDecision('NO','missing_image',0)
    if not isinstance(png,bytes):raise TypeError('Immutable original image bytes required')
    if not png:return ImagePresenceDecision('NO','empty_image_data',0)
    return ImagePresenceDecision('YES','image_data_present',len(png))

class Journal:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=False)
        self.seq=0;self.head='0'*64
    def emit(self,kind,data):
        row={'seq':self.seq,'previous':self.head,'time':time.time(),'kind':kind,'data':data}
        row['sha256']=digest(canonical(row))
        with (self.root/'events.jsonl').open('ab')as f:f.write(canonical(row)+b'\n');f.flush();os.fsync(f.fileno())
        self.seq+=1;self.head=row['sha256']
    def image(self,frame):
        if frame.png is not None:
            p=self.root/(frame.sha256+'.png')
            if p.exists():
                if p.read_bytes()!=frame.png:raise ValueError('Image binding collision')
            else:
                with p.open('xb')as f:f.write(frame.png)
        self.emit('capture',{'capture_id':frame.capture_id,'captured_at':frame.captured_at,'image_sha256':frame.sha256})

class ImageGate:
    """Until YES or cancellation; transport/model faults are separate terminal states.

    There is no total model-call cap on this continuous gate. The caller supplies an
    explicit cancellation predicate; each NO leads to a new live capture.
    """
    def __init__(self,checker,*,receipt_guard,revision,contract_sha256,journal,recapture_seconds=0.5,sleeper=time.sleep):
        if recapture_seconds<0:raise ValueError('Negative capture interval')
        self.checker=checker;self.revision=revision;self.contract_sha256=contract_sha256
        self.journal=journal;self.recapture_seconds=recapture_seconds;self.sleeper=sleeper
        self.calls=0;self.recaptures=0;self.presence_checks=0;self.precheck_no=0
        self.receipt_guard=receipt_guard;self.receipt_checks=0;self.receipt_no=0
    def acquire(self,initial,capture,*,cancelled):
        if not isinstance(initial,Frame):raise TypeError('Initial capture must be a Frame')
        frame=initial;seen=set();calls_start=self.calls;recaps_start=self.recaptures
        presence_start=self.presence_checks;precheck_no_start=self.precheck_no
        def finish(status,reason=None,decision=None):
            row={'status':status,'reason':reason,'model_calls':self.calls-calls_start,'recaptures':self.recaptures-recaps_start,'presence_checks':self.presence_checks-presence_start,'precheck_NO_count':self.precheck_no-precheck_no_start,'receipt_checks':self.receipt_checks,'receipt_NO_count':self.receipt_no,'last_capture_id':frame.capture_id,'last_image_sha256':frame.sha256,'semantic_mirage':None}
            self.journal.emit('gate_terminal',row)
            return {**row,'frame':frame if status=='accepted'else None,'decision':decision}
        while True:
            if cancelled():return finish('cancelled','manual_stop')
            if not isinstance(frame,Frame):raise TypeError('Capture callback must return a Frame')
            if frame.capture_id in seen:return finish('technical_failure','capture_callback_reused_an_old_capture_id')
            seen.add(frame.capture_id);self.journal.image(frame)
            presence=check_image_presence(frame.png);self.presence_checks+=1
            self.journal.emit('image_presence_check',{'capture_id':frame.capture_id,'image_sha256':frame.sha256,'decision':presence.value,'reason':presence.reason,'byte_length':presence.byte_length,'source':'image_presence_precheck','not_a_model_decision':True})
            if presence.value=='NO':
                self.precheck_no+=1
                self.journal.emit('precheck_decision',{'capture_id':frame.capture_id,'image_sha256':frame.sha256,'decision':'NO','reason':presence.reason,'source':'image_presence_precheck','Flash_called':False,'not_a_model_NO':True})
                self.journal.emit('missing_capture',{'capture_id':frame.capture_id,'reason':presence.reason,'not_a_model_NO':True})
            else:
                self.receipt_checks+=1
                verified=self.receipt_guard.check(frame.png,frame.receipt,expected=frame.expected)
                self.journal.emit('capture_receipt_decision',{'capture_id':frame.capture_id,'image_sha256':frame.sha256,'decision':verified.value,'reason':verified.reason,'expected':frame.expected,'receipt':frame.receipt,'source':'trusted_capture_receipt','Flash_called':False,'not_a_model_NO':verified.value=='NO'})
                if verified.value=='NO':self.receipt_no+=1
                else:
                    self.calls+=1
                    try:
                        # This is deliberately the entire checker interface.
                        decision=self.checker.decide(frame.png)
                        if not isinstance(decision,Decision) or decision.value not in {'YES','NO'}:raise ValueError('Invalid binary decision')
                        if decision.image_sha256!=frame.sha256 or decision.revision!=self.revision or decision.contract_sha256!=self.contract_sha256:raise ValueError('Checker response belongs to a different image/model/contract')
                    except Exception as e:
                        self.journal.emit('checker_failure',{'capture_id':frame.capture_id,'type':type(e).__name__,'message':str(e),'not_a_model_NO':True,'no_automatic_transport_retry':True})
                        return finish('technical_failure','checker_failure')
                    self.journal.emit('gate_decision',{'capture_id':frame.capture_id,'image_sha256':frame.sha256,'decision':decision.value,'request_id':decision.request_id,'revision':decision.revision,'contract_sha256':decision.contract_sha256})
                    if cancelled():return finish('cancelled','manual_stop_after_current_inference')
                    if decision.value=='YES':return finish('accepted',decision=decision)
            # NO and missing-image recovery both capture the SAME live environment.
            # No scrolling, back-navigation, click, page reset or image synthesis.
            self.journal.emit('recapture_requested',{'from_capture_id':frame.capture_id,'wait_seconds':self.recapture_seconds,'index':self.recaptures-recaps_start+1})
            deadline=time.monotonic()+self.recapture_seconds
            while time.monotonic()<deadline:
                if cancelled():return finish('cancelled','manual_stop')
                self.sleeper(min(0.1,max(0,deadline-time.monotonic())))
            if cancelled():return finish('cancelled','manual_stop')
            try:
                new_frame=capture()
                if not isinstance(new_frame,Frame):raise TypeError('Capture callback must return a Frame')
                frame=new_frame;self.recaptures+=1
            except Exception as e:
                self.journal.emit('capture_failure',{'type':type(e).__name__,'message':str(e)})
                return finish('technical_failure','capture_failed')

class GateController:
    """Call the original actor/parser/executor only after a bound YES frame.

    This new mode has no other vision helper or contextual semantic judge.
    Native actor parameters, complete actor history, parsing and execution are
    provided by their existing adapters and are not rewritten here.
    """
    def __init__(self,gate,*,max_steps=50,max_actor_calls=70):
        self.gate=gate;self.max_steps=max_steps;self.max_actor_calls=max_actor_calls
        self.steps=0;self.actor_calls=0
    def step(self,initial,capture,actor,parse,execute,*,cancelled):
        if self.steps>=self.max_steps:return {'status':'step_budget_exhausted'}
        if self.actor_calls>=self.max_actor_calls:return {'status':'actor_budget_exhausted'}
        self.steps+=1;accepted=self.gate.acquire(initial,capture,cancelled=cancelled)
        if accepted['status']!='accepted':return accepted
        frame=accepted['frame']
        if cancelled():return {'status':'cancelled','reason':'manual_stop_before_actor'}
        self.gate.journal.emit('main_image_forwarded',{'capture_id':frame.capture_id,'image_sha256':frame.sha256,'gate_request_id':accepted['decision'].request_id,'extra_auxiliary_text_in_main_prompt':False})
        self.actor_calls+=1
        try:
            reply=actor(frame)
            if not isinstance(reply,str):raise TypeError('Original native actor reply must be text')
            proposal=parse(reply)
        except Exception as e:
            self.gate.journal.emit('native_actor_or_parser_failure',{'type':type(e).__name__,'message':str(e),'executed':False})
            return {'status':'technical_failure','reason':'native_actor_or_parser_failure'}
        if cancelled():return {'status':'cancelled','reason':'manual_stop_before_execution'}
        try:execution=execute(proposal)
        except Exception as e:
            self.gate.journal.emit('native_execution_failure',{'type':type(e).__name__,'message':str(e)})
            return {'status':'technical_failure','reason':'native_execution_failure'}
        # Dispatch may be STOP, a fixture, or an actual environment action. Only
        # the native execution receipt can establish which one happened.
        self.gate.journal.emit('native_proposal_dispatched',{'capture_id':frame.capture_id,'image_sha256':frame.sha256,'candidate_sha256':digest(reply.encode()),'proposal_unmodified':True,'environment_action':execution.get('environment_action')if isinstance(execution,dict)else None})
        return {'status':'dispatched','candidate':reply,'proposal':proposal,'execution':execution,'frame':frame,'gate':accepted}

class NativeHistoryActor:
    """A full-history actor adapter. Flash receives none of these fields."""
    def __init__(self,template,call,*,past_messages=None,text_blocks=()):
        self.template=copy.deepcopy(template);self.call=call;self.text_blocks=copy.deepcopy(list(text_blocks));self.pending=None
        if not self.template.get('messages') or self.template['messages'][0]['role']!='system':raise ValueError('Original native actor system template required')
        if past_messages is not None and len(template['messages'])!=1:raise ValueError('Supply complete past messages once, without ambiguous duplicate history')
        self.history=copy.deepcopy(template['messages'][1:]if past_messages is None else list(past_messages))
        if any(b.get('type')!='text' for b in self.text_blocks):raise ValueError('Current text blocks must not contain an unchecked image')
    def __call__(self,frame):
        image={'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(frame.png).decode()}}
        body={k:copy.deepcopy(v)for k,v in self.template.items()if k!='messages'}
        body['messages']=[copy.deepcopy(self.template['messages'][0])]+copy.deepcopy(self.history)+[{'role':'user','content':copy.deepcopy(self.text_blocks)+[image]}]
        original=copy.deepcopy(body);reply=self.call(body)
        if body!=original:raise ValueError('Actor transport mutated the complete native request/history')
        self.pending={'body':original,'reply':reply,'frame_sha256':frame.sha256}
        return reply
    def commit(self,result):
        if result.get('status')!='dispatched' or self.pending is None or result['candidate']!=self.pending['reply']:raise ValueError('Only the actual parsed/dispatched exchange may be committed')
        if result['frame'].sha256!=self.pending['frame_sha256']:raise ValueError('Committed frame changed')
        self.history=copy.deepcopy(self.pending['body']['messages'][1:])+[{'role':'assistant','content':self.pending['reply']}]
        self.pending=None
