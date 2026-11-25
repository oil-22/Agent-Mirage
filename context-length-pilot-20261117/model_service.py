"""Isolated BF16 four-GPU actor service for the context-length pilot."""
import base64, copy, fcntl, hashlib, hmac, io, json, os, signal, subprocess, threading, time, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

P = Path(__file__).resolve().parent
R = P/'model-output'
LOCKS = []
STOP = threading.Event()
MUTEX = threading.Lock()
LAST = time.monotonic()

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf8')
    tmp.replace(path)

def sha(raw): return hashlib.sha256(raw).hexdigest()

def gpu_rows():
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
    return [dict(index=int(a),uuid=b.strip(),free_mib=int(c)) for a,b,c in (line.split(',') for line in raw.splitlines())]

def admit():
    rows=[r for r in gpu_rows() if r['index'] in [4,5,6,7]]
    assert len(rows)==4 and min(r['free_mib'] for r in rows)>23000, rows
    for directory in [Path.home()/'.mirage-resource-locks',Path.home()/'defense-resume-20261102-retry2/resource-locks']:
        directory.mkdir(exist_ok=True,parents=True)
        for row in rows:
            f=(directory/(row['uuid']+'.lock')).open('a')
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);LOCKS.append(f)
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
    assert not any(r['uuid'] in raw for r in rows), 'Selected GPUs have a compute process'
    save(R/'resource-admission.json',dict(gpus=rows,pid=os.getpid(),uid=os.getuid(),time=time.time()))

def foreign_compute_check():
    rows=json.loads((R/'resource-admission.json').read_text())['gpus']
    uuids={r['uuid'] for r in rows}
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
    for line in raw.splitlines():
        u,pid=line.split(',')
        if u.strip() in uuids and int(pid)!=os.getpid():
            raise RuntimeError('Foreign compute process appeared on reserved GPU: '+line)

