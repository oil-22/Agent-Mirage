"""Verify root's actual marker-only stop; no health, signals or original writes."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
source=(ROOT/'progress-preparation/progress_remote.py').read_text(encoding='utf8')
tail=r'''
group=Path('/home/researcher/jev-defense-four-gpu-20261106/online-service-group-1793978182501156243')
terminal=group/'terminal-sha256.json'
if not terminal.exists():
    print(json.dumps({'terminal_ready':False,'files':[p.name for p in group.iterdir()if p.is_file()],
        'HTTP_model_GUI_signals':0}));raise SystemExit(0)
mapping=read(terminal)
for name,expected in mapping.items():
    p=(group/name).resolve();assert p.is_relative_to(group.resolve())and not p.is_symlink()and sha(p)==expected
actual={p.relative_to(group).as_posix()for p in group.rglob('*')if p.is_file()and p!=terminal}
assert actual==set(mapping),'Original terminal manifest is not exhaustive'
exited=read(group/'exit.json');assert len(exited['workers'])==2
workers={r['role']:r for r in exited['workers']}
assert set(workers)=={'primary','pplx_flash'}and all(r['exit_code']==0 for r in workers.values())
processes={}
for role in('primary','pplx_flash'):
    expected=read(group/'processes'/f'{role}.json')['identity']
    assert expected==workers[role]['identity']
    processes[role]=identity_record(expected)
    assert not processes[role]['identity_matches']or processes[role].get('phase')in('exited','zombie'), 'Old model worker is still live'
launcher=identity_record(read(group/'process.json'))
assert not launcher['identity_matches']or launcher.get('phase')in('exited','zombie'),'Old launcher remains live'
lease=read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
holder=identity_record(lease['holder']);assert holder['identity_matches']
holder['actual_locks']=lock_records(holder['actual']['pid'],lease);assert len(holder['actual_locks'])==9
lines=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],universal_newlines=True).splitlines()
compute=[{'uuid':line.split(',')[0].strip(),'pid':int(line.split(',')[1])}for line in lines if line.strip()]
owned={row['uuid']for row in lease['gpu']};target=[row for row in compute if row['uuid']in owned]
assert not target,'GPU4-7 still contain compute; report without touching any process'
gpu_lines=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,memory.used','--format=csv,noheader,nounits'],universal_newlines=True).splitlines()
gpus=[]
for line in gpu_lines:
    index,uuid,free,used=[p.strip()for p in line.split(',')]
    if int(index)in(4,5,6,7):gpus.append({'index':int(index),'uuid':uuid,'free_MiB':int(free),'used_MiB':int(used)})
roles={}
for role in('primary','pplx_flash'):
    requests=[sealed_request(p)for p in sorted((group/role/'requests').iterdir())if p.is_dir()]
    roles[role]={'completed':sum(r['status']=='completed'for r in requests),'failed':sum(r['status']=='failed'for r in requests),
        'pending_unsealed':sum(r['status']=='pending_unsealed'for r in requests),
        'native_EOS_complete_replies':sum(r.get('generation',{}).get('last_token_is_native_EOS',False)for r in requests)}
assert roles['primary']=={'completed':72,'failed':1,'pending_unsealed':0,'native_EOS_complete_replies':72}
assert roles['pplx_flash']=={'completed':0,'failed':0,'pending_unsealed':0,'native_EOS_complete_replies':0}
journal=chain_snapshot(group/'journal.jsonl');assert journal['uncommitted_partial_tail_bytes']==0
state=read(group/'online-state.json');assert state['phase']=='terminal_failure'and state['active']is None
marker=read(group/'stop-requested.json');assert marker['no_signals_sent']is True and marker['holder_to_remain_running']is True
logs={role:{'bytes':(group/(role+'.log')).stat().st_size,'sha256':sha(group/(role+'.log'))}for role in roles}
assert all(sha(group/(role+'.log'))==obj['sha256']for role,obj in logs.items())
public={}
for name in('terminal-sha256.json','exit.json','stop-requested.json','online-state.json','journal.jsonl','process.json',
    'primary/stopped.json','pplx_flash/stopped.json'):
    p=group/name;raw=p.read_bytes();public[name]={'sha256':sha(p),'data':base64.b64encode(raw).decode()}
summary={'terminal_ready':True,'actual_model_workers_and_launcher_exited':True,'all_worker_exit_codes_zero':True,
    'group':str(group),'terminal_sha256':sha(terminal),'sealed_files':len(mapping),'sealed_total_bytes':sum((group/n).stat().st_size for n in mapping),
    'all_original_terminal_files_and_inventory_verified':True,'logs_stable':logs,'model_processes':processes,'launcher':launcher,
    'holder_untouched_and_actual9locks':holder,'GPU4_7_target_compute':target,'GPU4_7':gpus,
    'actual_request_counts':roles,'journal':journal,'state':state,'marker_no_signals_verified':True,
    'new_health_HTTP_model_GUI_or_scorer_calls':0,'signals_or_process_management':0,'time':time.time()}
print(json.dumps({'summary':summary,'public_files':public}))
'''
code="__name__='audit_helpers'\n"+source+'\n'+tail
r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','3090',
    '/opt/whz/conda-envs/webmall-vlm/bin/python -B -'],input=code,capture_output=True,text=True,timeout=120)
out=ROOT/('service-poststop-evidence-'+str(time.time_ns()));out.mkdir(exist_ok=False)
(out/'stderr.txt').write_text(r.stderr,encoding='utf8')
if r.returncode:
    (out/'failure.stdout.txt').write_text(r.stdout,encoding='utf8');raise SystemExit(r.returncode)
data=json.loads(r.stdout)
if data.get('terminal_ready')is False:
    (out/'not-ready.json').write_text(json.dumps(data,indent=2),encoding='utf8');print(json.dumps({'local':str(out),**data}));raise SystemExit(2)
for name,item in data['public_files'].items():
    p=out/'original-public'/name;assert p.resolve().is_relative_to(out.resolve());p.parent.mkdir(parents=True,exist_ok=True)
    raw=base64.b64decode(item['data']);assert hashlib.sha256(raw).hexdigest()==item['sha256'];p.write_bytes(raw)
receipt={**data['summary'],'local_evidence':str(out),'inspector_source_sha256':hashlib.sha256(code.encode()).hexdigest(),
    'private_task_auth_token_exported':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
(out/'source.py').write_text(code,encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in out.rglob('*')if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'local':str(out),'receipt_sha256':hashlib.sha256((out/'receipt.json').read_bytes()).hexdigest(),
    'terminal_sha256':receipt['terminal_sha256'],'sealed_files':receipt['sealed_files'],
    'all_worker_exit_codes_zero':True,'target_compute_empty':True,'holder9locks':True,
    'new_health_HTTP_model_GUI_or_scorer_calls':0}))
