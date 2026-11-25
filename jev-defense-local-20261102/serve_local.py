"""Loopback-only audited transport around unchanged pinned reference runtimes."""
import argparse, base64, hashlib, io, json, os, pathlib, sys, time, traceback, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

REVISIONS={'jev_style':'9d3147c2ba1d793958e447b0e7e20c7436ec34b5','neohorse':'434cb21d3a994a953d3ae5788405fcb2c4970554'}
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def save(p,x):
    with p.open('x',encoding='utf-8') as f: json.dump(x,f,ensure_ascii=False,indent=2)
def resource_snapshot(gpu_uuid,pid):
    lines=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True).strip().splitlines()
    pids={int(line.split(',')[1].strip()) for line in lines if line.split(',')[0].strip()==gpu_uuid}
    return {'gpu_uuid':gpu_uuid,'exclusive_gpu':pids=={pid},'actual_gpu_pids':sorted(pids)}

def main(a):
    root=a.root;root.mkdir(parents=True,exist_ok=False)
    (root/'requests').mkdir()
    save(root/'process.json',{'pid':os.getpid(),'uid':os.getuid(),'cmdline':pathlib.Path('/proc/self/cmdline').read_bytes().replace(b'\0',b' ').decode(),'start_ticks':pathlib.Path('/proc/self/stat').read_text().split()[21],'visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),'inherited_lock_fds':os.environ['MIRAGE_GPU_LOCK_FDS'],'model':a.model,'revision':REVISIONS[a.model]})
    import torch, transformers
    from PIL import Image
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    t=time.monotonic()
    if a.model=='jev_style':
        sys.path.insert(0,str(a.model_dir))
        from jev_style_decision import JevStyleDecision
        engine=JevStyleDecision(a.model_dir,device='cuda',dtype='bfloat16',fast=False,cuda_graphs=False,verify=True)
        module=engine.engine.bb.model.model
        all_model=engine.engine.bb.model
    else:
        sys.path.insert(0,str(a.model_dir/'package/src'))
        from neohorse_decision.vision import VisionDecisionEngine
        engine=VisionDecisionEngine(a.model_dir,device='cuda')
        module=engine.wrapper;all_model=engine.text.model
    tensors=list(all_model.named_parameters())+list(all_model.named_buffers())
    if not tensors or any(x.device.type!='cuda' or x.device.index!=0 for _,x in tensors):raise RuntimeError('All model tensors must be on this owned single CUDA device')
    audit={'model':a.model,'revision':REVISIONS[a.model],'load_seconds':time.monotonic()-t,'torch':torch.__version__,'transformers':transformers.__version__,'devices':sorted({str(x.device) for _,x in tensors}),'dtype_elements':{},'tensor_count':len(tensors),'single_gpu':True,'native_processor':True,'autoreg_generation':False,'max_context':32768 if a.model=='jev_style' else 12288,'neohorse_native_max_state_tokens':2048 if a.model=='neohorse' else None,'fast_text':False,'cuda_graphs':False}
    for _,x in tensors:audit['dtype_elements'][str(x.dtype)]=audit['dtype_elements'].get(str(x.dtype),0)+x.numel()
    save(root/'loaded.json',audit)
    token=a.token_file.read_text().strip()
    physical=os.environ['CUDA_VISIBLE_DEVICES']
    gpu_uuid=subprocess.check_output(['nvidia-smi','-i',physical,'--query-gpu=uuid','--format=csv,noheader'],text=True).strip()
    def resource_admission():
        return {**resource_snapshot(gpu_uuid,os.getpid()),'physical_gpu':physical}
    trace=[]
    def hook(_module,args,kwargs):
        record={}
        for k,v in kwargs.items():
            if isinstance(v,torch.Tensor):
                c=v.detach().cpu().contiguous()
                record[k]={'shape':list(c.shape),'dtype':str(c.dtype),'sha256':sha(c.view(torch.uint8).numpy().tobytes())}
                if k in ('input_ids','image_grid_thw'):record[k]['values']=c.tolist()
        trace.append(record)
    module.register_forward_pre_hook(hook,with_kwargs=True)
    class Handler(BaseHTTPRequestHandler):
        def reply(self,code,obj):
            body=canonical(obj);self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path!='/health':return self.reply(404,{'error':'not found'})
            self.reply(200,{'phase':'ready','pid':os.getpid(),'uid':os.getuid(),**audit,**resource_admission()})
        def do_POST(self):
            if self.path!='/decision':return self.reply(404,{'error':'not found'})
            if self.headers.get('Authorization')!='Bearer '+token:return self.reply(403,{'error':'unauthorized'})
            admission=resource_admission()
            if not admission['exclusive_gpu']:return self.reply(503,{'status':'waiting_resources','model_calls':0,**admission})
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=16*1024*1024:return self.reply(413,{'error':'request size'})
            body=self.rfile.read(n);req=json.loads(body);rid=req.get('request_id','')
            if not rid or len(rid)>96 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in rid):return self.reply(400,{'error':'invalid request ID'})
            d=root/'requests'/rid
            if d.exists():
                same=(d/'request.json').read_bytes()==body
                if same and (d/'response.json').exists():return self.reply(200,json.loads((d/'response.json').read_bytes()))
                return self.reply(409,{'error':'request ID already submitted; inspect preserved attempt; no automatic retry'})
            d.mkdir();(d/'request.json').write_bytes(body)
            t0=time.monotonic();trace.clear();torch.cuda.reset_peak_memory_stats()
            try:
                raw=base64.b64decode(req['image_base64'],validate=True)
                if sha(raw)!=req['image_sha256']:raise ValueError('Image SHA mismatch')
                (d/'original.image').write_bytes(raw)
                im=Image.open(io.BytesIO(raw));im.load()
                if im.width*im.height>4194304:raise ValueError('Original image exceeds deployment limit; reject, never crop')
                q=req['question'];options=req['options'];state=req['state']
                if not isinstance(state,(str,dict,list)) or not isinstance(q,str) or not isinstance(options,dict) or len(options)<2:raise ValueError('Invalid choice request')
                if a.model=='jev_style':
                    native={'state':state,'question':q,'options':options,'images_sha256':[sha(raw)]}
                    save(d/'native-request.json',native)
                    result=engine.decide(state,q,options=options,images=[raw])
                    answer=result['answer'];prob=result['probabilities']
                else:
                    native={'model':'NeoHorse-Jev-4B','state':state,'questions':{'evidence':{'type':'choice','instructions':q,'criteria':options}}}
                    save(d/'native-request.json',native)
                    result=engine.predict(native,image=im)
                    answer=result['answers']['evidence']['choice'];prob=result['answers']['evidence']['probabilities']
                save(d/'native-result.json',result)
                torch.cuda.synchronize()
                if not trace or not any('pixel_values' in r and 'input_ids' in r for r in trace):raise RuntimeError('Actual multimodal forward trace absent')
                save(d/'forward-trace.json',trace)
                response={'status':'ok','model':a.model,'revision':REVISIONS[a.model],'request_id':rid,'request_sha256':sha(body),'image_sha256':sha(raw),'original_size':list(im.size),'answer':answer,'probabilities':prob,'native_result':result,'scope':'one_original_frame_only','history_verified':False,'seconds_including_audit':time.monotonic()-t0,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_reserved_bytes':torch.cuda.max_memory_reserved(),'forward_trace_sha256':sha((d/'forward-trace.json').read_bytes()),'receipt':str(d),'generation_tokens':0}
                save(d/'response.json',response)
                save(d/'seal.json',{p.name:sha(p.read_bytes()) for p in d.iterdir() if p.is_file()})
                self.reply(200,response)
            except Exception:
                if trace and not (d/'forward-trace.json').exists():save(d/'forward-trace.json',trace)
                failure={'status':'technical_failure','model':a.model,'request_id':rid,'error':traceback.format_exc(),'seconds_including_audit':time.monotonic()-t0,'semantic_pass':None}
                save(d/'failure.json',failure);save(d/'seal.json',{p.name:sha(p.read_bytes()) for p in d.iterdir() if p.is_file()})
                self.reply(422,failure)
    save(root/'ready.json',{'time':time.time(),'port':a.port,'bind':'127.0.0.1','audit_sha256':sha((root/'loaded.json').read_bytes())})
    print(json.dumps({'ready':a.model,'port':a.port}),flush=True)
    HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',choices=list(REVISIONS),required=True);p.add_argument('--model-dir',type=pathlib.Path,required=True);p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--token-file',type=pathlib.Path,required=True);p.add_argument('--port',type=int,required=True)
    main(p.parse_args())
