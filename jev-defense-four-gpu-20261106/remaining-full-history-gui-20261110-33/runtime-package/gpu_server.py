"""One-process, original BF16/SDPA 27B + one image-only 9B full-GUI service."""
import argparse,base64,copy,fcntl,gc,hashlib,hmac,io,json,os,signal,sys,time,traceback
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'release'),str(HERE/'grammar-vendor')]
from protocol import RunBudget
from resource_gate import assert_owned_resources,identity,same_identity
from model_runtime import load_runtime,save,sha,canonical,digest
from defense.core import Journal,PublicView,VisibleImage
import image_evidence as contract

def main(a):
    assert sha(a.manifest)==a.manifest_sha256
    package=a.manifest.parent;manifest=json.loads(a.manifest.read_bytes())
    for n,h in manifest['files'].items():assert sha(package/n)==h,n
    assert not a.output.exists();a.output.mkdir()
    root=a.output;me=identity(os.getpid());save(root/'process.json',me)
    plan=json.loads((package/'plan.json').read_bytes());budget=RunBudget(plan,json.loads((package/'carryover/state.json').read_bytes()))
    launcher=json.loads(os.environ['MIRAGE_JEV_LAUNCHER_IDENTITY'])
    assert same_identity(identity(os.getppid()),launcher)
    assert os.getuid()==1033 and os.environ['CUDA_VISIBLE_DEVICES']=='4,5,6,7'
    lease=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
    journal=Journal(root/'journal');requests_root=root/'requests';requests_root.mkdir()
    stop={'requested':False};count=0;error=None;runtime=None;server=None;started=time.time();ready_time=None
    signal.signal(signal.SIGTERM,lambda *_:stop.update(requested=True))
    signal.signal(signal.SIGINT,lambda *_:stop.update(requested=True))
    def resource(empty=False):
        assert not (root.parent/'stop-requested.json').exists(),'Own task stop marker'
        proof=assert_owned_resources(lease,manifest['expected_holder'],{me['pid']:me,launcher['pid']:launcher},empty)
        journal.append('actual_resource_check',proof);return proof
    def status(phase,**extra):
        v={'phase':phase,'time':time.time(),'active':budget.active,'next_run_index':budget.index,'counts':budget.counts,
           'done':budget.done,'actual_model_attempts':count,**extra}
        p=root/'.status.tmp';p.write_bytes(canonical(v));p.replace(root/'status.json')
    try:
        resource(True)
        mutex=Path(json.loads(lease.read_bytes())['inference_lock']).open('a');fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status('loading')
        runtime=load_runtime(package,root,journal,resource,manifest,me)
        engine=runtime['engine'];torch=runtime['torch'];support=runtime['support'];aux=runtime['aux_support']
        aux_model=runtime['auxiliary_model'];aux_processor=runtime['auxiliary_processor'];generation=runtime['generation']
        audit=runtime['audited_generation']
        import bounded_auxiliary
        bounded_data=bounded_auxiliary.prepare(aux_processor,generation,root,package)
        from resident_schedule import ResidentSchedule
        schedule=ResidentSchedule(runtime,root,journal,resource)
        from prefill_residency import PrefillResidency
        prefill=PrefillResidency(runtime,schedule,root,journal,resource)
        token=(package/'private.token').read_bytes().strip()
        ready_time=time.time();last_activity={'time':ready_time}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def authorized(self):return hmac.compare_digest(self.headers.get('Authorization','').encode(),b'Bearer '+token)
            def reply(self,code,value):
                raw=canonical(value);self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);self.wfile.flush()
            def do_GET(self):
                if not self.authorized():self.reply(401,{'error':'unauthorized'});return
                if budget.active is not None:self.reply(409,{'error':'No health inference or probes while GUI is active'});return
                resource()
                self.reply(200,{'phase':'ready_gui','time_unix':time.time(),'pid':me['pid'],'uid':me['uid'],
                    'manifest_sha256':a.manifest_sha256,'resource_ownership_actual':True,'source_SHA_matches':True,
                    'new_model_calls':0,'actual_prior_model_attempts':count,'single_auxiliary':True})
            def do_POST(self):
                nonlocal count,error
                if not self.authorized():self.reply(401,{'error':'unauthorized'});return
                folder=None;raw=None;body={}
                try:
                    length=int(self.headers['Content-Length']);assert 0<length<150_000_000
                    raw=self.rfile.read(length);body=json.loads(raw)
                    item=budget.admit(self.path,body);resource();last_activity['time']=time.time()
                    response={'request_id':body['request_id'],'external_wire_sha256':digest(raw)}
                    if self.path in ['/begin','/end']:
                        journal.append('GUI_run_begin' if self.path=='/begin' else 'GUI_run_end',body)
                        status('terminal_failure' if budget.failed else 'completed' if budget.terminal else 'GUI_active' if budget.active else 'ready_next_run')
                        self.reply(200,{**response,'accepted':True});return
                    count+=1;folder=requests_root/('%04d'%count);folder.mkdir()
                    (folder/'external-wire.json').write_bytes(raw);save(folder/'payload.json',body['payload'])
                    op='evidence' if self.path=='/evidence' else body['payload']['operation']
                    journal.append('model_request',{'request':str(folder.relative_to(root)),'operation':op,'trajectory_id':body['trajectory_id'],
                        'decision_index':body['decision_index'],'attempt_index':body['attempt_index'],'payload_sha256':digest(canonical(body['payload']))})
                    status('generating',operation=op,request=str(folder.relative_to(root)));support.reset_memory(torch)
                    started_call=time.perf_counter();payload=body['payload']
                    if op=='evidence':
                        schedule.to_auxiliary()
                        raw_image=contract.validate_image_only_request(payload)
                        (folder/'original.png').write_bytes(raw_image)
                        text,actual,utf8_roundtrip=bounded_auxiliary.generate(aux_model,aux_processor,generation,torch,audit,bounded_data,raw_image,folder)
                        schedule.to_primary()
                        envelope={'request_sha256':digest(canonical(payload)),'image_sha256':payload['image_sha256'],
                                  'model':payload['model'],'revision':payload['revision'],'raw_output':text,'natural_eos':actual['natural_EOS']}
                        if not utf8_roundtrip:
                            # Do not edit raw output/EOS. The original observer
                            # rejects the extra transport-error field wholesale.
                            envelope['evidence_transport_error']='Native generated bytes fail strict UTF8 roundtrip'
                        result={'evidence_response':envelope}
                        try:
                            if not utf8_roundtrip:raise contract.EvidenceContractError('Invalid native UTF8; entire packet withheld')
                            save(folder/'evidence-packet.json',contract.actor_packet(payload,text,actual['natural_EOS']))
                        except contract.EvidenceContractError as exc:
                            save(folder/'contract-failure.json',{'type':type(exc).__name__,'message':str(exc),'no_retry':True})
                    else:
                        with audit(engine.model,engine.processor,folder):
                            if op=='actor':
                                assert set(payload)=={'operation','body'} and payload['body']['max_tokens']==2048
                                text=engine.generate(payload['body']['messages'],2048,folder/'native-call.json',original_body=payload['body'])
                                result={'text':text}
                            else:
                                assert op=='judge' and set(payload)=={'operation','system','view','candidate'}
                                v=payload['view'];assert set(v)=={'observation_id','messages','images','recent_action','execution_feedback','observed_at'}
                                view=PublicView(v['observation_id'],v['messages'],tuple(VisibleImage(base64.b64decode(im['raw_base64']),im['role']) for im in v['images']),v['recent_action'],v['execution_feedback'],v['observed_at'])
                                result={'verdict':engine.judge(payload['system'],view,payload['candidate'],receipt=folder/'native-call.json')}
                    response.update(result,operation=op,receipt=str(folder),payload_sha256=digest(canonical(payload)),
                        seconds_including_instrumentation=time.perf_counter()-started_call)
                    resource();save(folder/'response.json',response)
                    save(folder/'seal.json',{p.name:sha(p) for p in folder.iterdir() if p.is_file()})
                    journal.append('model_reply_sealed',{'request':str(folder.relative_to(root)),'seal_sha256':sha(folder/'seal.json'),'operation':op})
                    torch.cuda.empty_cache();status('GUI_active');self.reply(200,response)
                except BaseException:
                    error={'traceback':traceback.format_exc(),'semantic_mirage':None,'no_automatic_retry':True,'time':time.time()}
                    if folder is not None:
                        save(folder/'failure.json',error)
                        if runtime is not None:save(folder/'failure-memory.json',runtime['support'].memory(runtime['torch']))
                        if not (folder/'seal.json').exists():save(folder/'seal.json',{p.name:sha(p) for p in folder.iterdir() if p.is_file()})
                    journal.append('technical_failure',error);budget.failed=True;stop['requested']=True;status('terminal_failure')
                    self.reply(500,{'error':'Preserved technical failure','receipt':None if folder is None else str(folder),
                        'request_id':body.get('request_id'),'external_wire_sha256':None if raw is None else digest(raw),'semantic_mirage':None})

        server=HTTPServer(('192.0.2.11',19141),Handler);server.timeout=1
        save(root/'ready.json',{'phase':'ready_gui','time_unix':ready_time,'identity':me,'manifest_sha256':a.manifest_sha256,
            'URL':'http://192.0.2.11:19141','single_auxiliary':True,'new_model_calls':0,'GUI_started':False})
        status('ready_gui')
        while not stop['requested'] and not budget.terminal:
            if (root.parent/'stop-requested.json').exists():stop['requested']=True;break
            if time.time()-last_activity['time']>1800:raise RuntimeError('No GUI activity for 1800 seconds; stop own idle allocation')
            server.handle_request()
        status('technical_failure' if error or budget.failed else 'completed' if budget.terminal else 'stopped')
    except BaseException:
        error={'traceback':traceback.format_exc(),'semantic_mirage':None,'no_automatic_retry':True}
        save(root/'failure.json',error);journal.append('worker_failure',error)
    finally:
        if server is not None:server.server_close()
        save(root/'terminal.json',{'status':'technical_failure' if error or budget.failed else 'completed' if budget.terminal else 'stopped',
            'error':error,'done':budget.done,'total_model_attempts':count,'started':started,'ended':time.time(),
            'formal_Mirage_efficacy_proven':False,'single_auxiliary':True})
    return 1 if error or budget.failed else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    code=main(p.parse_args());raise SystemExit(code)
