"""Source-bound preconditions for exactly one failed-input capacity attempt; CPU only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

OLD = '/home/researcher/jev-defense-four-gpu-20261106/online-service-group-1793978182501156243'
FAILED = 'bd7ed2f4753b00594cb626a4cad3b740c0f95d91128547da69404254a2559841'
PROPOSAL = 'a0e6638ea5a9c78d703d18770fe7066ecc1b983c739324465bb3812acccfb935'
CPU = 'acb9b2fb465bb2763a696c83599d5b50f1aa61f5de78393b244084d5db02a6e9'
WIRE = 'b66a7a24a4037ced2b4ec5aa602853c6cde4d44c0b06aac3c619152a8bbf198e'


def read(path): return json.loads(Path(path).read_bytes())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()


def verify_manifest(root, path, expected):
    root=Path(root).resolve();path=Path(path)
    assert sha(path)==expected,'Terminal manifest identity changed'
    mapping=read(path)
    for name,digest in mapping.items():
        relative=Path(name);target=(root/relative).resolve()
        assert not relative.is_absolute()and'..'not in relative.parts and target.is_relative_to(root)
        assert not(root/relative).is_symlink()and sha(target)==digest,'Terminal file changed: '+name
    actual={p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()and p.resolve()!=path.resolve()}
    assert actual==set(mapping),'Terminal manifest is not exhaustive'
    return mapping


def identity(pid):
    root=Path('/proc')/str(pid)
    if not root.exists():return None
    stat=(root/'stat').read_text().rsplit(')',1)[1].split()
    return{'pid':int(pid),'uid':root.stat().st_uid,'start_ticks':stat[19],
        'command':(root/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()}


def same(actual,expected):
    return actual is not None and all(str(actual[key])==str(expected[key])for key in('pid','uid','command','start_ticks'))


def validate_static(spec, here):
    assert spec['stage']=='single_failed_judge_capacity_replay_14_22_22_6'
    assert spec['primary_calls']==1 and spec['helper_calls']==0 and spec['actor_GUI_scorer_calls']==0
    assert spec['max_output_tokens']==4096 and spec['automatic_retry']is False
    assert spec['primary_allocator']=='expandable_segments:True'
    assert spec['layer_counts']==[14,22,22,6]
    assert spec['proposal_receipt_sha256']==PROPOSAL and sha(spec['proposal_receipt'])==PROPOSAL
    assert spec['CPU_proof_sha256']==CPU and sha(spec['CPU_proof'])==CPU
    assert sha(spec['frozen_wire'])==WIRE
    payload=read(spec['frozen_wire']);assert set(payload)=={'operation','system','view','candidate'}and payload['operation']=='judge'
    for name,expected in spec['source_sha256'].items():assert sha(Path(here)/name)==expected
    primary=read(spec['roles']['primary']['admission']);helper=read(spec['roles']['pplx_flash']['admission'])
    assert primary['mode']=='capacity_preflight'and primary['max_new_calls']==1 and len(primary['requests'])==1
    assert primary['requests'][0]['wire_sha256']==WIRE
    assert helper['mode']=='resident_only'and helper['max_new_calls']==0 and helper['requests']==[]
    assert not spec['GUI_release_after_capacity']and not spec['resume_old_GUI_budget']
    return True


def validate_old_terminal(spec, inspect_identity=identity):
    old=Path(spec['old_group']);assert str(old)==OLD
    if spec.get('old_terminal_mode')=='postexit_copy_original_metadata_missing':
        # One source-bound exception authorized by root: old stop control failed
        # before its own exit/terminal writer. Keep original missing, do not
        # manufacture exit0 or bypass the preserved real prefill model failure.
        audit=spec['old_postexit_audit'];assert sha(audit['path'])==audit['sha256']
        assert audit['sha256']=='6cc5f640a3abd9bdeb53a990db14a5386107517846c82933b188e99e83013d36'
        value=read(audit['path'])
        assert value['original_group']==OLD
        assert value['original_exit_json_missing']is True and value['original_terminal_sha256_missing']is True
        assert value['actual_old_workers_and_launcher_pid_absent']is True
        assert value['worker_exit_codes_observed']is False
        assert value['worker_exit_codes']=={'primary':None,'pplx_flash':None}
        assert value['actual_holder_launcher_return']['pid']==2610486
        assert value['actual_holder_launcher_return']['exit_code']==1
        assert sha(value['actual_holder_return_source'])==value['actual_holder_return_source_sha256']
        assert value['original_group_not_modified']is True
        assert value['all_original_service_bytes_stable_before_copy_after']is True
        assert value['sealed_service_files']==529
        assert value['request_counts']=={'primary':{'completed':72,'failed':1,'pending_unsealed':0},
            'pplx_flash':{'completed':0,'failed':0,'pending_unsealed':0}}
        assert value['service_original_manifest_sha256']=='eedd00633edb80b9f57ed81d1e899e564e38b0c5c2efbd6c44531c99a372e624'
        assert spec['old_terminal_manifest']==value['service_original_manifest_path']
        assert spec['old_terminal_manifest_sha256']==value['service_original_manifest_sha256']
        verify_manifest(old,spec['old_terminal_manifest'],spec['old_terminal_manifest_sha256'])
        expected=[read(old/'processes'/(role+'.json'))['identity']for role in('primary','pplx_flash')]
        expected.append(read(old/'process.json'))
        assert not(old/'exit.json').exists()and not(old/'terminal-sha256.json').exists()
        for row in expected:assert not same(inspect_identity(row['pid']),row),'Old exact process still live'
    else:
        verify_manifest(old,spec['old_terminal_manifest'],spec['old_terminal_manifest_sha256'])
        assert(old/'exit.json').exists(),'Old launcher not terminal'
        exited=read(old/'exit.json')
        assert{row['role']for row in exited['workers']}=={'primary','pplx_flash'}
        assert all(row['exit_code']==0 for row in exited['workers'])
        for row in exited['workers']:
            assert not same(inspect_identity(row['identity']['pid']),row['identity']),'Old exact worker is still live'
    state=read(old/'online-state.json');assert state['phase']=='terminal_failure'and state['active']is None
    completed=failed=0
    for role in('primary','pplx_flash'):
        requests=list((old/role/'requests').iterdir())
        assert len(requests)==(73 if role=='primary'else 0)
        for request in requests:
            assert(request/'seal.json').exists(),'Old pending request prevents resource reuse'
            for name,expected in read(request/'seal.json').items():assert sha(request/name)==expected
            failed+=(request/'failure.json').exists();completed+=(request/'response.json').exists()
    assert completed==72 and failed==1
    assert sha(old/'primary/requests'/FAILED/'seal.json')=='2524d02f7c18dd662794122701648e92c7b5729b9ae7c386b13c23ffbe4dcec7'
    assert sha(old/'primary/requests'/FAILED/'failure.json')=='33711cdae751e010211c07d62a2228eb7bbb305c07f832108482a8b4f7f64a6d'
    return{'old_exact_workers_absent':True,'completed':completed,'failed':failed,'pending':0}


def empty_resources(lease, inspect_identity=identity, raw_compute=None, raw_gpu=None):
    assert same(inspect_identity(lease['holder']['pid']),lease['holder'])
    assert len(lease['lock_records'])==9
    for row in lease['lock_records']:
        path=Path('/proc',str(lease['holder']['pid']),'fd',str(row['fd']))
        info=Path('/proc',str(lease['holder']['pid']),'fdinfo',str(row['fd'])).read_text()
        assert os.readlink(path)==row['path']and path.stat().st_ino==row['inode']and'lock:'in info
    if raw_compute is None:
        raw_compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid',
            '--format=csv,noheader,nounits'],text=True)
    target={row['uuid']for row in lease['gpu']}
    assert{row['index']for row in lease['gpu']}=={4,5,6,7}
    assert not any(line.split(',')[0].strip()in target for line in raw_compute.splitlines()if line.strip())
    if raw_gpu is None:
        raw_gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free',
            '--format=csv,noheader,nounits'],text=True)
    actual={}
    for line in raw_gpu.splitlines():
        if line.strip():
            index,uuid,free=[part.strip()for part in line.split(',')]
            actual[int(index)]={'uuid':uuid,'free_mib':int(free)}
    for row in lease['gpu']:
        observed=actual[row['index']]
        assert observed['uuid']==row['uuid']and observed['free_mib']>=23000,'GPU UUID/free memory gate failed'
    return{'actual_holder_identity_all9locks_verified':True,'target_compute_count':0,
        'actual_GPU4_7':{str(row['index']):actual[row['index']]for row in lease['gpu']},
        'minimum_free_mib':23000}
