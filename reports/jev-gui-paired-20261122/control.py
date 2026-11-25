"""Once-only stage, qualification, leased startup, and read-only inspection."""
import base64
import io
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from prepare import HERE, read, save, sha

SSH = ['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12']
MODEL_PYTHON = '/opt/whz/conda-envs/webmall-vlm/bin/python'
GUI_PYTHON = '/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python'


def remote(host, code, label, *, private_prefix=b'', timeout=60):
    op = ROOT / 'operations' / (str(time.time_ns()) + '-' + label + '-' + host)
    op.mkdir(parents=True, exist_ok=False)
    (op / 'source.py').write_bytes(code.encode())
    executable = MODEL_PYTHON if host == '3090' else GUI_PYTHON
    try:
        result = subprocess.run(SSH + [host, executable + ' -B -'], input=private_prefix + code.encode(),
                                capture_output=True, timeout=timeout)
        (op / 'stdout.bin').write_bytes(result.stdout)
        (op / 'stderr.bin').write_bytes(result.stderr)
        save(op / 'transport.json', {'returncode': result.returncode, 'host': host, 'time': time.time()})
    except subprocess.TimeoutExpired as exc:
        (op / 'stdout.partial.bin').write_bytes(exc.stdout or b'')
        (op / 'stderr.partial.bin').write_bytes(exc.stderr or b'')
        save(op / 'transport.json', {'host': host, 'timeout_seconds': timeout, 'inspect_before_any_follow_up': True})
        raise RuntimeError(f'No response; inspect preserved operation {op} first') from None
    finally:
        save(op / 'seal.json', {p.name: sha(p) for p in op.iterdir() if p.is_file()})
    if result.returncode:
        raise RuntimeError(f'{op}\n' + result.stderr.decode(errors='replace')[-4800:])
    return {'operation': str(op), 'result': json.loads(result.stdout)}


def prefix(host):
    return (f"ROOT={MANIFEST['package'+host]!r}\nEXPECTED={POINTER['manifest_sha256']!r}\n"
            f'HOST={host!r}\nOUTPUT={MANIFEST["output3090"]!r}\n')


def stage(host):
    target = ROOT / ('stage-' + host + '.json')
    assert not target.exists()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in [*MANIFEST['files'], 'manifest.json', 'private.token']:
            archive.writestr(name, (PACKAGE / name).read_bytes())
    payload = b'PAYLOAD=' + repr(base64.b64encode(buf.getvalue())).encode() + b'\n'
    result = remote(host, prefix(host) + r'''
import ast,base64,hashlib,io,json,os,sys,zipfile
from pathlib import Path
assert os.getuid()==(1033 if HOST=='3090'else 1015)
p=Path(ROOT);p.parent.mkdir(parents=True,exist_ok=True);p.mkdir(mode=0o700,exist_ok=False)
old_umask=os.umask(0o077)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD,validate=True)))as z:
 for name in z.namelist():
  out=p/name;assert out.resolve().is_relative_to(p.resolve());out.parent.mkdir(parents=True,exist_ok=True)
  with out.open('xb')as f:f.write(z.read(name))
os.umask(old_umask)
sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import sha
from paired_contract import load_plan
from continuation_guard import verify_native_parent,verify_gui_parent
assert sha(p/'manifest.json')==EXPECTED
m,plan=load_plan(p)
for name,d in m['files'].items():
 assert sha(p/name)==d,name
 if name.endswith('.py'):ast.parse((p/name).read_bytes(),filename=name)
assert sha(p/'private.token')==m['auth_token_sha256'] and (p/'private.token').stat().st_mode & 0o077==0
if m.get('action_envelope_compatibility'):
 from continuation_guard import verify_stage_parent
 proof=verify_stage_parent(p,HOST)
else:
 proof=(verify_native_parent if HOST=='3090'else verify_gui_parent)(p)
print(json.dumps({'runtime':str(p),'manifest_sha256':EXPECTED,'plan_sha256':m['plan_sha256'],'expected':len(plan['queue']),
 'availability_proof':proof,'new_model_GUI_scorer_calls':0}))
''', 'stage-paired-runtime', private_prefix=payload, timeout=85)
    save(target, result)
    return result['result']


