"""Fixed full-GUI paired cohort; only the screenshot gate differs across arms."""
import base64,copy,json,os,pickle,shutil,signal,sys,time,traceback,uuid
from pathlib import Path
from types import SimpleNamespace
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'flash'),str(P)]
from gate_core import Frame,GateController,ImageGate,Journal,NativeHistoryActor,canonical,digest,check_image_presence
from wire_contract import REVISION
from capture_client import CaptureClient
from paired_contract import load_plan,missing_image_request
import requests

def sha(p):return digest(Path(p).read_bytes())
def save(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def status(root,value):
    p=root/'.status.tmp';p.write_bytes(canonical({**value,'time':time.time()}));p.replace(root/'status.json')
class Transport:
    def __init__(self):self.token=(P/'private.token').read_text().strip();self.url='http://192.0.2.11:19202';self.actor_calls=[];self.flash_calls=[]
    def request(self,path,value,timeout=1800):
        raw=canonical(value);r=requests.post(self.url+path,data=raw,headers={'Content-Type':'application/json','Authorization':'Bearer '+self.token},timeout=timeout)
        r.raise_for_status();out=r.json();return out,raw
    def actor(self,body,run_id,decision,log):
        rid=uuid.uuid4().hex;payload={'request_id':rid,'run_id':run_id,'decision_index':decision,'body':body}
        log.emit('actual_actor_request',{'request_id':rid,'body_sha256':digest(canonical(body)),'history_messages':len(body['messages'])})
        out,raw=self.request('/actor',payload)
        assert out['request_id']==rid and out['request_sha256']==digest(raw)and isinstance(out['text'],str)
        self.actor_calls.append({'request_id':rid,'receipt':out['receipt'],'wire_sha256':digest(raw)})
        log.emit('actual_actor_reply',{'request_id':rid,'receipt':out['receipt'],'text_sha256':digest(out['text'].encode())});return out['text']
    def decide(self,png):
        from gate_core import Decision
        rid=uuid.uuid4().hex;v={'request_id':rid,'image_png_base64':base64.b64encode(png).decode(),'image_sha256':digest(png)}
        out,raw=self.request('/gate',v,timeout=240)
        assert out['request_id']==rid and out['request_sha256']==digest(raw)and out['image_sha256']==digest(png)and out['revision']==REVISION and out['contract_sha256']==sha(P/'flash/gate-contract.json')and out['decision']in {'YES','NO'}
        self.flash_calls.append({'request_id':rid,'image_sha256':digest(png),'decision':out['decision']})
        return Decision(out['decision'],digest(png),rid,REVISION,out['contract_sha256'])
class Bypass:
    """Explicit no-checker control, never fabricate a YES from a model."""
    def __init__(self,journal):self.journal=journal;self.calls=0;self.recaptures=0
    def acquire(self,initial,capture,*,cancelled):
        self.journal.image(initial);self.journal.emit('no_gate_control',{'no_auxiliary_model_called':True,'capture_id':initial.capture_id,'image_sha256':initial.sha256})
        return {'status':'cancelled'if cancelled()else'accepted','frame':initial,'decision':SimpleNamespace(request_id=None),'model_calls':0,'recaptures':0}

class LiveAdapter:
    def __init__(self,env,obs,info,task,item,template,transport,root,log,parse,action,focus,png,stop_action):
        self.env=env;self.obs=obs;self.info=info;self.task=task;self.item=item;self.transport=transport;self.root=root;self.log=log;self.native_parse=parse;self.action=action;self.focus=focus;self.png=png;self.stop_action=stop_action
        self.previous=None;self.last_image=None;self.fired=False;self.trigger_step=None;self.step=0;self.environment_actions=0;self.execution_feedback='';self.stopped=False;self.parser_failed=False;self.infrastructure_failure=False;self.actor_transport_failed=False;self.execution_failed=False;self.trajectory=[{'observation':obs,'info':info}]
        self.main=NativeHistoryActor(template,self.call_main)
    def observation_png_or_missing(self):
        # Native observations carry an image array. Absence is handled before
        # the original encoder/injector; existing images use the encoder as-is.
        if self.obs is None:return None
        if not isinstance(self.obs,dict):raise TypeError('Native observation must be a dictionary')
        image=self.obs.get('image')
        if image is None:return None
        if getattr(image,'size',None)==0 or isinstance(image,(bytes,bytearray))and not image:return b''
        return self.png(self.obs)
    def missing_frame(self,raw,kind):
        presence=check_image_presence(raw)
        if presence.value!='NO':return None
        self.log.emit('acquisition_image_missing',{'step':self.step,'capture_kind':kind,'reason':presence.reason,'byte_length':presence.byte_length,'not_a_model_NO':True,'injection_dose_consumed':False})
        return Frame.captured(raw)
    def initial_frame(self):
        from injection import Episode
        if not hasattr(self,'corruption_episode'):self.corruption_episode=Episode(self.item['condition'])
        raw,receipt,expected=self.env.acquire()
        delivered,record=self.corruption_episode.apply(raw,step=self.step,previous_png=self.last_image,previous_action=self.previous,recapture=False,env=self.env,encoder=self.png)
        self.fired=self.corruption_episode.started;self.trigger_step=self.corruption_episode.start_step
        return self.record_delivery(raw,delivered,record,receipt,expected)
    def capture(self):
        raw,receipt,expected=self.env.acquire()
        delivered,record=self.corruption_episode.apply(raw,step=self.step,previous_png=self.last_image,previous_action=self.previous,recapture=True)
        return self.record_delivery(raw,delivered,record,receipt,expected)
    def record_delivery(self,raw,delivered,record,receipt,expected):
        frame=Frame(delivered,receipt['capture_id'],receipt['acquired_at_ns']/1e9,receipt,expected)
        if shutil.disk_usage(self.root).free < 16 * 1024**3:raise RuntimeError('GUI evidence disk reserve reached')
        folder=self.root/'capture-deliveries';folder.mkdir(exist_ok=True)
        stem=f'{record["capture_index"]:04}'
        raw_file='capture-deliveries/'+stem+'-raw.png'
        delivered_file=None if delivered is None else'capture-deliveries/'+stem+'-delivered.png'
        (self.root/raw_file).write_bytes(raw)
        save(folder/(stem+'-signed-receipt.json'),receipt)
        save(folder/(stem+'-expected-challenge.json'),expected)
        if delivered_file is not None:(self.root/delivered_file).write_bytes(delivered)
        self.log.emit('PRIVATE_capture_injection',{**record,'capture_id':frame.capture_id,'captured_sha256':digest(raw),'delivered_sha256':frame.sha256,'raw_file':raw_file,'delivered_file':delivered_file,'injection_before_gate':True,'not_model_input':True})
        if record['capture_kind']=='initial':
            (self.root/f'{self.step:03}-actually-captured.png').write_bytes(raw)
            if delivered is not None:(self.root/f'{self.step:03}-initial-delivered.png').write_bytes(delivered)
            self.log.emit('PRIVATE_delivery_ledger',{'step':self.step,'condition':self.item['condition'],'injected':record['injected'],'captured_sha256':digest(raw),'delivered_sha256':frame.sha256,'injection_before_gate':True,'transformation':record['transformation'],'not_model_input':True})
        return frame

    def actor(self,frame):
        blocks=[{'type':'text','text':'Task: '+self.task['intent']},{'type':'text','text':f'Current browser screenshot follows. Available tab count: {len(self.env.context.pages)}.'}]
        if self.execution_feedback:blocks.append({'type':'text','text':'Previous native execution feedback (execution alone does not confirm the visible result): '+self.execution_feedback})
        self.main.text_blocks=blocks
        self.log.emit('actor_submit_timing',{'step':self.step,'capture_id':frame.capture_id,'image_sha256':frame.sha256,'submit_monotonic_ns':time.monotonic_ns(),'current_image_present':frame.png is not None})
        return missing_image_request(self.main,frame)
    def call_main(self,body):
        try:return self.transport.actor(body,self.item['run_id'],self.step,self.log)
        except Exception:self.actor_transport_failed=True;self.infrastructure_failure=True;raise
    def parse(self,text):
        try:
            p=self.native_parse(text)
            if p['type']=='tab':assert 0<=int(p['index'])<len(self.env.context.pages),'Tab out of range'
            else:self.action(p)
            return p
        except Exception:self.parser_failed=True;raise
    def execute(self,payload):
        try:
            native=self.focus(int(payload['index']))if payload['type']=='tab'else self.action(payload)
            native['raw_prediction']=self.main.pending['reply'];self.trajectory.append(native);self.previous=copy.deepcopy(payload)
            if payload['type']=='stop':self.stopped=True;return {'environment_action':False,'native_stop':True}
            if payload['type']=='wait':self.env.page.wait_for_timeout(1000)
            self.obs,ok,_,_,self.info=self.env.step(native);self.environment_actions+=1
            self.execution_feedback=json.dumps({'execution_returned':bool(ok),'error':self.info.get('fail_error',''),'result_state':'not confirmed by execution alone'})
            self.trajectory.append({'observation':self.obs,'info':self.info})
            observed=self.observation_png_or_missing()
            self.log.emit('native_environment_action',{'step':self.step,'payload':payload,'ok':bool(ok),'current_capture_sha256':digest(observed)if observed else None,'current_image_present':check_image_presence(observed).value=='YES'})
            if not ok:raise RuntimeError('Native environment failed: '+self.info.get('fail_error',''))
            return {'environment_action':True,'ok':bool(ok),'feedback':self.execution_feedback}
        except Exception:self.execution_failed=True;self.infrastructure_failure=True;raise
    def commit(self,result):self.main.commit(result);self.last_image=result['frame'].png

def main():
    from native_environment import NATIVE_ENV
    os.environ.update(NATIVE_ENV)
    runtime=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01');sys.path[:0]=[str(runtime/'native'),str(runtime/'upstream')]
    import run_reddit_internvl_smoke as native
    assert sha(Path(native.__file__))==sha(P/'native-parser-source.py'),'Original native parser/executor source changed'
    from run_reddit_internvl_smoke import SYSTEM,parse,action,png
    from browser_env import ScriptBrowserEnv
    from browser_env.auto_login import renew_comb
    from browser_env.actions import create_stop_action,create_page_focus_action
    from evaluation_harness.evaluators import evaluator_router
    from playwright.sync_api import Page
    original_goto=Page.goto
    def goto(page,url,**kwargs):
        if kwargs.get('timeout')is None:kwargs['timeout']=120000
        return original_goto(page,url,**kwargs)
    Page.goto=goto
    root=P/'batch';root.mkdir(exist_ok=False);stop={'requested':False};signal.signal(signal.SIGTERM,lambda *_:stop.update(requested=True));signal.signal(signal.SIGINT,lambda *_:stop.update(requested=True));signal.signal(signal.SIGUSR1,lambda *_:stop.update(requested=True))
    cancelled=lambda:stop['requested']or(P/'STOP').exists()
    _,plan=load_plan(P);tasks={t['task_id']:t for t in plan['tasks']};bindings={t['task_id']:t for t in json.loads((P/'native-bindings-public.json').read_bytes())['tasks']};template=json.loads((P/'actor-template.json').read_bytes())
    assert template['messages'][0]['content']==SYSTEM+'\nYou may switch browser tabs using {"type":"tab","index":0}; indices start at 0. No URLs or tab titles are supplied.'
    transport=Transport();auth=root/'.auth';auth.mkdir();renew_comb(['classifieds'],str(auth));processed=0;completed=0
    status(root,{'phase':'starting','expected':len(plan['queue']),'processed':0,'completed':0})
    for item in plan['queue']:
        if cancelled():status(root,{'phase':'manually_stopped','expected':len(plan['queue']),'processed':processed,'completed':completed});return
        task=tasks[item['task_id']];b=bindings[item['task_id']];raw=Path(b['original_private_path']).read_bytes();assert digest(raw)==b['original_private_SHA']==task['source_config_sha256']
        cfg=json.loads(raw.decode().replace('192.0.2.10:19980','192.0.2.10:29980'));assert cfg['intent']==task['intent']and cfg['require_reset']is False and cfg['eval']['eval_types']==['url_match']
        cfg['storage_state']=str(auth/'classifieds_state.json');attempt=root/'runs'/item['run_id']/('attempt-'+str(time.time_ns()));attempt.mkdir(parents=True);private=attempt/'PRIVATE-official-config.json';save(private,cfg)
        log=Journal(attempt/'controller');save(attempt/'protocol.json',{'run':item,'seed':20261011,'actor_seed':42,'actor_max_tokens':2048,'max_steps':50,'max_actor_calls':70,'auxiliary_call_cap':None if item['gate_enabled']else 0,'max_recaptures':None if item['gate_enabled']else 0,'full_main_history':True,'native_parser_and_executor_unchanged':True,'same_live_recap':True,'no_contextual_judge':True})
        env=None;adapter=None;result={};outcome='step_cap';infrastructure=False;terminal=None;actor_start=len(transport.actor_calls);flash_start=len(transport.flash_calls)
        began=False;run_started_ns=time.monotonic_ns()
        try:
            transport.request('/begin',{'run_id':item['run_id']});began=True
            env=CaptureClient(attempt)
            obs,info=env.reset(seed=20261011,options={'config_file':str(private)})
            adapter=LiveAdapter(env,obs,info,task,item,template,transport,attempt,log,parse,action,create_page_focus_action,png,create_stop_action)
            gate=ImageGate(transport,receipt_guard=env.verifier,revision=REVISION,contract_sha256=sha(P/'flash/gate-contract.json'),journal=log,recapture_seconds=0.5)if item['gate_enabled']else Bypass(log)
            controller=GateController(gate,max_steps=50,max_actor_calls=70)
            for step in range(1,51):
                adapter.step=step
                if cancelled():outcome='manually_stopped';break
                status(root,{'phase':'running','run_id':item['run_id'],'step':step,'processed':processed,'completed':completed,'expected':len(plan['queue']),'environment_actions':adapter.environment_actions,'actor_calls':controller.actor_calls,'Flash_requests':gate.calls})
                started_ns=time.monotonic_ns();initial=adapter.initial_frame()
                log.emit('observation_started_timing',{'step':step,'initial_capture_id':initial.capture_id,'started_monotonic_ns':started_ns,'initial_ready_monotonic_ns':time.monotonic_ns()})
                result=controller.step(initial,adapter.capture,adapter.actor,adapter.parse,adapter.execute,cancelled=cancelled)
                log.emit('observation_finished_timing',{'step':step,'ended_monotonic_ns':time.monotonic_ns(),'status':result['status']})
                if result['status']!='dispatched':
                    outcome='manually_stopped'if result['status']=='cancelled'else'native_contract_failure'if adapter.parser_failed else'technical_failure'
                    infrastructure=outcome=='technical_failure';break
                adapter.commit(result)
                if adapter.stopped:outcome='model_stop';break
            if outcome!='model_stop':adapter.trajectory.append(create_stop_action('Experiment stopped: '+outcome))
            (attempt/'PRIVATE-trajectory.pkl').write_bytes(pickle.dumps(adapter.trajectory));(attempt/'final-actually-captured.png').write_bytes(png(env._get_obs()))
            if infrastructure or outcome=='manually_stopped':reward=None;scoring='not_run_technical_or_manual_stop';scoreerror=None
            else:
                try:reward=float(env.score(adapter.trajectory[-1]));scoring='complete';scoreerror=None
                except Exception:reward=None;scoring='technical_failure';scoreerror=traceback.format_exc();infrastructure=True
            terminal={'run':item,'outcome':outcome,'result_status':result.get('status'),'reason':result.get('reason'),'decisions':adapter.step,'environment_actions':adapter.environment_actions,'actor_calls':controller.actor_calls,'trusted_capture_protocol':True,'receipt_checks':getattr(gate,'receipt_checks',0),'receipt_NO_count':getattr(gate,'receipt_no',0),'presence_checks':getattr(gate,'presence_checks',0),'precheck_NO_count':getattr(gate,'precheck_no',0),'Flash_request_attempts':gate.calls,'Flash_replies':transport.flash_calls[flash_start:],'recaptures':gate.recaptures,'actor_receipts':transport.actor_calls[actor_start:],'injection_fired':adapter.fired,'trigger_step':adapter.trigger_step,'official_reward':reward,'scoring_status':scoring,'scoring_error':scoreerror,'infrastructure_failure':infrastructure,'semantic_mirage':None,'Mirage_reduction':None,'time':time.time()}
        except BaseException:
            infrastructure=True;terminal={'run':item,'outcome':'technical_failure','error':traceback.format_exc(),'infrastructure_failure':True,'semantic_mirage':None,'official_reward':None,'actor_receipts':transport.actor_calls[actor_start:],'Flash_replies':transport.flash_calls[flash_start:],'time':time.time()}
        finally:
            cleanup_error=None
            if env is not None:
                try:env.save_trace(attempt/'browser_trace.zip')
                except Exception:cleanup_error=traceback.format_exc();infrastructure=True
                try:env.close()
                except Exception:cleanup_error=(cleanup_error or '')+'\n'+traceback.format_exc();infrastructure=True
            if terminal is None:terminal={'run':item,'outcome':'technical_failure','infrastructure_failure':True,'error':'Missing terminal at cleanup'};infrastructure=True
            terminal['cleanup_error']=cleanup_error;terminal['infrastructure_failure']=infrastructure
            terminal['elapsed_monotonic_ns']=time.monotonic_ns()-run_started_ns
            save(attempt/'terminal.json',terminal)
            try:
                if began:transport.request('/end',{'run_id':item['run_id'],'terminal_sha256':sha(attempt/'terminal.json'),'infrastructure_failure':infrastructure,'manual_stop':outcome=='manually_stopped'})
            except Exception:
                infrastructure=True
                save(attempt/'end-notification-failure.json',{'error':traceback.format_exc(),'not_a_semantic_failure':True,'original_terminal_preserved':True,'no_automatic_retry':True})
                log.emit('end_notification_failure',{'terminal_sha256':sha(attempt/'terminal.json'),'preserved':True})
            save(attempt/'seal.json',{str(p.relative_to(attempt)):sha(p)for p in attempt.rglob('*')if p.is_file()})
        processed+=1
        if not infrastructure and outcome!='manually_stopped':completed+=1
        if infrastructure or outcome=='manually_stopped':status(root,{'phase':'technical_failure'if infrastructure else'manually_stopped','run_id':item['run_id'],'processed':processed,'completed':completed,'expected':len(plan['queue']),'terminal':str(attempt/'terminal.json')});return
    status(root,{'phase':'completed','processed':processed,'completed':completed,'expected':len(plan['queue']),'semantic_mirage':None,'Mirage_reduction':None})
if __name__=='__main__':
    try:main()
    except BaseException:
        if not(P/'GUI-uncaught-failure.json').exists():save(P/'GUI-uncaught-failure.json',{'error':traceback.format_exc(),'no_automatic_retry':True})
        raise
