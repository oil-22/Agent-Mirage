"""Finite native GPU comparison. No actor, GUI, scorer, server or autoregression."""
import argparse, fcntl, hashlib, io, json, os, subprocess, sys, time, traceback
from pathlib import Path

B=Path('/home/researcher/jev-defense-four-gpu-20261106')
ROOT=B/'binary-gate-comparison-20261112'
LEASE=B/'resource-attempt-20261106-01/lease.json'
LEASE_SHA='8f5da746fbb45c587d23a0073f8dc62dcd9510b321b4cef0995c09aa8c92a89a'
PROTOCOL_SHA='556273f9c9c6930258b57753e34145590c142384db48d0f45c4e4d03b5aee6e9'

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def save(p,v):
 with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def identity(pid):
 p=Path('/proc',str(pid));s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
def snapshot():
 cards={}
 raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
 for line in raw.strip().splitlines():
  i,u,m=[v.strip() for v in line.split(',')];cards[int(i)]={'uuid':u,'free_mib':int(m)}
 apps=[]
 raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
 for line in raw.strip().splitlines():
  if not line.strip():continue
  u,p,m=[v.strip() for v in line.split(',')];apps.append({'uuid':u,'memory_mib':m,'identity':identity(int(p))})
 return {'time':time.time(),'gpu':cards,'compute':apps}
def verify_locks():
 assert os.getuid()==1033 and sha(LEASE)==LEASE_SHA
 lease=json.loads(LEASE.read_bytes());expected=lease['holder'];actual=identity(expected['pid'])
 assert all(actual[k]==expected[k] for k in ['pid','uid','command','start_ticks'])
 assert actual['state'] not in ['Z','X']
 fds=tuple(int(v) for v in os.environ['MIRAGE_GPU_LOCK_FDS'].split(','))
 assert len(fds)==9 and os.environ['MIRAGE_TASK_LEASE']==str(LEASE)
 for row in lease['lock_records']:
  fd=row['fd'];assert fd in fds
  p=Path('/proc/self');info=(p/'fdinfo'/str(fd)).read_text()
  assert os.readlink(p/'fd'/str(fd))==row['path'] and os.fstat(fd).st_ino==row['inode']
  assert 'WRITE '+str(expected['pid']) in info
 return fds
def admission(require_loaded):
 verify_locks();s=snapshot();uuid=s['gpu'][4]['uuid']
 expected_uuid=json.loads(LEASE.read_bytes())['gpu'][0]['uuid']
 assert uuid==expected_uuid
 pids={r['identity']['pid'] for r in s['compute'] if r['uuid']==uuid}
 assert pids==({os.getpid()} if require_loaded else set()), 'Exclusive GPU4 unavailable: '+str(pids)
 if not require_loaded:assert s['gpu'][4]['free_mib']>=23000
 return s
class Journal:
 def __init__(self,path):self.path=path;self.seq=0;self.head='0'*64
 def add(self,kind,data):
  row={'seq':self.seq,'previous':self.head,'time':time.time(),'kind':kind,'data':data};row['sha256']=hashlib.sha256(canon(row)).hexdigest()
  with self.path.open('ab') as f:f.write(canon(row)+b'\n');f.flush();os.fsync(f.fileno())
  self.seq+=1;self.head=row['sha256']