def qualify():
    target = ROOT / 'cpu-native-qualification.json'
    assert not target.exists() and all((ROOT / ('stage-' + h + '.json')).exists() for h in ('3090','4090'))
    result = remote('3090', prefix('3090') + r'''
import ast,base64,copy,io,json,os,sys
from pathlib import Path
os.environ.update({'CUDA_VISIBLE_DEVICES':'','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'2'})
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import sha
from paired_contract import CONDITIONS,load_plan,missing_image_request
from gate_core import Frame,NativeHistoryActor
from historical_memory import validate_proof,validate_active_sources
from injection import Episode
from PIL import Image
from transformers import AutoProcessor
assert sha(p/'manifest.json')==EXPECTED
m,plan=load_plan(p)
for condition in CONDITIONS:
 rows=[row for row in plan['queue'] if row['condition']==condition]
 assert len(rows)==20 and sum(row['gate_enabled'] for row in rows[::2])==5
 for a,b in zip(rows[::2],rows[1::2]):
  assert a['pair_id']==b['pair_id'] and a['task_id']==b['task_id'] and a['gate_enabled'] != b['gate_enabled']
old=Path(m['historical_package3090']);verify=list()
def node(path,cls,name):
 tree=ast.parse(path.read_bytes());root=next(x for x in tree.body if isinstance(x,ast.ClassDef)and x.name==cls) if cls else tree
 return ast.dump(next(x for x in root.body if isinstance(x,ast.FunctionDef)and x.name==name),include_attributes=False)
for name in ('__init__','generate'):
 assert node(old/'primary_server.py','NativeActor',name)==node(p/'primary_server.py','NativeActor',name)
for name in ('parse','execute','capture','initial_frame'):
 assert node(old/'gui_experiment.py','LiveAdapter',name)==node(p/'gui_experiment.py','LiveAdapter',name)
binding=json.loads((p/'parent-capacity.json').read_bytes());validate_proof(binding);validate_active_sources(binding,p,sha)
old_group=Path('/data/researcher/jev-defense-four-gpu-20261106/flash-four-mode-scale10-20261116-12/model-attempt-01')
wire=old_group/'primary/requests/00001/wire-request.bin'
assert sha(wire)==json.loads((wire.parent/'seal.json').read_bytes())['wire-request.bin']
historical=json.loads(wire.read_bytes())['body'];entered=historical['messages'][-1]['content'][-1]
assert entered['type']=='image_url'
png=base64.b64decode(entered['image_url']['url'].split(',',1)[1],validate=True)
template=json.loads((p/'actor-template.json').read_bytes()); calls=[]
def call(x):calls.append(copy.deepcopy(x));return 'fixture reply; no generation'
add=[{'type':'text','text':'Task: CPU transport boundary check'},{'type':'text','text':'Current browser screenshot follows. Available tab count: 1.'}]
actor=NativeHistoryActor(template,call,text_blocks=add)
present=Frame.captured(png);reply=missing_image_request(actor,present)
actor.commit({'status':'dispatched','candidate':reply,'frame':present})
old_actor=NativeHistoryActor(template,call,text_blocks=add);old_actor(present)
assert calls[0]==calls[1]
missing=Frame.captured(None);reply=missing_image_request(actor,missing)
assert calls[2]['messages'][1:-1]==actor.history and calls[2]['messages'][-1]['content']==add
actor.commit({'status':'dispatched','candidate':reply,'frame':missing})
missing_image_request(actor,present)
assert calls[3]['messages'][1:-1]==actor.history
processor=AutoProcessor.from_pretrained(json.loads((p/'primary-reference.json').read_bytes())['primary_model'],local_files_only=True,trust_remote_code=True)
def proc(body):
 converted=[]
 for m in body['messages']:
  parts=m['content']if isinstance(m['content'],list)else[{'type':'text','text':m['content']}]
  converted.append({'role':m['role'],'content':[b if b['type']=='text'else{'type':'image','image':Image.open(io.BytesIO(base64.b64decode(b['image_url']['url'].split(',',1)[1]))).convert('RGB')}for b in parts]})
 return processor.apply_chat_template(converted,add_generation_prompt=True,tokenize=True,return_dict=True,
  return_tensors='pt',tools=body.get('tools'),**body['chat_template_kwargs'])
rows=[]
for k,n in ((0,1),(2,1),(3,2)):
 v=proc(calls[k]);assert len(v['image_grid_thw'])==n
 rows.append({'case':['present','missing_current_retains_previous','present_after_missing'][len(rows)],
  'input_tokens':v['input_ids'].shape[-1],'original_image_grids':v['image_grid_thw'].tolist(),
  'current_blocks':[b['type']for b in calls[k]['messages'][-1]['content']]})
for mode in ('silent_drop','blank_replace','stale_replace'):
 a=Episode(mode);first,ledger=a.apply(b'next',step=2,previous_png=b'prev',previous_action={'type':'click'},recapture=False,blank=b'blank')
 assert first=={'silent_drop':None,'blank_replace':b'blank','stale_replace':b'prev'}[mode] and ledger['injected']
 assert a.apply(b'next',step=2,previous_png=b'prev',previous_action={'type':'click'},recapture=True)[0]==b'next'
print(json.dumps({'passed':True,'manifest_sha256':EXPECTED,'trajectories':100,'fixed_pairs':50,
 'same_native_ctor_generate_parser_executor_injection_AST':True,'image_omission_processor_inputs':rows,
 'new_model_calls':0,'new_GUI_actions':0,'new_scorer_calls':0,'GPU_used':False}))
''', 'native-CPU-qualification', timeout=115)
    save(target, result)
    return result['result']


