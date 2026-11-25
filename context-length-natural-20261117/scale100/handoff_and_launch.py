"""Finish the current five-task main phase, freeze compatible reuse, launch scale100."""
from pathlib import Path
import json, subprocess, time
from deploy_scale100 import remote, ROOT

P=Path(__file__).resolve().parent
OLD='/data/researcher/context-length-natural-20261117/batch01'
MODEL_PY='/opt/whz/conda-envs/webmall-vlm/bin/python'
GUI_PY='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python'

boundary=r'''
from pathlib import Path
import json,time
p=Path(OLD);o=p/'gui-output'
s=json.loads((o/'status.json').read_text())
done=(o/'T131/clean/terminal.json').exists() or (o/'initial-phase-completed.json').exists()
if done and not (p/'STOP').exists():
    (p/'STOP').write_text('Expanded to 100 unique tasks; preserve completed main trajectories and defer continuations.\n')
    (p/'scale100-handoff.json').write_text(json.dumps(dict(time=time.time(),reason='user expanded to 100 unique natural trajectories',continuations='deferred',status_at_handoff=s)))
rec=json.loads((p/'gui-launch-receipt.json').read_text());proc=Path('/proc')/str(rec['pid'])/'stat'
alive=proc.exists() and proc.read_text().split()[2]!='Z'
print(json.dumps(dict(phase=s.get('phase'),task=s.get('task'),step=s.get('step'),clean_terminals=len(list(o.glob('T*/clean/terminal.json'))),boundary_reached=done,alive=alive)))
'''

ledger_code=r'''
from pathlib import Path
import json,hashlib,time
p=Path(ROOT);cfg=json.loads((p/'config.json').read_text());tasks={t['task_id']:t for t in json.loads((p/'tasks.json').read_text())}
rows=[];excluded=[]
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def norm(v):
    if isinstance(v,dict):return {k:norm(x) for k,x in v.items() if k!='storage_state'}
    if isinstance(v,list):return [norm(x) for x in v]
    if isinstance(v,str):return v.replace('192.0.2.10:19980','192.0.2.10:29980')
    return v
for root in [Path('/data/researcher/context-length-pilot-20261117/quant-nf4-02'),Path(OLD)]:
    oldcfg=json.loads((root/'config.json').read_text())
    keys=['model','bins','tolerance','max_steps','conditions','quantization','placement_from','placement_overrides','defense_enabled','capture','controls_mask']
    mismatches=[k for k in keys if cfg[k]!=oldcfg[k]]
    assert not mismatches,dict(root=str(root),config_mismatches=mismatches)
    assert sha(p/'actor-template.json')==sha(root/'actor-template.json')
    assert sha(p/'native-parser-source.py')==sha(root/'native-parser-source.py')
    oldtasks={t['task_id']:t for t in json.loads((root/'tasks.json').read_text())}
    for f in sorted((root/'gui-output').glob('T*/clean/terminal.json')):
        tid=int(f.parent.parent.name[1:]);term=json.loads(f.read_text())
        if tid not in tasks or term['outcome'] not in ['model_stop','step_cap']:
            excluded.append(dict(task_id=tid,root=str(root),reason='outside panel or incomplete natural termination'));continue
        assert not any(r['task_id']==tid for r in rows),'duplicate task'
        for key in ['intent','image','sites','require_reset']:assert tasks[tid][key]==oldtasks[tid][key],(tid,key)
        oldprivate=json.loads((f.parent.parent/'PRIVATE-evaluation.json').read_text())
        newprivate=json.loads((p/'PRIVATE-evaluator-configs'/f'T{tid:03}.json').read_text())
        a,b=norm(oldprivate),norm(newprivate)
        diffs=[k for k in set(a)|set(b) if a.get(k)!=b.get(k)]
        assert not diffs,dict(task_id=tid,private_config_different_field_names=diffs)
        assert len(list(f.parent.glob('*-response.json')))==term['steps']
        rows.append(dict(task_id=tid,clean_path=str(f.parent),terminal_sha256=sha(f),source_root=str(root),outcome=term['outcome'],steps=term['steps'],public_inputs_equal=True,evaluator_config_equal_except_storage_state=True,model_protocol_equal=True,actor_template_sha256=sha(root/'actor-template.json')))
out=dict(created_at=time.time(),completed_natural_trajectories=rows,excluded=excluded,counting='one complete main trajectory per unique task; no branches or diagnostics',old_branch_continuations='preserved separately; not counted')
(p/'reuse-ledger.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
'''