def stats(path):
 s=path.stat();return {'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'mtime_ns':s.st_mtime_ns}
def verify_checkpoint(name,config):
 receipt=Path(config['receipt']);assert sha(receipt)==config['receipt_sha256']
 v=json.loads(receipt.read_bytes());assert v['revision']==config['revision']
 model=Path(config['model_dir']);result={'receipt':str(receipt),'receipt_sha256':sha(receipt),'revision':v['revision'],'files':[]}
 stable=None
 if name=='flash':
  stable_path=ROOT/'flash-identity.json';assert sha(stable_path)==json.loads((ROOT/'protocol.json').read_bytes())['flash_identity_sha256']
  stable=json.loads(stable_path.read_bytes());stable={r['file']:r for r in stable['files']}
 for row in v['files']:
  p=model/row['file'];assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(model.resolve())
  stamp=stats(p);assert stamp['size']==row['bytes']
  if stable is not None:
   assert stable[row['file']]['sha256']==row['sha256'] and stable[row['file']]['stat']==stamp
  if p.suffix not in ['.safetensors','.bin','.pt']:
   assert sha(p)==row['sha256'], 'Native source/metadata changed: '+str(p)
  result['files'].append({'file':row['file'],'completed_full_sha256':row['sha256'],'current_stat':stamp,'new_full_sha256':sha(p) if p.stat().st_size<2*1024*1024 else None})
 result['identity_method']='Prior sealed complete byte identity; current size/stat and native source/metadata hashes. Flash also matches prior full dev/ino/size/mtime_ns. Style native verify=True additionally verifies its publisher manifest.'
 return result
def memory(torch):
 return {'allocated_bytes':torch.cuda.memory_allocated(),'reserved_bytes':torch.cuda.memory_reserved(),'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_reserved_bytes':torch.cuda.max_memory_reserved()}
def worker(name):
 assert os.environ['CUDA_VISIBLE_DEVICES']=='4'
 assert sha(ROOT/'protocol.json')==PROTOCOL_SHA
 protocol=json.loads((ROOT/'protocol.json').read_bytes());config=protocol['models'][name]
 root=ROOT/'results'/name;root.mkdir(parents=True,exist_ok=False);(root/'requests').mkdir()
 save(root/'process.json',{**identity(os.getpid()),'visible_devices':os.environ['CUDA_VISIBLE_DEVICES'],'inherited_fds':list(verify_locks()),'script_sha256':sha(Path(__file__))})
 journal=Journal(root/'events.jsonl');count=0;completed=0;phase='startup'
 try:
  save(root/'admission-before-load.json',admission(False));before=verify_checkpoint(name,config);save(root/'checkpoint-before.json',before)
  import torch,transformers
  from PIL import Image
  torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
  t=time.monotonic();model=Path(config['model_dir'])
  if name=='flash':
   sys.path.insert(0,str(model/'source/src'));from pplx_decider import Decider
   engine=Decider.from_pretrained(model,device='cuda:0',fast=False,cpu_threads=4)
   modules=[('backbone',engine.backbone),('readout',engine.readout)]
   forward_module=engine.backbone;raw_module=engine.readout
   import pplx_decider.model as native
   assert Path(native.__file__).resolve()==model/'source/src/pplx_decider/model.py'
  elif name=='neohorse':
   sys.path.insert(0,str(model/'package/src'));from neohorse_decision.vision import VisionDecisionEngine
   engine=VisionDecisionEngine(model,device='cuda')
   modules=[('native_model',engine.text.model)];forward_module=engine.wrapper;raw_module=engine.text.model.head
  else:
   sys.path.insert(0,str(model));from jev_style_decision import JevStyleDecision
   engine=JevStyleDecision(model,device='cuda',dtype='bfloat16',fast=False,cuda_graphs=False,verify=True,threads=4)
   modules=[('native_model',engine.engine.bb.model)];forward_module=engine.engine.bb.model.model;raw_module=None
  torch.cuda.synchronize();load_seconds=time.monotonic()-t
  tensor_rows=[]
  for prefix,module in modules:
   for key,v in list(module.named_parameters())+list(module.named_buffers()):
    assert v.device.type=='cuda' and v.device.index==0
    tensor_rows.append({'name':prefix+'.'+key,'device':str(v.device),'dtype':str(v.dtype),'elements':v.numel(),'bytes':v.numel()*v.element_size()})
  assert tensor_rows
  save(root/'actual-tensors.json',tensor_rows)
  audit={'model':name,'repository':config['repository'],'revision':config['revision'],'native_adapter':True,'load_seconds':load_seconds,'torch':torch.__version__,'transformers':transformers.__version__,'devices':sorted({r['device'] for r in tensor_rows}),'dtype_elements':{s:sum(r['elements'] for r in tensor_rows if r['dtype']==s) for s in sorted({r['dtype'] for r in tensor_rows})},'parameter_and_buffer_bytes':sum(r['bytes'] for r in tensor_rows),'memory':memory(torch),'fast':False,'cuda_graphs':False,'autoreg_generation':False,'model_order':protocol['model_order'],'per_call_empty_context':True}
  save(root/'loaded.json',audit);save(root/'admission-after-load.json',admission(True));journal.add('loaded',{'loaded_sha256':sha(root/'loaded.json')})
  current=[];raw_outputs=[];copies=[]
  def record(v,values=False):
   c=v.detach().cpu().contiguous();b=c.view(torch.uint8).numpy().tobytes();r={'shape':list(c.shape),'dtype':str(c.dtype),'sha256':hashlib.sha256(b).hexdigest()}
   if values:r['values']=c.tolist()
   return c,r
  def input_hook(module,args,kwargs):
   row={'cache_present':kwargs.get('past_key_values') is not None,'use_cache':kwargs.get('use_cache',getattr(module.config,'use_cache',None))}
   assert not row['cache_present'] and row['use_cache'] is not True
   tensor_copy={}
   for key,value in kwargs.items():
    if isinstance(value,torch.Tensor):
     c,r=record(value,key in ['input_ids','image_grid_thw']);row[key]=r;tensor_copy[key]=c
   assert 'input_ids' in row and 'pixel_values' in row and 'image_grid_thw' in row
   current.append(row);copies.append(tensor_copy)
  handles=[forward_module.register_forward_pre_hook(input_hook,with_kwargs=True)]
  if raw_module is not None:
   def output_hook(module,args,output):raw_outputs.append(record(output,True)[1])
   handles.append(raw_module.register_forward_hook(output_hook))
  phase='requests'
  for case in protocol['cases']:
   d=root/'requests'/case['id'];d.mkdir(exist_ok=False);raw=(ROOT/'inputs'/case['file']).read_bytes()
   assert hashlib.sha256(raw).hexdigest()==case['sha256']
   im=Image.open(io.BytesIO(raw));im.load();assert list(im.size)==[case['width'],case['height']]
   save(d/'admission-before.json',admission(True))
   request={'request_id':name+'-'+case['id'],'image_file':str(ROOT/'inputs'/case['file']),'image_sha256':case['sha256'],'state':protocol['state'],'question':protocol['question'],'options':protocol['options'],'single_complete_image':True,'empty_context':True}
   save(d/'request.json',request);current.clear();raw_outputs.clear();copies.clear();torch.cuda.reset_peak_memory_stats()
   journal.add('request_started',{'case_id':case['id'],'request_sha256':sha(d/'request.json'),'image_sha256':case['sha256']});count+=1
   try:
    t=time.monotonic()
    if name=='flash':
     native_request={'state':protocol['state'],'images':[im],'questions':{'usable':{'type':'choice','instructions':protocol['question'],'criteria':protocol['options']}}}
     save(d/'native-request.json',{**native_request,'images':[{'original_image_sha256':case['sha256'],'width':im.width,'height':im.height}]})
     result=engine.decide(native_request);answer=result['answers']['usable']['choice'];prob=result['answers']['usable']['probabilities']
    elif name=='neohorse':
     native_request={'model':'NeoHorse-Jev-4B','state':protocol['state'],'questions':{'evidence':{'type':'choice','instructions':protocol['question'],'criteria':protocol['options']}}}
     save(d/'native-request.json',native_request)
     result=engine.predict(native_request,image=im);answer=result['answers']['evidence']['choice'];prob=result['answers']['evidence']['probabilities']
    else:
     native_request={'state':protocol['state'],'question':protocol['question'],'options':protocol['options']}
     save(d/'native-request.json',native_request)
     result=engine.decide(protocol['state'],protocol['question'],options=protocol['options'],images=[raw]);answer=result['answer'];prob=result['probabilities']
    torch.cuda.synchronize();elapsed=time.monotonic()-t
    assert answer in ['YES','NO'] and set(prob)=={'YES','NO'} and abs(sum(prob.values())-1)<0.0001
    assert current and len(current)==1 and len(copies)==1
    save(d/'native-result.json',result);save(d/'forward-trace.json',current);save(d/'raw-readout.json',raw_outputs if raw_outputs else {'scores':result['scores'],'temperature':result['temperature']})
    # Preserve actual runtime tensor bytes remotely, not just processor predictions.
    torch.save(copies[0],d/'actual-forward-inputs.pt')
    save(d/'response.json',{'status':'ok','model':name,'case_id':case['id'],'answer':answer,'probabilities':prob,'elapsed_seconds_including_input_capture':elapsed,'memory':memory(torch),'image_sha256':case['sha256'],'revision':config['revision'],'input_tokens':current[0]['input_ids']['shape'][-1],'image_grid_thw':current[0]['image_grid_thw']['values'],'new_context':True,'output_tokens':0})
    save(d/'admission-after.json',admission(True));completed+=1
   except BaseException:
    save(d/'failure.json',{'error':traceback.format_exc(),'actual_attempted_calls':count,'no_automatic_retry':True});raise
   finally:
    seal={p.name:sha(p) for p in d.iterdir() if p.is_file()};save(d/'seal.json',seal);journal.add('request_sealed',{'case_id':case['id'],'seal_sha256':sha(d/'seal.json'),'complete':(d/'response.json').exists()})
   print(json.dumps({'model':name,'case':case['id'],'completed':completed}),flush=True)
  for handle in handles:handle.remove()
  assert completed==protocol['max_calls_per_model']==count
  after=verify_checkpoint(name,config);assert after==before;save(root/'checkpoint-after.json',after)
  journal.add('completed',{'attempted':count,'completed':completed})
  save(root/'terminal.json',{'status':'completed','model':name,'attempted_calls':count,'complete_replies':completed,'natural_binary_outputs':completed,'output_tokens':0,'GUI_actions':0,'main_model_calls':0,'paid_API_calls':0,'journal_events':journal.seq,'journal_head':journal.head,'time':time.time()})
 except BaseException:
  failure={'status':'technical_failure','phase':phase,'model':name,'attempted_calls':count,'complete_replies':completed,'error':traceback.format_exc(),'time':time.time(),'no_automatic_retry':True}
  if not (root/'terminal.json').exists():save(root/'terminal.json',failure)
  traceback.print_exc();sys.stdout.flush();sys.stderr.flush();raise SystemExit(1)

def launcher():
 assert os.environ['CUDA_VISIBLE_DEVICES']=='4,5,6,7'
 fds=verify_locks();assert sha(ROOT/'protocol.json')==PROTOCOL_SHA
 protocol=json.loads((ROOT/'protocol.json').read_bytes())
 manifest=json.loads((ROOT/'package-manifest.json').read_bytes())
 assert all(sha(ROOT/n)==h for n,h in manifest['files'].items())
 assert not (ROOT/'launch.json').exists() and not (ROOT/'terminal.json').exists()
 save(ROOT/'launch.json',{**identity(os.getpid()),'time':time.time(),'script_sha256':sha(Path(__file__)),'protocol_sha256':PROTOCOL_SHA,'lease_sha256':sha(LEASE),'inherited_lock_fds':list(fds),'max_total_calls':54,'old_queues_started':False})
 (ROOT/'results').mkdir(exist_ok=False);rows=[]
 for name in protocol['model_order']:
  admission(False);config=protocol['models'][name]
  env={**os.environ,'CUDA_VISIBLE_DEVICES':'4','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','PYTHONUNBUFFERED':'1','PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'4','MIRAGE_COMPARISON_MODEL':name}
  argv=[config['python'],'-B','-u',str(Path(__file__).resolve()),'--worker',name]
  log=ROOT/(name+'-worker.log')
  with log.open('xb') as f:
   p=subprocess.Popen(argv,env=env,cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,pass_fds=fds)
   save(ROOT/(name+'-launch.json'),{'pid':p.pid,'argv':argv,'uid':os.getuid(),'time':time.time(),'model':name,'physical_gpu':4})
   code=p.wait()
  r=ROOT/'results'/name
  seal={str(f.relative_to(r)):sha(f) for f in r.rglob('*') if f.is_file()}
  save(ROOT/(name+'-postexit-seal.json'),{'files':seal,'log_sha256':sha(log),'exit_code':code,'time':time.time()})
  rows.append({'model':name,'exit_code':code,'terminal':json.loads((r/'terminal.json').read_bytes()) if (r/'terminal.json').exists() else None})
  save(ROOT/(name+'-exit.json'),{'pid':p.pid,'exit_code':code,'time':time.time()})
  admission(False)
 save(ROOT/'terminal.json',{'status':'completed' if all(r['exit_code']==0 for r in rows) else 'completed_with_technical_failures','models':rows,'attempted_calls':sum((r['terminal'] or {}).get('attempted_calls',0) for r in rows),'complete_replies':sum((r['terminal'] or {}).get('complete_replies',0) for r in rows),'max_calls':54,'GUI_actions':0,'main_model_calls':0,'old_queues_started':False,'time':time.time(),'gpu_after':snapshot()})
 save(ROOT/'terminal-seal.json',{str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name!='terminal-seal.json'})
 print(json.dumps({'terminal':str(ROOT/'terminal.json'),'status':json.loads((ROOT/'terminal.json').read_bytes())['status']}),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--worker',choices=['flash','neohorse','style']);args=parser.parse_args()
 if args.worker:worker(args.worker)
 else:
  try:launcher()
  except BaseException:
   if not (ROOT/'launcher-failure.json').exists():save(ROOT/'launcher-failure.json',{'error':traceback.format_exc(),'time':time.time()})
   traceback.print_exc();sys.stdout.flush();sys.stderr.flush();raise SystemExit(1)