LIVE_ID = r'''
def actual(saved):
 try:
  v=identity(saved['pid'])
 except (FileNotFoundError,ProcessLookupError):return None
 return v if v['state'] not in {'Z','X'} and all(v[k]==saved[k]for k in ['uid','command','start_ticks'])else None
def bound_lock_matches(pid,records,holder):
 out=[]
 for q in records:
  f=Path('/proc',str(pid),'fd',str(q['fd']));info=Path('/proc',str(pid),'fdinfo',str(q['fd']))
  if f.is_symlink()and os.readlink(f)==q['path']and f.stat().st_ino==q['inode'] and 'WRITE '+str(holder)in info.read_text():out.append(q['path'])
 return out
'''


def submit():
    target = ROOT / 'model-submission.json'
    assert not target.exists() and read(ROOT/'cpu-native-qualification.json')['result']['manifest_sha256'] == POINTER['manifest_sha256']
    result = remote('3090', prefix('3090') + r'''
import fcntl,json,os,socket,subprocess,sys,time
from pathlib import Path
p=Path(ROOT);o=Path(OUTPUT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import gpu_snapshot,identity,sha
from continuation_guard import verify_native_parent
assert sha(p/'manifest.json')==EXPECTED and not o.exists()and not(p/'background').exists()
proof=verify_native_parent(p)
s=gpu_snapshot();assert not s['compute']and all(s['gpu'][i]['free_mib']>=23000 for i in range(8)),s
for addr,port in [('192.0.2.11',19202),('127.0.0.1',18342)]:
 with socket.socket()as check:check.bind((addr,port))
with Path('/home/researcher/jev-defense-four-gpu-20261106/inference.lock').open('a')as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
o.parent.mkdir(parents=True,exist_ok=True)
disk=os.statvfs(o.parent);assert disk.f_bavail*disk.f_frsize>64*1024**3
(p/'background').mkdir(exist_ok=False)
argv=['/opt/whz/conda-envs/webmall-vlm/bin/python','-B','-u',str(p/'launch_group.py')]
with(p/'background/launcher.log').open('xb')as f:
 child=subprocess.Popen(argv,cwd=p,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
event={'pid':child.pid,'actual':identity(child.pid),'argv':argv,'manifest_sha256':EXPECTED,'parent_proof':proof,
 'prelaunch_snapshot':s,'startup_is_not_inference':True,'time':time.time()}
with(p/'background/launch.json').open('x')as f:json.dump(event,f);f.flush();os.fsync(f.fileno())
print(json.dumps(event))
''', 'submit-independent-model-lease', timeout=55)
    save(target, result)
    return result['result']


