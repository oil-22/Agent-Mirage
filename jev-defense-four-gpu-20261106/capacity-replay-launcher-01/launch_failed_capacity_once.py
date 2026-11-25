"""Root-reviewed new holder launch only. Finite model admission, marker-only normal stop."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import traceback
from capacity_gate import validate_static,validate_old_terminal,empty_resources,sha,read
from four_gpu_contract import FLASH,validate_layout
from preflight_service import check_inherited_locks,identity,save
from marker_stop_helpers import commands_for,stop_owned,progress_owned_stop

BASE=Path('/home/researcher/jev-defense-four-gpu-20261106')


def attempt_terminal(root):
    requests=list((root/'primary/requests').glob('*'))
    assert len(requests)<=1,'Finite stage produced more than one primary request'
    if not requests or not(requests[0]/'seal.json').exists():return None
    request=requests[0]
    for name,expected in read(request/'seal.json').items():assert sha(request/name)==expected
    assert not list((root/FLASH/'requests').glob('*'))
    return{'request':str(request),'request_seal_sha256':sha(request/'seal.json'),
        'status':'technical_failure'if(request/'failure.json').exists()else'completed',
        'primary_model_calls':1,'helper_model_calls':0,'actor_GUI_scorer_calls':0,
        'capacity_semantic_or_GUI_success_not_inferred':True}


def main(a):
    assert os.getuid()==1033 and a.root.resolve().is_relative_to(BASE)
    assert sha(a.spec)==a.spec_sha256
    spec=read(a.spec);here=Path(__file__).resolve().parent
    validate_static(spec,here)
    assert spec['root_reviewed_approval']is True,'Root has not reviewed/finalized this specification'
    assert str(a.root)==spec['new_group']and not a.root.exists()
    lease_path=Path(os.environ['MIRAGE_TASK_LEASE']);lease=read(lease_path)
    check_inherited_locks(lease)
    old=validate_old_terminal(spec);resources=empty_resources(lease)
    validate_layout(read(spec['layout']))
    for role in('primary',FLASH):assert sha(spec['roles'][role]['admission'])==spec['admission_sha256'][role]
    claim=Path(spec['once_only_claim'])
    save(claim,{'spec_sha256':a.spec_sha256,'new_group':str(a.root),'time':time.time(),
        'old_terminal_gate':old,'resources':resources,'automatic_retry':False})
    a.root.mkdir(parents=True,exist_ok=False);(a.root/'processes').mkdir()
    worker=here/'preflight_service.py'
    commands=commands_for(spec,a.root,worker,lease_path)
    save(a.root/'runtime-config.json',{**spec,'commands':commands,'group_root':str(a.root)})
    save(a.root/'launch-specification.json',spec);save(a.root/'process.json',identity(os.getpid()))
    descriptors=tuple(int(x)for x in os.environ['MIRAGE_GPU_LOCK_FDS'].split(','))
    stopping={'value':False}
    signal.signal(signal.SIGTERM,lambda *_:stopping.update(value=True))
    signal.signal(signal.SIGUSR1,lambda *_:stopping.update(value=True))
    children=[];sent=False
    try:
        for role in('primary',FLASH):
            env={**os.environ,'CUDA_VISIBLE_DEVICES':'4,5,6,7'if role=='primary'else'7',
                'PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
                'TOKENIZERS_PARALLELISM':'false'}
            env.pop('PYTORCH_CUDA_ALLOC_CONF',None)
            if role=='primary':env['PYTORCH_CUDA_ALLOC_CONF']=spec['primary_allocator']
            log=a.root/(role+'.log')
            with log.open('xb')as handle:
                process=subprocess.Popen(commands[role],stdin=subprocess.DEVNULL,stdout=handle,
                    stderr=subprocess.STDOUT,env=env,cwd=str(BASE),pass_fds=descriptors,start_new_session=True)
            actual=identity(process.pid)
            children.append({'role':role,'process':process,'identity':actual,'log':log})
            save(a.root/(role+'-launch.json'),{'identity':actual,'argv':commands[role],
                'visible_gpus':env['CUDA_VISIBLE_DEVICES'],'inherited_lock_count':len(descriptors),
                'PYTORCH_CUDA_ALLOC_CONF':env.get('PYTORCH_CUDA_ALLOC_CONF')})
        print(json.dumps({'new_group':str(a.root),'stage':'loading_capacity_only',
            'primary_budget':1,'helper_budget':0,'GUI_budget':0}),flush=True)
        while any(row['process'].poll()is None for row in children):
            terminal=attempt_terminal(a.root)if all((a.root/role/'requests').exists()for role in('primary',FLASH))else None
            if terminal and not(a.root/'capacity-attempt-terminal.json').exists():save(a.root/'capacity-attempt-terminal.json',terminal)
            if(terminal is not None or stopping['value']or any(row['process'].poll()is not None for row in children))and not sent:
                stop_owned(children);sent=True
            if sent:progress_owned_stop(children)
            time.sleep(1)
        if any(row['process'].returncode!=0 for row in children):raise RuntimeError('Capacity service infrastructure exit failed; preserve, no retry')
    except BaseException:
        save(a.root/'launcher-failure.json',{'error':traceback.format_exc(),'time':time.time()})
        stop_owned(children)
        while any(row['process'].poll()is None for row in children):progress_owned_stop(children);time.sleep(1)
        raise
    finally:
        if children and not any(row['process'].poll()is None for row in children):
            save(a.root/'exit.json',{'time':time.time(),'workers':[{'role':row['role'],
                'identity':row['identity'],'exit_code':row['process'].poll(),
                'zombie_observed':row.get('zombie_observed')}for row in children]})
            save(a.root/'terminal-manifest.json',{str(p.relative_to(a.root)):sha(p)for p in a.root.rglob('*')
                if p.is_file()and p.name!='terminal-manifest.json'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--spec',type=Path,required=True);parser.add_argument('--spec-sha256',required=True)
    main(parser.parse_args())