free_code=r'''
from pathlib import Path
import subprocess,json,socket
p=Path(OLD);r=json.loads((p/'model-launch-receipt.json').read_text());proc=Path('/proc')/str(r['pid'])/'stat'
alive=proc.exists() and proc.read_text().split()[2]!='Z'
rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
g=[dict(index=int(a),uuid=b.strip(),free_mib=int(c)) for a,b,c in [s.split(',') for s in rows.splitlines()] if int(a) in [4,5,6,7]]
apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
free=not alive and len(g)==4 and min(x['free_mib'] for x in g)>23000 and not any(x['uuid'] in apps for x in g)
if free:
    sock=socket.socket();sock.bind(('192.0.2.11',19319));sock.close()
print(json.dumps(dict(old_model_alive=alive,owned_gpus_free=free,gpus=g)))
'''

launch=r'''
from pathlib import Path
import subprocess,os,json,time,fcntl
p=Path(ROOT);assert not (p/(KIND+'-output')).exists();assert not (p/(KIND+'-launch-receipt.json')).exists()
if KIND=='gui':
    lease=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock').open('a')
    fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);lease.close()
env=os.environ.copy();env.update(PYTHONUNBUFFERED='1',TOKENIZERS_PARALLELISM='false')
if KIND=='model':
    env.update(CUDA_VISIBLE_DEVICES='4,5,6,7',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
    script='model_service.py'
else:script='run_scale100.py'
with (p/(KIND+'.log')).open('ab',buffering=0) as log:
    child=subprocess.Popen([PY,'-u',str(p/script)],cwd=p,env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
d=dict(pid=child.pid,time=time.time(),kind=KIND,script=script,task_ids=json.loads((p/'config.json').read_text())['task_ids'],physical_gpus=[4,5,6,7] if KIND=='model' else [],batch=ROOT)
(p/(KIND+'-launch-receipt.json')).write_text(json.dumps(d))
print(json.dumps(d))
'''

if __name__=='__main__':
    last=None
    for _ in range(720):
        d=remote('4090','OLD='+repr(OLD)+'\n'+boundary)
        if d!=last:print(json.dumps(d),flush=True);last=d
        if not d['alive']:break
        time.sleep(2)
    else:raise TimeoutError('Old batch did not reach handoff boundary')
    for _ in range(90):
        d=remote('3090','OLD='+repr(OLD)+'\n'+free_code)
        if d['owned_gpus_free']:break
        time.sleep(2)
    else:raise TimeoutError('Owned GPUs not released')
    print(json.dumps(d),flush=True)
    ledger=remote('4090','OLD='+repr(OLD)+'\n'+ledger_code)
    (P/'reuse-ledger.json').write_text(json.dumps(ledger,indent=2))
    r=subprocess.run(['D:/Git/usr/bin/scp.exe','-q','-o','BatchMode=yes',str(P/'reuse-ledger.json'),'3090:'+ROOT+'/reuse-ledger.json'],capture_output=True,text=True,timeout=35)
    assert r.returncode==0,r.stderr
    print(json.dumps(dict(reused_unique_tasks=[r['task_id'] for r in ledger['completed_natural_trajectories']])),flush=True)
    for host,kind,py in [('3090','model',MODEL_PY),('4090','gui',GUI_PY)]:
        rec=remote(host,'KIND='+repr(kind)+'\nPY='+repr(py)+'\n'+launch)
        (P/(kind+'-launch-receipt.json')).write_text(json.dumps(rec,indent=2))
        print(json.dumps(rec),flush=True)