def gui():
    target = ROOT / 'gui-submission.json'
    assert not target.exists() and (ROOT / 'model-submission.json').exists()
    ownership = remote('3090', prefix('3090') + r'''
import json,os,sys,urllib.request
from pathlib import Path
p=Path(ROOT);o=Path(OUTPUT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import gpu_snapshot,identity,sha
''' + LIVE_ID + r'''
def read(q):return json.loads(q.read_bytes())
assert sha(p/'manifest.json')==EXPECTED and not(o/'exit.json').exists()
lease=read(o/'lease.json');pr=read(o/'primary/process.json');fl=read(p/'flash/service/process.json')
assert actual(lease['holder']) and actual(pr) and actual(fl) and lease['manifest_sha256']==EXPECTED
proof={str(proc['pid']):bound_lock_matches(proc['pid'],lease['lock_records'],lease['holder']['pid'])for proc in (pr,fl)}
assert all(len(v)==17 for v in proof.values())
assert read(o/'primary/ready.json')['manifest_sha256']==EXPECTED
assert read(p/'flash/service/ready.json')['pid']==fl['pid']
snap=gpu_snapshot()
for i in range(8):
 assert snap['gpu'][i]['uuid']==lease['gpu'][i]['uuid']
 assert {(v['pid'],v['identity']['uid'])for v in snap['compute']if v['uuid']==snap['gpu'][i]['uuid']}=={(pr['pid']if i<7 else fl['pid'],1033)}
print(json.dumps({'manifest_sha256':EXPECTED,'lease_sha256':sha(o/'lease.json'),'primary':pr,'Flash':fl,'actual_inherited_locks':proof,'snapshot':snap}))
''', 'verify-actual-before-gui', timeout=55)
    result = remote('4090', prefix('4090') + r'''
import fcntl,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import identity,sha
from continuation_guard import verify_gui_parent
from paired_contract import load_plan
assert sha(p/'manifest.json')==EXPECTED
m,plan=load_plan(p);proof=verify_gui_parent(p)
assert not any((p/x).exists()for x in ('control','batch','background','STOP'))
site=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock')
with site.open('a')as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert urllib.request.urlopen('http://192.0.2.10:29980/',timeout=12).status==200
req=urllib.request.Request(m['main_url']+'/health',headers={'Authorization':'Bearer '+(p/'private.token').read_text().strip()})
with urllib.request.urlopen(req,timeout=20)as response:h=json.load(response)
assert h['phase']=='ready'and h['actor_attempts']==h['actor_replies']==h['done']==0 and h['active']is None
assert h['expected']==len(plan['queue'])and h['manifest_sha256']==EXPECTED
(p/'background').mkdir(exist_ok=False)
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(p/'gui_outer.py')]
with(p/'background/outer.log').open('xb')as f:
 child=subprocess.Popen(argv,cwd=p,env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
event={'actual':identity(child.pid),'argv':argv,'time':time.time(),'pre_GUI_health':h,'proof':proof,'first_pair':plan['queue'][:2]}
with(p/'background/launch.json').open('x')as f:json.dump(event,f);f.flush();os.fsync(f.fileno())
print(json.dumps(event))
''', 'submit-isolated-paired-gui', timeout=65)
    save(target, {'verified_model_ownership': ownership, **result})
    return result['result']


