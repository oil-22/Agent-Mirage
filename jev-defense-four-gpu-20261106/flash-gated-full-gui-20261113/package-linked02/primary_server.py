"""Original native actor only; serial Flash proxy receives one image, no context."""
import base64,copy,fcntl,hmac,inspect,json,os,signal,sys,threading,time,traceback,urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'flash'),str(P/'release'),str(P)]
from gate_core import Journal,canonical,digest
from resource_guard import identity,locks,sha,LEASE
from wire_contract import decode_request

def save(path,value):
    with path.open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def resource(loaded):
    import subprocess
    lease,fds=locks();cards={};process=[]
    for line in subprocess.check_output(['nvidia-smi','--id=4,5,6','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True).splitlines():
        i,u,m=[s.strip()for s in line.split(',')];cards[int(i)]={'uuid':u,'free_mib':int(m)}
    for line in subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).splitlines():
        if line.strip():
            u,p,m=[s.strip()for s in line.split(',')]
            if u in {v['uuid']for v in cards.values()}:process.append({'uuid':u,'identity':identity(int(p)),'memory_mib':m})
    for i,v in cards.items():
        assert v['uuid']==next(r['uuid']for r in lease['gpu']if r['index']==i)
        pids={r['identity']['pid']for r in process if r['uuid']==v['uuid']}
        assert pids==({os.getpid()}if loaded else set()),'Foreign/unverified compute; no sharing/preemption'
        if not loaded:assert v['free_mib']>=23000
    return {'cards':cards,'compute':process,'held_inherited_locks':len(fds),'time':time.time()}

class NativeActor:
    def __init__(self,root):
        import torch,transformers
        from transformers import AutoProcessor,AutoModelForImageTextToText
        from defense.qwen_backend import LocalQwen
        import preflight_support as support
        self.torch=torch;self.root=root;self.support=support
        reference=json.loads((P/'primary-reference.json').read_bytes());model=Path(reference['primary_model'])
        assert sha(P/'release/defense/qwen_backend.py')==reference['primary_backend_sha256']
        expected=json.loads(Path(reference['primary_expected_runtime']).read_bytes())
        assert torch.__version__==expected['torch']and transformers.__version__==expected['transformers']
        for n,h in expected['metadata_sha256'].items():assert sha(model/n)==h
        boundfile=Path(reference['primary_native_layout_receipt']);assert sha(boundfile)==reference['primary_native_layout_receipt_sha256']
        bound=json.loads(boundfile.read_bytes());meta=Path(bound['meta_root']);headers=Path(bound['header_inventory_root'])
        for n,h in json.loads((meta/'seal.json').read_bytes()).items():assert sha(meta/n)==h
        assert sha(headers/'seal.json')==bound['header_inventory_seal_sha256']
        assert sha(headers/'headers.json')==json.loads((headers/'seal.json').read_bytes())['headers.json']
        stats=[]
        for row in json.loads((headers/'headers.json').read_bytes()):
            s=(model/row['file']).stat();assert(s.st_size,s.st_mtime_ns)==(row['bytes'],row['mtime_ns'])
            stats.append({'file':row['file'],'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'inode':s.st_ino})
        assert len(stats)==18
        save(root/'checkpoint-admission.json',{'metadata':expected['metadata_sha256'],'native_layout_receipt_sha256':sha(boundfile),'weight_stat_continuity':stats,'no_redundant_full_weight_hash':True})
        save(root/'admission-before-load.json',resource(False));torch.set_num_threads(4)
        start=time.time();self.engine=LocalQwen.__new__(LocalQwen);self.engine.torch=torch
        self.engine.processor=AutoProcessor.from_pretrained(model,local_files_only=True,trust_remote_code=True)
        self.engine.model=AutoModelForImageTextToText.from_pretrained(model,dtype=torch.bfloat16,attn_implementation='sdpa',device_map='balanced',max_memory={i:'22GiB'for i in range(3)},local_files_only=True,trust_remote_code=True).eval()
        source=Path(inspect.getfile(type(self.engine.model)));assert sha(source)==bound['native_source_sha256']
        actual=[{'name':n,'shape':list(t.shape),'dtype':str(t.dtype),'device':str(t.device),'bytes':t.numel()*t.element_size()}for n,t in self.engine.model.state_dict().items()]
        state=support.validate_native_state_records(actual,json.loads((meta/'meta-state.json').read_bytes()))
        tensors=support.audit_tensors(torch,[('primary',self.engine.model)],['cuda:0','cuda:1','cuda:2'])
        assert all(t.dtype==torch.bfloat16 for t in self.engine.model.parameters()if t.is_floating_point())
        for row in stats:
            s=(model/row['file']).stat();assert(s.st_size,s.st_mtime_ns,s.st_ino)==(row['bytes'],row['mtime_ns'],row['inode'])
        self.loaded={'identity':identity(os.getpid()),'native_state':state,'CUDA':tensors,'device_map':{k:str(v)for k,v in self.engine.model.hf_device_map.items()},'physical_gpus':[4,5,6],'dtype':'bfloat16','attention':'sdpa','native_model_source_sha256':sha(source),'native_generation_backend_sha256':sha(P/'release/defense/qwen_backend.py'),'native_generate_unchanged':True,'main_history_truncation':False,'image_preprocessing_changed':False,'long_history_capacity_proven':False,'load_seconds':time.time()-start,'memory':support.memory(torch),'torch':torch.__version__,'transformers':transformers.__version__}
        save(root/'loaded.json',self.loaded);save(root/'actual-state.json',actual);save(root/'admission-after-load.json',resource(True))
    def generate(self,body,folder):
        torch=self.torch;engine=self.engine;prepared={};first={};count=0
        apply=engine.processor.apply_chat_template;generate=engine.model.generate
        def tensor_record(v,name):
            c=v.detach().cpu().contiguous();data=c.view(torch.uint8).numpy().tobytes();p=folder/(name+'.tensor')
            with p.open('xb')as f:f.write(data)
            return {'shape':list(c.shape),'dtype':str(c.dtype),'bytes':len(data),'sha256':digest(data),'file':p.name}
        def wrapped_apply(*args,**kwargs):
            value=apply(*args,**kwargs)
            for k,v in value.items():prepared[k]=tensor_record(v,'prepared_'+k)
            save(folder/'prepared.json',prepared);return value
        def hook(_module,args,kwargs):
            nonlocal count
            if count==0:
                for k in prepared:
                    v=kwargs[k];record=tensor_record(v,'first_forward_'+k)
                    assert all(record[x]==prepared[k][x]for x in ['shape','dtype','bytes','sha256']);first[k]=record
                save(folder/'first-forward.json',first)
                assert kwargs.get('past_key_values')is None or kwargs['past_key_values'].get_seq_length()==0
            count+=1
        def wrapped_generate(*args,**kwargs):
            assert not args
            save(folder/'effective-generation.json',kwargs['generation_config'].to_dict())
            seq=generate(**kwargs);length=kwargs['input_ids'].shape[-1]
            assert torch.equal(seq[:,:length],kwargs['input_ids'])
            ids=seq[0,length:].detach().cpu().tolist();eos=kwargs['generation_config'].eos_token_id;eos=[eos]if isinstance(eos,int)else eos
            tensor_record(seq,'sequence_ids')
            save(folder/'actual-generation.json',{'input_tokens':length,'output_tokens':len(ids),'output_ids':ids,'natural_EOS':bool(ids and ids[-1]in eos),'actual_forward_calls':count,'memory':self.support.memory(torch)})
            if not ids or ids[-1]not in eos:raise RuntimeError('Native output did not end in original EOS; no retry/cap expansion')
            return seq
        engine.processor.apply_chat_template=wrapped_apply;engine.model.generate=wrapped_generate;handle=engine.model.register_forward_pre_hook(hook,with_kwargs=True)
        try:return engine.generate(body['messages'],2048,folder/'native-call.json',original_body=body)
        finally:
            handle.remove();engine.processor.apply_chat_template=apply;engine.model.generate=generate
            save(folder/'forward-count.json',{'actual_forward_calls':count});torch.cuda.empty_cache()

def main(root):
    root.mkdir(parents=True,exist_ok=False);(root/'requests').mkdir();save(root/'process.json',identity(os.getpid()))
    manifest=json.loads((P/'manifest.json').read_bytes())
    for n,h in manifest['files'].items():assert sha(P/n)==h,n
    token=(P/'private.token').read_text().strip();journal=Journal(root/'journal');plan=json.loads((P/'plan.json').read_bytes());queue=[r['run_id']for r in plan['queue']]
    stop=threading.Event();mutex=threading.Lock();active=None;index=0;attempted=0;replies=0;actor_counts={};request_ids=set();terminal_status='technical_failure';server=None
    inference=Path(json.loads(LEASE.read_bytes())['inference_lock']).open('a');fcntl.flock(inference,fcntl.LOCK_EX|fcntl.LOCK_NB)
    def state(phase,**extra):
        value={'phase':phase,'active':active,'done':index,'expected':len(queue),'attempted_actor_calls':attempted,'complete_actor_replies':replies,'actor_counts':actor_counts,'time':time.time(),**extra}
        tmp=root/'.status.tmp';tmp.write_bytes(canonical(value));tmp.replace(root/'status.json')
    try:
        state('loading');native=NativeActor(root);journal.emit('loaded',{'loaded_sha256':sha(root/'loaded.json')});state('ready')
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send(self,code,v):
                raw=canonical(v);self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
                try:self.wfile.write(raw)
                except (BrokenPipeError,ConnectionResetError):pass
            def auth(self):return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
            def do_GET(self):
                if not self.auth():return self.send(401,{'error':'unauthorized'})
                return self.send(200,{'phase':'ready','identity':identity(os.getpid()),'manifest_sha256':sha(P/'manifest.json'),'done':index,'expected':len(queue),'active':active,'actor_attempts':attempted,'actor_replies':replies})
            def do_POST(self):
                nonlocal active,index,attempted,replies
                if not self.auth():return self.send(401,{'error':'unauthorized'})
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<150_000_000:return self.send(400,{'error':'invalid length'})
                raw=self.rfile.read(length);folder=None
                with mutex:
                    try:
                        if stop.is_set():raise RuntimeError('Experiment stopped')
                        body=json.loads(raw)
                        if self.path=='/gate':
                            request,png=decode_request(raw)
                            if active is None:raise ValueError('No active GUI run')
                            flash=P/'flash/service';url='http://127.0.0.1:18341/decision'
                            req=urllib.request.Request(url,data=raw,headers={'Content-Type':'application/json','Authorization':'Bearer '+(flash/'token').read_text().strip()})
                            with urllib.request.urlopen(req,timeout=180)as response:out=json.load(response)
                            journal.emit('Flash_reply_forwarded',{'run_id':active,'decision':out['decision'],'request_id':out['request_id'],'image_sha256':out['image_sha256']})
                            return self.send(200,out)
                        if self.path=='/begin':
                            assert set(body)=={'run_id'}and active is None and index<len(queue)and body['run_id']==queue[index]
                            active=body['run_id'];actor_counts[active]=0;journal.emit('run_begin',body);state('GUI_active');return self.send(200,{'accepted':True})
                        if self.path=='/end':
                            assert set(body)=={'run_id','terminal_sha256','infrastructure_failure'}and body['run_id']==active
                            journal.emit('run_end',body);index+=1;active=None
                            if body['infrastructure_failure']:stop.set()
                            state('completed'if index==len(queue)else'stopped'if body['infrastructure_failure']else'ready_next')
                            if index==len(queue):stop.set()
                            return self.send(200,{'accepted':True})
                        assert self.path=='/actor'and set(body)=={'request_id','run_id','decision_index','body'}and body['run_id']==active
                        rid=body['request_id'];assert rid not in request_ids and isinstance(rid,str)and len(rid)==32;request_ids.add(rid)
                        assert actor_counts[active]<70 and 1<=body['decision_index']<=50
                        original=body['body'];template=json.loads((P/'actor-template.json').read_bytes())
                        assert{k:v for k,v in original.items()if k!='messages'}=={k:v for k,v in template.items()if k!='messages'}
                        assert original['messages'][0]==template['messages'][0]
                        attempted+=1;actor_counts[active]+=1;folder=root/'requests'/('%05d'%attempted);folder.mkdir()
                        (folder/'wire-request.bin').write_bytes(raw);save(folder/'body.json',original);save(folder/'admission-before.json',resource(True))
                        journal.emit('actor_request',{'request_id':rid,'run_id':active,'wire_sha256':digest(raw),'folder':str(folder),'decision':body['decision_index']});state('generating',request=str(folder))
                        start=time.time();text=native.generate(original,folder);save(folder/'admission-after.json',resource(True))
                        out={'request_id':rid,'request_sha256':digest(raw),'text':text,'receipt':str(folder),'seconds_with_audit':time.time()-start}
                        save(folder/'response.json',out);save(folder/'seal.json',{p.name:sha(p)for p in folder.iterdir()if p.is_file()});replies+=1
                        journal.emit('actor_reply_sealed',{'request_id':rid,'run_id':active,'seal_sha256':sha(folder/'seal.json'),'folder':str(folder)});state('GUI_active');return self.send(200,out)
                    except BaseException:
                        failure={'error':traceback.format_exc(),'not_semantic_NO':True,'no_automatic_retry':True,'time':time.time()}
                        if folder is not None:
                            save(folder/'failure.json',failure);save(folder/'seal.json',{p.name:sha(p)for p in folder.iterdir()if p.is_file()})
                        journal.emit('technical_failure',failure);state('technical_failure',error=failure);stop.set();return self.send(503,{'error':'Preserved technical failure','receipt':str(folder),'no_automatic_retry':True})
        server=ThreadingHTTPServer(('192.0.2.11',19201),Handler);server.timeout=0.5;server.daemon_threads=False
        signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
        save(root/'ready.json',{'identity':identity(os.getpid()),'manifest_sha256':sha(P/'manifest.json'),'URL':'http://192.0.2.11:19201','time':time.time()})
        while not stop.is_set():server.handle_request()
        terminal_status='completed'if index==len(queue)else'stopped'
    except BaseException:save(root/'failure.json',{'error':traceback.format_exc(),'no_automatic_retry':True});traceback.print_exc()
    finally:
        if server is not None:server.server_close()
        save(root/'terminal.json',{'status':terminal_status,'done':index,'expected':len(queue),'attempted_actor_calls':attempted,'complete_actor_replies':replies,'time':time.time()});sys.stdout.flush();sys.stderr.flush()
    return 0 if terminal_status=='completed'else 1
if __name__=='__main__':raise SystemExit(main(Path(sys.argv[1])))