def main():
    global LAST
    R.mkdir(exist_ok=False)
    save(R/'status.json',dict(phase='resource_admission',time=time.time(),pid=os.getpid()))
    admit()
    import torch, transformers
    from transformers import AutoProcessor, AutoModelForImageTextToText
    from PIL import Image
    torch.set_num_threads(4)
    assert torch.cuda.device_count()==4
    config=json.loads((P/'config.json').read_text())
    token=(P/'service.token').read_text().strip()
    save(R/'status.json',dict(phase='loading',time=time.time(),pid=os.getpid()))
    processor=AutoProcessor.from_pretrained(config['model'],local_files_only=True,trust_remote_code=True)
    model=AutoModelForImageTextToText.from_pretrained(config['model'],dtype=torch.bfloat16,
        attn_implementation='sdpa',device_map='balanced',max_memory={i:'18GiB' for i in range(4)},
        local_files_only=True,trust_remote_code=True).eval()
    assert not any(str(v) in ['cpu','disk'] for v in model.hf_device_map.values()), 'No CPU/disk offload allowed'
    assert all(p.dtype==torch.bfloat16 for p in model.parameters() if p.is_floating_point())
    save(R/'loaded.json',dict(pid=os.getpid(),model=config['model'],dtype=str(model.dtype),
        torch=torch.__version__,transformers=transformers.__version__,
        device_map={k:str(v) for k,v in model.hf_device_map.items()},physical_gpus=[4,5,6,7],
        backend='sdpa',history_truncation=False,quantization=False,memory_patch=False,
        metadata_sha256={n:sha((Path(config['model'])/n).read_bytes()) for n in ['config.json','preprocessor_config.json','generation_config.json']},time=time.time()))
    index=0

    def prepare(body):
        messages=[];image_records=[]
        for mi,m in enumerate(body['messages']):
            blocks=m['content'] if isinstance(m['content'],list) else [dict(type='text',text=m['content'])]
            out=[]
            for b in blocks:
                if b['type']=='text':out.append(copy.deepcopy(b))
                elif b['type']=='image_url':
                    url=b['image_url'];url=url['url'] if isinstance(url,dict) else url
                    assert url.startswith('data:image/')
                    raw=base64.b64decode(url.split(',',1)[1]);im=Image.open(io.BytesIO(raw)).convert('RGB')
                    out.append(dict(type='image',image=im))
                    image_records.append(dict(message_index=mi,sha256=sha(raw),width=im.width,height=im.height))
                else:raise ValueError('Unknown input block')
            messages.append(dict(role=m['role'],content=out))
        inputs=processor.apply_chat_template(messages,add_generation_prompt=True,tokenize=True,
             return_dict=True,return_tensors='pt',tools=body.get('tools'),**body.get('chat_template_kwargs',{}))
        ids=inputs['input_ids'][0]
        vision_count=int((ids==model.config.image_token_id).sum())
        info=dict(input_tokens=ids.numel(),visual_tokens=vision_count,
                  non_image_token_count=ids.numel()-vision_count,images=image_records,
                  image_grid_thw=inputs['image_grid_thw'].tolist() if 'image_grid_thw' in inputs else [],
                  input_ids_sha256=sha(ids.contiguous().numpy().tobytes()),history_messages=len(body['messages']))
        return inputs,info

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,code,value):
            raw=json.dumps(value).encode();self.send_response(code);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)));self.end_headers()
            try:self.wfile.write(raw)
            except (BrokenPipeError,ConnectionResetError):pass
        def auth(self):return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
        def do_GET(self):
            if not self.auth():return self.send(401,{'error':'unauthorized'})
            return self.send(200,dict(ready=not STOP.is_set(),requests=index,pid=os.getpid()))
        def do_POST(self):
            nonlocal index
            global LAST
            if not self.auth():return self.send(401,{'error':'unauthorized'})
            if self.path=='/shutdown':STOP.set();return self.send(200,dict(stopping=True))
            with MUTEX:
                folder=None
                try:
                    if STOP.is_set():raise RuntimeError('Service is stopping')
                    length=int(self.headers.get('Content-Length','0'));assert 0<length<300_000_000
                    wire=self.rfile.read(length);request=json.loads(wire);body=request['body']
                    assert body['temperature']==0 and body['max_tokens']==2048
                    assert body.get('chat_template_kwargs',{}).get('enable_thinking') is False
                    LAST=time.monotonic();foreign_compute_check()
                    inputs,info=prepare(body)
                    if self.path=='/count':
                        LAST=time.monotonic();return self.send(200,info)
                    assert self.path=='/generate'
                    index+=1;folder=R/'requests'/f'{index:05}';folder.mkdir(parents=True)
                    (folder/'request.json').write_bytes(wire);save(folder/'input-info.json',info)
                    torch.save({k:v for k,v in inputs.items() if k!='pixel_values'},folder/'input-layout.pt')
                    save(R/'status.json',dict(phase='generating',request=index,meta=request.get('meta'),input_tokens=info['input_tokens'],time=time.time()))
                    cfg=copy.deepcopy(model.generation_config);cfg.do_sample=False;cfg.max_new_tokens=2048;cfg.temperature=0.0
                    save(folder/'generation-config.json',cfg.to_dict())
                    torch.manual_seed(42);started=time.time()
                    for i in range(4):torch.cuda.reset_peak_memory_stats(i)
                    with torch.inference_mode():seq=model.generate(**inputs.to(model.device),generation_config=cfg)
                    ids=seq[0,info['input_tokens']:].detach().cpu().tolist()
                    eos=cfg.eos_token_id;eos=[eos] if isinstance(eos,int) else eos
                    result=dict(text=processor.tokenizer.decode(ids,skip_special_tokens=True).strip(),
                        **info,output_tokens=len(ids),output_ids=ids,natural_EOS=bool(ids and ids[-1] in eos),
                        seconds=time.time()-started,receipt=str(folder),meta=request.get('meta'),
                        peak_allocated_bytes=[torch.cuda.max_memory_allocated(i) for i in range(4)])
                    foreign_compute_check();save(folder/'response.json',result)
                    del seq,inputs;torch.cuda.empty_cache();LAST=time.monotonic()
                    save(R/'status.json',dict(phase='ready',requests=index,last_receipt=str(folder),time=time.time()))
                    self.send(200,result)
                except BaseException:
                    failure=dict(error=traceback.format_exc(),time=time.time(),not_semantic_failure=True,request=index)
                    if folder:save(folder/'failure.json',failure)
                    save(R/'failure.json',failure);save(R/'status.json',dict(phase='failed',**failure))
                    STOP.set();self.send(503,dict(error='Preserved service failure',details=failure['error']))
    server=ThreadingHTTPServer(('192.0.2.11',19317),Handler);server.timeout=1
    signal.signal(signal.SIGTERM,lambda *_:STOP.set());signal.signal(signal.SIGINT,lambda *_:STOP.set())
    LAST=time.monotonic();save(R/'status.json',dict(phase='ready',requests=0,pid=os.getpid(),time=time.time()))
    save(R/'ready.json',dict(pid=os.getpid(),time=time.time(),url='http://192.0.2.11:19317'))
    try:
        while not STOP.is_set():
            server.handle_request()
            if time.monotonic()-LAST>1800:save(R/'idle-timeout.json',dict(time=time.time()));STOP.set()
            if (P/'STOP').exists():STOP.set()
    finally:server.server_close();save(R/'exit.json',dict(requests=index,time=time.time()))

if __name__=='__main__':
    try:main()
    except BaseException:
        save(R/'startup-failure.json',dict(error=traceback.format_exc(),time=time.time()));raise