def inspect(host):
    value=remote(host, prefix(host) + r'''
import hashlib,json,os,sys
from pathlib import Path
p=Path(ROOT);o=Path(OUTPUT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import identity
''' + LIVE_ID + r'''
paths=([p/'background/launch.json',o/'launcher-process.json',o/'lease.json',o/'primary/process.json',o/'primary/status.json',o/'primary/ready.json',o/'primary/terminal.json',o/'launcher-failure.json',o/'exit.json',p/'flash/service/process.json',p/'flash/service/ready.json',p/'flash/service/terminal.json'] if HOST=='3090' else [p/'background/launch.json',p/'control/process.json',p/'control/runner-process.json',p/'batch/status.json',p/'control/exit.json',p/'GUI-uncaught-failure.json'])
results={}
for q in paths:
 if q.exists():
  r=json.loads(q.read_bytes());results[q.name if q.parent==o else q.parent.name+'/'+q.name]=r
  if {'pid','uid','command','start_ticks'}<=r.keys():results[q.parent.name+'/actual']=actual(r)
lease=results.get('lease.json')
if lease:
 results['inherited_locks']={key:len(bound_lock_matches(r['pid'],lease['lock_records'],lease['holder']['pid']))for key,r in list(results.items())if key.endswith('/actual')and r}
if HOST=='4090':
 actual_outer=results.get('control/actual');site=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock')
 if results.get('control/process.json'):actual_outer=actual(results['control/process.json'])
 if actual_outer:
  st=site.stat();key=f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}'
  results['actual_site_lease']=[r for r in Path('/proc/locks').read_text().splitlines()if key in r and int(r.split()[4])==actual_outer['pid']]
 rows=[]
 for q in (p/'batch/runs').glob('*/attempt-*/terminal.json'):
  t=json.loads(q.read_bytes());rows.append({k:t.get(k)for k in ['run','outcome','official_reward','scoring_status','infrastructure_failure','injection_fired','recaptures','actor_calls','elapsed_monotonic_ns']})
 results['terminals']=rows
else:
 received=[]
 for q in sorted((o/'primary/requests').glob('*/response.json'))[-3:]:
  v=json.loads(q.read_bytes());g=json.loads((q.parent/'actual-generation.json').read_bytes());r=json.loads((q.parent/'wire-request.bin').read_bytes())
  raw=(q.parent/'wire-request.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==v['request_sha256']
  result={'run':r['run_id'],'step':r['decision_index'],'request_id':v['request_id'],'EOS':g['natural_EOS'],'forward_calls':g['actual_forward_calls'],
   'current_image_count':sum(b['type']=='image_url'for b in r['body']['messages'][-1]['content']),
   'reply_sha256':hashlib.sha256(v['text'].encode()).hexdigest()}
  received.append(result)
 results['actual_main_EOS_replies']=received
logs=([p/'background/launcher.log',o/'primary.log',o/'Flash-service.log']if HOST=='3090'else[p/'background/outer.log',p/'control/runner.log'])
def tail(q):
 with q.open('rb')as f:f.seek(max(q.stat().st_size-1400,0));return f.read().decode(errors='replace')
print(json.dumps({'host':HOST,'runtime':ROOT,'records':results,'logs':{q.name:tail(q)for q in logs if q.exists()}}))
''', 'inspect-actual-paired-runtime', timeout=40)
    return value


if __name__ == '__main__':
    POINTER = read(HERE / 'frozen-current.json')
    ROOT = Path(POINTER['root'])
    PACKAGE = Path(POINTER['runtime'])
    assert sha(PACKAGE / 'manifest.json') == POINTER['manifest_sha256']
    MANIFEST = read(PACKAGE / 'manifest.json')
    assert all(sha(PACKAGE / n) == h for n,h in MANIFEST['files'].items())
    options = {'stage': stage, 'qualify': qualify, 'submit': submit, 'gui': gui, 'inspect': inspect}
    result = options[sys.argv[1]](*sys.argv[2:])
    print(json.dumps(result))
