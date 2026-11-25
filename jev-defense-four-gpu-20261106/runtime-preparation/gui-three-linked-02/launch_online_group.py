"""New three-trajectory services; root's holder alone may launch this stage."""
import argparse
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
import traceback

from online_contract import initial_state, validate_plan
from online_service import save, sha
from online_gate import BASE, read, validate_static, verify_gate


def main(a):
    if os.getuid() != 1033 or not a.root.resolve().is_relative_to(BASE):
        raise RuntimeError('Task UID/root differs')
    if sha(a.spec) != a.spec_sha256:
        raise RuntimeError('Concrete new online spec differs')
    spec = read(a.spec); here = Path(__file__).resolve().parent
    validate_static(spec, here)
    if spec.get('root_reviewed_approval') is not True or str(a.root) != spec['new_group'] or a.root.exists():
        raise RuntimeError('Root-reviewed fresh independent group is required')
    parent = Path(spec['preflight_source_root']);sys.path.insert(0,str(parent))
    from preflight_service import check_inherited_locks, identity
    from four_gpu_contract import FLASH, validate_layout
    from capacity_gate import verify_manifest, validate_old_terminal, empty_resources, identity as proc_identity, same
    from marker_stop_helpers import stop_owned, progress_owned_stop
    lease_path=Path(os.environ['MIRAGE_TASK_LEASE']);lease=read(lease_path)
    check_inherited_locks(lease)
    gate_path,gate,old = verify_gate(spec,verify_manifest,validate_old_terminal,proc_identity,same)
    # This checks actual holder identity/all9held locks and fresh GPU4-7
    # UUID/compute/free>=23000MiB before any model process is created.
    resources = empty_resources(lease)
    validate_layout(read(spec['layout']))
    plan=read(spec['online_plan']);runs=validate_plan(plan)
    token_path=Path(spec['token_file'])
    if (token_path.is_symlink() or token_path.stat().st_uid != 1033 or
            stat.S_IMODE(token_path.stat().st_mode) != 0o600 or
            token_path.resolve().parent != Path(spec['preparation_root']).resolve()):
        raise RuntimeError('Independent UID1033/mode600 new token is required')
    token=token_path.read_bytes().strip()
    if len(token)<32 or any(token==Path(old_token).read_bytes().strip() for old_token in spec['forbidden_previous_tokens']):
        raise RuntimeError('New online token must differ from both oldonline and capacity')
    save(Path(spec['once_only_claim']),{'root':str(a.root),'spec_sha256':sha(a.spec),
        'gate_sha256':sha(gate_path),'resources':resources,'old_terminal_preserved':old,
        'time':time.time(),'automatic_retry':False})
    a.root.mkdir(exist_ok=False);(a.root/'processes').mkdir();(a.root/'transitions').mkdir()
    save(a.root/'online-state.json',initial_state(plan))
    caps={key:{'actor':70,'judge':140,'observer':row['caps']['observe'],'steps':50}for key,row in runs.items()}
    save(a.root/'online-admission.json',{'stage':'new_exact_three_online_GUI',
        'plan_sha256':spec['online_plan_sha256'],'run_order':list(runs),'per_run_caps':caps,
        'online_launch_gate_sha256':sha(gate_path),'capacity_terminal_manifest_sha256':
        gate['capacity_terminal_manifest_sha256'],'automatic_retries':False,
        'common_decoder_layer_counts':[14,22,22,6],'primary_allocator':spec['primary_allocator']})
    worker=here/'online_service.py';commands={}
    for role in ('primary',FLASH):
        python=spec['roles'][role]['python']
        if role=='primary' and python!='/opt/whz/conda-envs/webmall-vlm/bin/python':
            raise RuntimeError('Original primary environment required')
        if role==FLASH and not Path(python).is_relative_to(BASE/'flash-preparation'):
            raise RuntimeError('Isolated native Flash environment required')
        commands[role]=[python,'-u',str(worker),'--role',role,'--root',str(a.root/role),
            '--lease',str(lease_path),'--config',str(a.root/'runtime-config.json'),
            '--port',str(spec['roles'][role]['port'])]
    save(a.root/'runtime-config.json',{**spec,'commands':commands,'group_root':str(a.root)})
    save(a.root/'launch-specification.json',spec);save(a.root/'process.json',identity(os.getpid()))
    descriptors=tuple(int(s)for s in os.environ['MIRAGE_GPU_LOCK_FDS'].split(','))
    stopping={'value':False}
    signal.signal(signal.SIGTERM,lambda *_:stopping.update(value=True))
    signal.signal(signal.SIGUSR1,lambda *_:stopping.update(value=True))
    children=[];sent=False
    try:
        for role in ('primary',FLASH):
            env={**os.environ,'CUDA_VISIBLE_DEVICES':'4,5,6,7'if role=='primary'else'7',
                'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false',
                'PYTHONDONTWRITEBYTECODE':'1'}
            env.pop('PYTORCH_CUDA_ALLOC_CONF',None)
            if role=='primary':env['PYTORCH_CUDA_ALLOC_CONF']=spec['primary_allocator']
            log=a.root/(role+'.log')
            with log.open('xb')as handle:
                process=subprocess.Popen(commands[role],stdout=handle,stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,env=env,cwd=str(BASE),pass_fds=descriptors,start_new_session=True)
            actual=identity(process.pid);children.append({'role':role,'process':process,'identity':actual,'log':log})
            save(a.root/(role+'-launch.json'),{'identity':actual,'argv':commands[role],
                'visible_gpus':env['CUDA_VISIBLE_DEVICES'],'inherited_lock_count':len(descriptors),
                'PYTORCH_CUDA_ALLOC_CONF':env.get('PYTORCH_CUDA_ALLOC_CONF')})
        print(json.dumps({'group':str(a.root),'stage':'loading_new_exact_three_online_group',
            'workers':[{'role':c['role'],'pid':c['process'].pid}for c in children]}),flush=True)
        while any(c['process'].poll()is None for c in children):
            if(any(c['process'].poll()is not None for c in children)or stopping['value'])and not sent:
                stop_owned(children);sent=True
            if sent:progress_owned_stop(children)
            time.sleep(1)
        if any(c['process'].returncode!=0 for c in children):
            raise RuntimeError('Online worker failed; preserve all original terminal data before diagnosis')
    except BaseException:
        save(a.root/'launcher-failure.json',{'error':traceback.format_exc(),'time':time.time()})
        stop_owned(children)
        while any(c['process'].poll()is None for c in children):progress_owned_stop(children);time.sleep(1)
        raise
    finally:
        if children and not any(c['process'].poll()is None for c in children):
            save(a.root/'exit.json',{'time':time.time(),'workers':[{'role':c['role'],
                'identity':c['identity'],'exit_code':c['process'].poll(),
                'zombie_observed':c.get('zombie_observed')}for c in children]})
            save(a.root/'terminal-sha256.json',{str(p.relative_to(a.root)):sha(p)
                for p in a.root.rglob('*')if p.is_file()and p.name!='terminal-sha256.json'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--spec',type=Path,required=True);parser.add_argument('--spec-sha256',required=True)
    main(parser.parse_args())
