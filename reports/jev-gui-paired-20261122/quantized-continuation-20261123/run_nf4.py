"""Freeze, stage, and run only the 37 still untouched pairs on a 3+1 lease."""
import ast
import hashlib
import json
import secrets
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import control
from prepare import edit, read, save, sha

CURRENT = HERE/'current.json'
V2_POINTER = HERE.parent/'action-envelope-repair/linked-current.json'
V2_SHA = '71070ef222926791fc85af8ddb7d1e6f59d7233657cdf3de9d9f224b1759d50e'
CUT = 26


def freeze():
    assert not CURRENT.exists(), 'Inspect the existing generation; do not re-stage it.'
    v2 = read(V2_POINTER); parent = Path(v2['runtime'])
    assert sha(parent/'manifest.json') == v2['manifest_sha256'] == V2_SHA
    old = read(parent/'manifest.json')
    assert all(sha(parent/n)==h for n,h in old['files'].items())
    case = 'paper-paired-nf4-three-plus-flash-' + str(time.time_ns())
    root = HERE/case; root.mkdir(exist_ok=False)
    p = root/'runtime'; p.mkdir()
    for name in old['files']:
        dest = p/name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(parent/name, dest)
    (p/'private.token').write_text(secrets.token_hex(32) + '\n', encoding='ascii')
    for name in ('continuation_guard.py','nf4_runtime.py','tensor_archive.py'):
        shutil.copyfile(HERE/name,p/name)

    full = read(p/'parent-full-plan.json')
    old_plan = read(p/'plan.json')
    assert len(full['queue'])==100 and old_plan['queue']==full['queue'][22:]
    plan = {**old_plan,'queue':full['queue'][CUT:]}
    assert len(plan['queue']) == 74 and all(a['pair_id']==b['pair_id'] and a['gate_enabled']!=b['gate_enabled']
               for a,b in zip(plan['queue'][::2],plan['queue'][1::2]))
    (p/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    cut = read(p/'action-envelope-cutover.json')
    v1 = read(parent.parent/'v1-release-cross-host-binding.json')
    assert v1['both_host_terminal_sha256_equal'] and v1['parent_original_prefix']==22
    save(p/'quantized-parent.json', {
        'original': {**cut['parent_runtime'], 'manifest_sha256':cut['parent_manifest_sha256'],
                     'plan_sha256':cut['parent_plan_sha256'], 'output3090':cut['parent_model_output'],
                     'terminals_scored':v1['model']['result']['terminals']},
        'envelope':{'3090':old['package3090'],'4090':old['package4090'], 'manifest_sha256':V2_SHA,
                    'plan_sha256':old['plan_sha256'], 'output3090':old['output3090']}})
    edit(p/'paired_contract.py',[("    split = cut['prefix_count']","    assert cut['prefix_count'] == 22\n    split = m['preserved_prefix_count']\n    assert split == 26")])

    device_map={k:(0 if v < 8 else 1 if v < 37 else 2) for v in range(64) for k in [f'model.language_model.layers.{v}']}
    device_map.update({k:0 for k in ('model.visual','model.language_model.embed_tokens','model.language_model.rotary_emb')})
    device_map.update({'model.language_model.norm':2,'lm_head':2})
    assert device_map.keys() == read(p/'explicit-placement.json')['device_map'].keys()
    save(p/'quantized-placement.json',{'device_map':device_map,'primary_physical_gpus':[0,1,2],
         'Flash_physical_gpu':3,'NF4_compute_dtype':'bfloat16','CPU_disk_offload':False})
    cfg=p/'flash/service-config.json'
    v=read(cfg); assert v['physical_gpu']==7
    cfg.write_text(json.dumps({**v,'physical_gpu':3},ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    edit(p/'flash/resource_guard.py',[
        ('Fresh eight-GPU lease only','Fresh four-GPU lease only'),
        ('if len(fds) != 17 or', "if [r['index'] for r in lease['gpu']] != [0,1,2,3] or len(fds) != 9 or"),
        ("            compute.append({'uuid': u, 'pid': int(p), 'used_mib': m, 'identity': identity(int(p))})",
         "            try: owner = identity(int(p))\n            except OSError: owner = None\n            compute.append({'uuid': u, 'pid': int(p), 'used_mib': m, 'identity': owner})"),
        ('if index != 7 or uuid', 'if index != 3 or uuid'),
        ("    pids = {r['pid'] for r in snapshot['compute'] if r['uuid'] == uuid}",
         "    pids = {r['pid'] if r['identity'] and r['identity']['uid']==1033 else -1 for r in snapshot['compute'] if r['uuid'] == uuid}")])
    edit(p/'expanded_guard.py',[
        ('Actual eight-card','Actual four-card'),
        ('range(7)}, 7:', 'range(3)}, 3:'),
        ("pids = {r['pid'] for r in snapshot['compute'] if r['uuid'] == cards[index]['uuid']}",
         "pids = {r['pid'] if r['identity'] and r['identity']['uid']==1033 else -1 for r in snapshot['compute'] if r['uuid'] == cards[index]['uuid']}"),
        ('for i in range(7)):', 'for i in range(3)):'),
        ("list(range(7)), 'Flash_physical_gpu': 7", "list(range(3)), 'Flash_physical_gpu': 3")])
    edit(p/'launch_group.py',[
        ('new eight-GPU','new four-GPU'),
        ("        if before['compute'] or any(before['gpu'][i]['free_mib'] < 23000 for i in range(8)):",
         "        indexes = [0,1,2,3]\n        uuids = {before['gpu'][i]['uuid'] for i in indexes}\n        if any(row['uuid'] in uuids for row in before['compute']) or any(before['gpu'][i]['free_mib'] < 23000 for i in indexes):"),
        ('Eight empty task-allocatable GPUs','Four empty task-allocatable GPUs'),
        (Path(old['package3090']).name+'.lock', case+'.lock'),
        ('for i in range(8) for directory', 'for i in indexes for directory'),
        ("if after['compute'] or any(after['gpu'][i]['free_mib'] < 23000 or after['gpu'][i]['uuid'] != before['gpu'][i]['uuid'] for i in range(8)):",
         "if any(row['uuid'] in uuids for row in after['compute']) or any(after['gpu'][i]['free_mib'] < 23000 or after['gpu'][i]['uuid'] !=before['gpu'][i]['uuid'] for i in indexes):"),
        ("**after['gpu'][i]} for i in range(8)", "**after['gpu'][i]} for i in indexes"),
        ("'CUDA_VISIBLE_DEVICES': '7'", "'CUDA_VISIBLE_DEVICES': after['gpu'][3]['uuid']"),
        ("'CUDA_VISIBLE_DEVICES': '0,1,2,3,4,5,6'", "'CUDA_VISIBLE_DEVICES': ','.join(after['gpu'][i]['uuid'] for i in indexes[:3])"),
        ("'eight_reserved_GPU_cost_must_be_reported': True", "'reserved_GPUs_for_run_cost': 4")])

    # The archived BF16 proof still validates its original file hashes and seven-card result.
    # Update only the placement admission for installation onto this three-card process.
    edit(p/'historical_memory.py',[("{str(v.gate_proj.weight.device) for v in layers} == {'cuda:' + str(i) for i in range(7)}",
        "{str(v.gate_proj.weight.device) for v in layers} == {'cuda:' + str(i) for i in range(3)}")])
    edit(p/'primary_server.py',[
        ('from transformers import AutoProcessor,AutoModelForImageTextToText',
         'from transformers import AutoProcessor,AutoModelForImageTextToText,BitsAndBytesConfig\n        import bitsandbytes as bnb\n        import nf4_runtime'),
        ('for device in range(7):torch.cuda.set_per_process_memory_fraction(0.87,device)',
         'for device in range(3):torch.cuda.set_per_process_memory_fraction(0.94,device)'),
        ("'fraction_per_primary_GPU':0.87", "'fraction_per_primary_GPU':0.94"),
        ("        self.engine.model=AutoModelForImageTextToText.from_pretrained(model,dtype=torch.bfloat16,attn_implementation='sdpa',device_map=json.loads((P/'explicit-placement.json').read_bytes())['device_map'],max_memory={i:'20GiB'for i in range(7)},local_files_only=True,trust_remote_code=True).eval()",
         "        placement=json.loads((P/'quantized-placement.json').read_bytes())['device_map']\n        self.engine.model,quant=nf4_runtime.load(model,placement,torch,bnb,AutoModelForImageTextToText,BitsAndBytesConfig)"),
        ("        actual=[{'name':n,'shape':list(t.shape),'dtype':str(t.dtype),'device':str(t.device),'bytes':t.numel()*t.element_size()}for n,t in self.engine.model.state_dict().items()]\n        state=support.validate_native_state_records(actual,json.loads((meta/'meta-state.json').read_bytes()))",
         "        actual,quant_state,state=nf4_runtime.audit(self.engine.model,json.loads((meta/'meta-state.json').read_bytes()),placement,torch,bnb)\n        save(root/'quantization-state.json',quant_state)"),
        ("        placement=json.loads((P/'explicit-placement.json').read_bytes())['device_map'];assert ''not in placement", "        assert ''not in placement"),
        ("['cuda:'+str(i)for i in range(7)]", "['cuda:'+str(i)for i in range(3)]"),
        ("'physical_gpus':list(range(7)),'dtype':'bfloat16'", "'physical_gpus':list(range(3)),'dtype':'NF4 weights; BF16 compute','quantization':quant.to_dict(),'bitsandbytes':bnb.__version__"),
        ("['primary_allocator_memory_fraction']=0.87", "['primary_allocator_memory_fraction']=0.94"),
        ("            c=v.detach().cpu().contiguous();data=c.view(torch.uint8).numpy().tobytes();p=folder/(name+'.tensor')\n            from evidence_store import store\n            source=folder/prepared[name.removeprefix('first_forward_')]['file']if name.startswith('first_forward_')and name.removeprefix('first_forward_')in prepared else None\n            storage=store(p,data,source)\n            return {'shape':list(c.shape),'dtype':str(c.dtype),'bytes':len(data),'sha256':digest(data),'file':p.name,'storage':storage}",
         "            c=v.detach().cpu().contiguous();data=memoryview(c.view(torch.uint8).numpy()).cast('B');raw_sha=digest(data)\n            from tensor_archive import store\n            prior=prepared.get(name.removeprefix('first_forward_')) if name.startswith('first_forward_') else None\n            file,storage=store(folder,name,data,raw_sha,self.root/'tensor-blobs',prior)\n            return {'shape':list(c.shape),'dtype':str(c.dtype),'bytes':len(data),'sha256':raw_sha,'file':file,'storage':storage}"),
        ("        installation=install_historical(native,P,root,save,sha,resource)",
         "        from mlp_lifetime import prepare as check_mlp\n        mlp_check=root/'NF4-MLP-memory-check';mlp_check.mkdir()\n        check_mlp(native.torch,sys.modules[type(native.engine.model).__module__],native.engine.model,mlp_check,save,sha)\n        installation=install_historical(native,P,root,save,sha,resource)"),
        ("        state('ready')\n        class Handler", "        from nf4_runtime import qualify\n        state('NF4_full_history_capacity')\n        if stop.is_set():raise RuntimeError('Manual stop before capacity probe')\n        capacity=qualify(native,P,root,save,sha,resource,journal)\n        if stop.is_set():raise RuntimeError('Manual stop before GUI')\n        state('ready')\n        class Handler"),
        ("'URL':'http://192.0.2.11:19202','time':time.time()}",
         "'URL':'http://192.0.2.11:19202','time':time.time(),'capacity_seal_sha256':capacity['seal_sha256'],'NF4_capacity_passed':True}")])

    changes = {'continuation_guard.py','paired_contract.py','plan.json','flash/service-config.json','flash/resource_guard.py',
               'expanded_guard.py','launch_group.py','historical_memory.py','primary_server.py'}
    assert all(sha(p/n) == h for n,h in old['files'].items() if n not in changes)
    files = {q.relative_to(p).as_posix():sha(q) for q in sorted(p.rglob('*')) if q.is_file() and q.name!='private.token'}
    for n in files:
        if n.endswith('.py'):ast.parse((p/n).read_bytes(),filename=n)
    manifest = {**old,'files':files,'trajectories':74,'plan_sha256':sha(p/'plan.json'),
                'preserved_prefix_count':CUT,'pair_precision':'27B NF4 double quantization, BF16 compute',
                'primary_physical_gpus':[0,1,2],'Flash_physical_gpu':3,'auth_token_sha256':sha(p/'private.token'),
                'package3090':f'/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/{case}',
                'package4090':f'/data/researcher/jev-defense-four-gpu-20261106/{case}/runtime',
                'output3090':f'/data/researcher/jev-defense-four-gpu-20261106/{case}/model-attempt-01'}
    save(p/'manifest.json',manifest)
    ptr={'root':str(root),'runtime':str(p),'manifest_sha256':sha(p/'manifest.json'),
         'plan_sha256':manifest['plan_sha256'],'preserved_BF16_prefix':26,'new_NF4_trajectories':74,
         'first_pair':[row['run_id'] for row in plan['queue'][:2]]}
    save(CURRENT,ptr)
    return ptr


def setup():
    control.POINTER=read(CURRENT)
    control.ROOT=Path(control.POINTER['root']);control.PACKAGE=Path(control.POINTER['runtime'])
    assert sha(control.PACKAGE/'manifest.json')==control.POINTER['manifest_sha256']
    control.MANIFEST=read(control.PACKAGE/'manifest.json')
    assert all(sha(control.PACKAGE/n)==h for n,h in control.MANIFEST['files'].items())


def qualify_storage():
    sys.path.insert(0, str(control.PACKAGE))
    import tensor_archive as arc
    from io import BytesIO
    gen=lambda x:hashlib.sha256(x).hexdigest()
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp); blobs=p/'blobs'; raw=memoryview(b'a'*arc.CHUNK+b'last')
        f,s=arc.store(p,'prepared_pixel_values',raw,gen(raw),blobs)
        g,_=arc.store(p,'first_forward_pixel_values',raw,gen(raw),blobs,{'file':f,'sha256':gen(raw),'bytes':len(raw),'storage':s})
        new=memoryview(b'a'*arc.CHUNK+b'next'); n,_=arc.store(p,'next_image',new,gen(new),blobs)
        result=BytesIO(); assert arc.reconstruct(p/g,blobs,result)==gen(raw) and result.getvalue()==raw
        assert arc.reconstruct(p/n,blobs)==gen(new) and len(list(blobs.glob('*/*')))==3
    value={'archive_raw_roundtrip_and_prefix_reuse':True,'prepared_forward_byte_binding':True,
           'paired_plan_full_suffix':True,'vision_Flash_prompt_injection_GUI_scorer_native_backend_byte_identical':True,
           'model_or_GUI_calls':0}
    save(control.ROOT/'static-qualification.json',value)
    return value


def cross_parent():
    target=control.ROOT/'parent-prefix-cross-host.json'
    model=read(control.ROOT/'stage-3090.json')['result']
    gui=read(control.ROOT/'stage-4090.json')['result']
    assert model['manifest_sha256']==gui['manifest_sha256']==control.POINTER['manifest_sha256']
    m=model['availability_proof']; g=gui['availability_proof']
    assert len(m['native_BF16']['terminals_scored'])==22 and len(m['envelope_BF16']['terminals_scored'])==3
    assert all(m[k]['terminals_scored']==g[k]['terminals_scored'] for k in ('native_BF16','envelope_BF16'))
    value={'scored_terminal_sha256s_match_both_hosts':25,'unscored_technical_terminal_sha256':g['envelope_BF16']['technical_terminal_sha256'],
           'unscored_technical_wire_seal_sha256':m['envelope_BF16']['technical_request_seal_sha256'],
           'preserved_prefix':26,'unstarted_suffix':74}
    save(target,value)
    return value


def submit():
    target=control.ROOT/'model-submission.json'
    assert not target.exists() and read(control.ROOT/'static-qualification.json')['archive_raw_roundtrip_and_prefix_reuse']
    assert read(control.ROOT/'parent-prefix-cross-host.json')['scored_terminal_sha256s_match_both_hosts']==25
    result=control.remote('3090', control.prefix('3090')+r'''
import fcntl,json,os,socket,subprocess,sys,time
from pathlib import Path
p=Path(ROOT);o=Path(OUTPUT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import gpu_snapshot,identity,sha
from continuation_guard import verify_native_parent
assert sha(p/'manifest.json')==EXPECTED and not o.exists() and not(p/'background').exists()
proof=verify_native_parent(p)
s=gpu_snapshot(); uuid={s['gpu'][i]['uuid'] for i in range(4)}
assert all(s['gpu'][i]['free_mib']>=23000 for i in range(4)) and not any(v['uuid'] in uuid for v in s['compute'])
for addr,port in [('192.0.2.11',19202),('127.0.0.1',18342)]:
 with socket.socket() as check:check.bind((addr,port))
with Path('/home/researcher/jev-defense-four-gpu-20261106/inference.lock').open('a') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
o.parent.mkdir(parents=True,exist_ok=True)
disk=os.statvfs(o.parent);assert disk.f_bavail*disk.f_frsize>64*1024**3
(p/'background').mkdir(exist_ok=False)
argv=['/opt/whz/conda-envs/webmall-vlm/bin/python','-B','-u',str(p/'launch_group.py')]
with(p/'background/launcher.log').open('xb')as f:
 child=subprocess.Popen(argv,cwd=p,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
event={'pid':child.pid,'actual':identity(child.pid),'argv':argv,'manifest_sha256':EXPECTED,
       'startup_is_not_inference':True,'time':time.time(),'exclusive_selected_physical_cards':[0,1,2,3]}
with(p/'background/launch.json').open('x')as f:json.dump(event,f);f.flush();os.fsync(f.fileno())
print(json.dumps(event))
''','submit-quantized-model-leases')
    save(target,result)
    return result['result']


def model_proof():
    return control.remote('3090',control.prefix('3090')+r'''
import json,os,sys
from pathlib import Path
p=Path(ROOT);o=Path(OUTPUT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import identity,sha,gpu_snapshot
'''+control.LIVE_ID+r'''
def read(p):return json.loads(p.read_bytes())
assert not (o/'exit.json').exists() and sha(p/'manifest.json')==EXPECTED
lease=read(o/'lease.json');pr=read(o/'primary/process.json');fl=read(p/'flash/service/process.json')
assert all(actual(v) for v in (lease['holder'],pr,fl)) and lease['manifest_sha256']==EXPECTED
checks={str(v['pid']):bound_lock_matches(v['pid'],lease['lock_records'],lease['holder']['pid']) for v in (pr,fl)}
assert all(len(v)==9 for v in checks.values())
r=read(o/'primary/ready.json');assert r['manifest_sha256']==EXPECTED and r['NF4_capacity_passed']
f=read(p/'flash/service/ready.json');assert f['pid']==fl['pid'] and f['independent_single_image']
c=o/'primary/capacity';assert sha(c/'seal.json')==r['capacity_seal_sha256']
for name,h in read(c/'seal.json').items():assert sha(c/name)==h,name
q=read(c/'qualification.json'); assert q['passed'] and q['input_tokens']==53167 and q['identical_complete_native_input_bytes_to_BF16']
state=read(o/'primary/loaded.json');assert state['native_state']['quantized_language_linear_modules']==496
s=gpu_snapshot();own=[]
for i in range(4):
 card=s['gpu'][i]; assert card['uuid']==lease['gpu'][i]['uuid']
 compute=[v for v in s['compute'] if v['uuid']==card['uuid']]
 assert len(compute)==1 and compute[0]['pid']==(pr['pid'] if i<3 else fl['pid']) and compute[0]['identity']['uid']==1033
 own.append({'gpu':i,'free_mib':card['free_mib'],'pid':compute[0]['pid'],'uid':1033})
print(json.dumps({'capacity':q,'lease_sha256':sha(o/'lease.json'),'lock_count_per_child':9,'cards':own,
 'loaded':state,'capacity_seal_sha256':r['capacity_seal_sha256'],'primary':pr,'Flash':fl}))
''','verify-quantized-ready-capacity-and-ownership',timeout=55)


def gui():
    target=control.ROOT/'gui-submission.json'
    assert not target.exists() and (control.ROOT/'model-submission.json').exists()
    ownership=model_proof()
    result=control.remote('4090',control.prefix('4090')+r'''
import fcntl,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import identity,sha
from continuation_guard import verify_gui_parent,SITE
from paired_contract import load_plan
assert sha(p/'manifest.json')==EXPECTED
m,plan=load_plan(p);proof=verify_gui_parent(p)
assert not any((p/x).exists() for x in ('control','batch','background','STOP'))
with SITE.open('a') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert urllib.request.urlopen('http://192.0.2.10:29980/',timeout=12).status==200
req=urllib.request.Request(m['main_url']+'/health',headers={'Authorization':'Bearer '+(p/'private.token').read_text().strip()})
with urllib.request.urlopen(req,timeout=20)as response:h=json.load(response)
assert h['phase']=='ready' and h['actor_attempts']==h['actor_replies']==h['done']==0 and h['active'] is None
assert h['expected']==len(plan['queue'])==74 and h['manifest_sha256']==EXPECTED
(p/'background').mkdir(exist_ok=False)
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(p/'gui_outer.py')]
with(p/'background/outer.log').open('xb')as f:
 child=subprocess.Popen(argv,cwd=p,env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
event={'actual':identity(child.pid),'argv':argv,'time':time.time(),'pre_GUI_health':h,'first_pair':plan['queue'][:2]}
with(p/'background/launch.json').open('x')as f:json.dump(event,f);f.flush();os.fsync(f.fileno())
print(json.dumps(event))
''','submit-nf4-untouched-gui-pairs',timeout=60)
    save(target,{'verified_actual_model_and_capacity':ownership,**result})
    return result['result']


if __name__=='__main__':
    verb,*args=sys.argv[1:]
    if verb=='freeze':
        output=freeze()
    else:
        setup()
        actions={'stage':control.stage,'cross':cross_parent,'qualify':qualify_storage,'submit':submit,
                 'verify-model':model_proof,'gui':gui,'inspect':control.inspect}
        output=actions[verb](*args)
    print(json.dumps(output,ensure_ascii=False))
