"""Preserve T157's malformed output, then continue the unchanged 100-task panel."""
from pathlib import Path
import json,subprocess,sys
import handoff_and_launch as h
P=Path(__file__).resolve().parent
Q=P.parent/'scale100-resume01'
OLD=h.ROOT
ROOT=OLD+'-resume01'
SSH=['D:/Git/usr/bin/ssh.exe','-o','BatchMode=yes','-o','ConnectTimeout=10']
def remote(host,code,timeout=60,py='python3'):
    r=subprocess.run(SSH+[host,py+' -'],input='ROOT='+repr(ROOT)+'\nOLD='+repr(OLD)+'\n'+code,text=True,capture_output=True,timeout=timeout)
    if r.returncode:raise RuntimeError(host+': '+r.stderr[-3500:]+r.stdout[-1000:])
    return json.loads(r.stdout)

if __name__=='__main__':
    d=remote('3090',h.free_code);assert d['owned_gpus_free'],d
    print(json.dumps(dict(owned_gpus_free=True)),flush=True)
    for host in ['4090','3090']:
        remote(host,"from pathlib import Path\nimport json\np=Path(ROOT);p.mkdir(parents=True,exist_ok=False)\nprint(json.dumps(dict(created=str(p))))")
        r=subprocess.run(['D:/Git/usr/bin/scp.exe','-q','-o','BatchMode=yes',str(Q/'runtime-package.tar.gz'),host+':'+ROOT+'/runtime-package.tar.gz'],capture_output=True,text=True,timeout=90)
        assert r.returncode==0,r.stderr
        code=r'''
from pathlib import Path
import json,tarfile,hashlib
p=Path(ROOT)
with tarfile.open(p/'runtime-package.tar.gz') as archive:
    for member in archive.getmembers():assert member.isfile() and p.resolve() in (p/member.name).resolve().parents
    archive.extractall(p)
manifest=json.loads((p/'deployment-manifest.json').read_text())
for name,digest in manifest.items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,name
(p/'service.token').chmod(0o600);(p/'PRIVATE-evaluator-configs').chmod(0o700)
for f in (p/'PRIVATE-evaluator-configs').iterdir():f.chmod(0o600)
print(json.dumps(dict(verified_files=len(manifest))))
'''
        print(host,remote(host,code,py=h.MODEL_PY if host=='3090' else 'python3'),flush=True)
    test=r'''
import subprocess,json
code="""import run_scale100 as r
from types import SimpleNamespace
env=SimpleNamespace(context=SimpleNamespace(pages=[1]))
for payload in [dict(type='click',x=[605,419]),dict(type='click',x=605),dict(type='tab',index=[0])]:
    try:r.execute(env,payload,'schema regression only')
    except ValueError as error:assert 'Invalid native action payload' in str(error)
    else:raise AssertionError('malformed action was accepted')
action,obs,info,feedback=r.execute(env,dict(type='stop',answer='test'),'schema regression only')
assert obs is None and info is None and feedback==''
tasks=__import__('json').loads((r.P/'tasks.json').read_text());task=next(t for t in tasks if t['reference_image_paths'])
raw=(r.P/task['reference_image_paths'][0]).read_bytes();body=r.body_for([],task,env,'',raw)
assert r.replace_current(body,None)['messages'][1]==body['messages'][1]
print('SCHEMA_AND_REFERENCE_OK')
"""
r=subprocess.run([PY,'-c',code],cwd=ROOT,text=True,capture_output=True,timeout=60)
assert r.returncode==0,(r.stdout[-500:],r.stderr[-1500:])
print(json.dumps(dict(schema_checks=4,reference_preservation=True,actor_calls=0,environment_actions=0)))
'''
    test_result=remote('4090','PY='+repr(h.GUI_PY)+'\n'+test,timeout=75)
    (Q/'recovery-tests.json').write_text(json.dumps(test_result,indent=2));print(json.dumps(test_result),flush=True)
    ledger=r'''
from pathlib import Path
import json,hashlib,time,collections
old=Path(OLD);p=Path(ROOT);out=old/'gui-output'
pid=json.loads((old/'gui-launch-receipt.json').read_text())['pid'];proc=Path('/proc')/str(pid)/'stat'
assert not proc.exists() or proc.read_text().split()[2]=='Z'
folder=out/'T157/clean';failure=json.loads((out/'failure.json').read_text())
assert 'TypeError: float() argument must be a string or a real number' in failure['error']
assert len(list(folder.glob('*-response.json')))==1 and not (folder/'terminal.json').exists()
response=json.loads((folder/'001-response.json').read_text());action=json.loads((folder/'001-action.json').read_text())
assert action['payload']==dict(type='click',x=[605,419]) and response['natural_EOS']
terminal=dict(outcome='native_action_contract_failure',steps=1,reward=None,reward_status='not evaluated: original controller exited before scoring',covered_bins=[],uncovered_bins=[2000,5000,10000,20000,40000],checkpoints=[],semantic_labels='format failure only; not an Agent-Mirage event label',recovered_after_controller_crash=True,original_failure_time=failure['time'],recovered_at=time.time(),source_response_sha256=hashlib.sha256((folder/'001-response.json').read_bytes()).hexdigest(),executed_environment_actions=0)
(folder/'terminal.json').write_text(json.dumps(terminal,indent=2))
(out/'recovery-disposition.json').write_text(json.dumps(dict(task_id=157,batch_failure='uncaught malformed action TypeError',task_outcome='native_action_contract_failure',regeneration=False,action_coercion=False,score_imputed=False,time=time.time()),indent=2))
rows=json.loads((old/'reuse-ledger.json').read_text())['completed_natural_trajectories']
for f in sorted(out.glob('T*/clean/terminal.json')):
    t=json.loads(f.read_text());tid=int(f.parent.parent.name[1:])
    assert t['outcome'] in ['model_stop','step_cap','native_parse_failure','native_action_contract_failure']
    rows.append(dict(task_id=tid,clean_path=str(f.parent),terminal_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_root=OLD,outcome=t['outcome'],steps=t['steps'],model_protocol_equal=True))
assert len(rows)==len({r['task_id'] for r in rows})==80
cfg=json.loads((p/'config.json').read_text());oldcfg=json.loads((old/'config.json').read_text())
for key in ['task_ids','bins','tolerance','max_steps','model','quantization','placement_overrides']:assert cfg[key]==oldcfg[key],key
for name in ['actor-template.json','native-parser-source.py','tasks.json']:assert (p/name).read_bytes()==(old/name).read_bytes(),name
result=dict(created_at=time.time(),completed_natural_trajectories=rows,resumed_from=OLD,remaining_task_ids=[tid for tid in cfg['task_ids'] if tid not in {r['task_id'] for r in rows}],counting='task trajectories ending in natural stop, step cap, or explicit model format failure; report categories separately; no repeat of a failed output',outcomes=dict(collections.Counter(r['outcome'] for r in rows)))
(p/'reuse-ledger.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''
    rec=remote('4090',ledger);(Q/'reuse-ledger.json').write_text(json.dumps(rec,indent=2))
    r=subprocess.run(['D:/Git/usr/bin/scp.exe','-q','-o','BatchMode=yes',str(Q/'reuse-ledger.json'),'3090:'+ROOT+'/reuse-ledger.json'],capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr
    print(json.dumps(dict(outcomes=rec['outcomes'],remaining_task_ids=rec['remaining_task_ids'])),flush=True)
    for host,kind,py in [('3090','model',h.MODEL_PY),('4090','gui',h.GUI_PY)]:
        launch=remote(host,'KIND='+repr(kind)+'\nPY='+repr(py)+'\n'+h.launch)
        (Q/(kind+'-launch-receipt.json')).write_text(json.dumps(launch,indent=2))
        print(json.dumps(dict(host=host,pid=launch['pid'],script=launch['script'])),flush=True)
    (P/'active-run.json').write_text(json.dumps(dict(local_root=str(Q),remote_root=ROOT,resumed_from=OLD),indent=2))
