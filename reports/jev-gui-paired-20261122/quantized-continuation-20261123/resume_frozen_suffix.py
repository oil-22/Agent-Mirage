"""Once-only, source-bound NF4 continuation for the 71 genuinely unstarted arms."""

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import secrets
import shutil
import time

import run_nf4 as nf4
from prepare import edit, read, save, sha

HERE=Path(__file__).resolve().parent
CURRENT=HERE/'native-key-resume-current.json'
CUT=29
FAILED='paperpair-T171-blank_replace-off'
FIRST='paperpair-T171-blank_replace-on'
RECEIPTS={'3090':'1795494566746111300','4090':'1795494566746295200'}
control=nf4.control


def verified_receipt(root, host):
    d=root/'operations'/f'{RECEIPTS[host]}-verify-NF4-technical-terminal-postexit-{host}'
    seal=read(d/'seal.json')
    assert all(sha(d/name)==h for name,h in seal.items())
    t=read(d/'transport.json');assert t['host']==host and t['returncode']==0
    return read(d/'stdout.bin'),sha(d/'seal.json')


def freeze():
    assert not CURRENT.exists(), 'Already prepared; inspect the existing linked attempt.'
    nf4.setup()
    before=control.PACKAGE; parent=control.MANIFEST; prior=control.POINTER
    m, mh=verified_receipt(control.ROOT,'3090'); g, gh=verified_receipt(control.ROOT,'4090')
    assert m['uid']==1033 and g['uid']==1015
    assert m['parent_manifest_sha256']==g['parent_manifest_sha256']==prior['manifest_sha256']
    assert m['terminal_sha256']==g['terminal_sha256']==m['service_end'][-1]['terminal_sha256']
    assert m['service_end'][-1]['run_id']==FAILED and m['service_end'][-1]['infrastructure_failure']
    assert m['untouched_frozen_suffix_slots']==g['untouched_frozen_suffix_slots']==71 and g['next_slot']==FIRST
    old=read(before/'plan.json'); full=read(before/'parent-full-plan.json')['queue']
    assert old['queue']==full[26:] and len(full)==100
    assert full[CUT-1]['run_id']==FAILED and full[CUT]['run_id']==FIRST
    assert full[CUT-1]['pair_id']==full[CUT]['pair_id']
    assert [r['run_id'] for r in full[26:CUT]]==[e['run_id'] for e in m['service_end']]
    case=f'paper-paired-nf4-untouched-after-native-key-{time.time_ns()}'
    root=HERE/case; p=root/'runtime';p.mkdir(parents=True,exist_ok=False)
    for name in parent['files']:
        dst=p/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(before/name,dst)
    shutil.copyfile(HERE/'verify_native_key_parent.py',p/'verify_native_key_parent.py')
    (p/'private.token').write_text(secrets.token_hex(32)+'\n',encoding='ascii')
    (p/'plan.json').write_text(json.dumps({**old,'queue':full[CUT:]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save(p/'nf4-resume-link.json',{
        'parent_manifest_sha256':prior['manifest_sha256'],'parent_plan_sha256':prior['plan_sha256'],
        'parent_packages':{host:parent['package'+host] for host in ('3090','4090')},
        'terminal_sha256_by_run':{v['run_id']:v['terminal_sha256'] for v in m['service_end']},
        'model_postexit_sha256':m['postexit_sha256'],'GUI_postexit_sha256':g['postexit_sha256'],
        'GUI_batch_seal_sha256':g['batch_seal_sha256'],'model_journal_head':m['model_journal_head'],
        'failed_GUI_controller_head':g['controller_head'],'original_slot_cutoff':CUT,
        'preservation_reader_seals':{'3090':mh,'4090':gh},'failed_arm_reexecutes':0})
    edit(p/'paired_contract.py',[
        ('assert split == 26','assert split == 29'),
        ('and split % 2 == 0','and parent[\'queue\'][split-1][\'pair_id\'] == parent[\'queue\'][split][\'pair_id\']'),
    ])
    edit(p/'continuation_guard.py',[
        ("assert m['preserved_prefix_count'] == 26","assert m['preserved_prefix_count'] == 29"),
        ("    return {'host': host, 'preserved_prefix': 26,", "    from verify_native_key_parent import verify_prior_nf4\n"
         "    parent = verify_prior_nf4(package, host, full, gone, events)\n"
         "    return {'host': host, 'preserved_prefix': 29, 'prior_NF4': parent,"),
        ("'continuation_trajectories': 74","'continuation_trajectories': 71"),
    ])
    edit(p/'launch_group.py',[(repr(Path(parent['package3090']).name+'.lock'), "(P.name + '.lock')")])
    edit(p/'primary_server.py',[
        ('        from nf4_runtime import qualify\n','        from verify_native_key_parent import admit_prior_capacity\n'),
        ("        capacity=qualify(native,P,root,save,sha,resource,journal)",
         "        capacity=admit_prior_capacity(native,P,root,save,sha,resource,journal)"),
    ])
    files={q.relative_to(p).as_posix():sha(q) for q in sorted(p.rglob('*')) if q.is_file() and q.name!='private.token'}
    changed={name for name in parent['files'] if parent['files'][name]!=files[name]}
    assert changed=={'plan.json','paired_contract.py','continuation_guard.py','launch_group.py','primary_server.py'}
    for name in files:
        if name.endswith('.py'):ast.parse((p/name).read_bytes(),filename=name)
    def source_node(path,name):
        return ast.dump(next(n for n in ast.parse(path.read_bytes()).body if getattr(n,'name',None)==name))
    assert source_node(before/'primary_server.py','NativeActor')==source_node(p/'primary_server.py','NativeActor')
    assert source_node(before/'primary_server.py','resource')==source_node(p/'primary_server.py','resource')
    manifest={**parent,'files':files,'plan_sha256':files['plan.json'],'trajectories':len(full[CUT:]),
        'preserved_prefix_count':CUT,'auth_token_sha256':sha(p/'private.token'),
        'package3090':f'/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/{case}',
        'package4090':f'/data/researcher/jev-defense-four-gpu-20261106/{case}/runtime',
        'output3090':f'/data/researcher/jev-defense-four-gpu-20261106/{case}/model-attempt-01'}
    save(p/'manifest.json',manifest)
    ptr={'root':str(root),'runtime':str(p),'manifest_sha256':sha(p/'manifest.json'),
         'plan_sha256':manifest['plan_sha256'],'stage_id':'NF4-resume-01','measurement_version':'NF4',
         'preserved_prefix':CUT,'unstarted_suffix':manifest['trajectories'],'first_run':FIRST}
    save(root/'continuation-boundary.json',{
        'unchanged_experiment_files':sorted(set(parent['files'])-changed),
        'only_changed_orchestration_and_prior_capacity_evidence':sorted(changed),
        'native_actor_class_AST_identical':True,'checkpoint_NF4_Flash_and_GUI_unchanged':True,
        'original_parent_pointer_sha256':sha(nf4.CURRENT),'no_extra_stress_generation':True,
        'does_not_normalize_invalid_original_keyboard_input':True,'new_model_GUI_scorer_calls':0})
    save(CURRENT,ptr)
    return ptr


def setup():
    control.POINTER=read(CURRENT);control.ROOT=Path(control.POINTER['root']);control.PACKAGE=Path(control.POINTER['runtime'])
    assert sha(control.PACKAGE/'manifest.json')==control.POINTER['manifest_sha256']
    control.MANIFEST=read(control.PACKAGE/'manifest.json')
    assert all(sha(control.PACKAGE/name)==d for name,d in control.MANIFEST['files'].items())


def stage():
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs={h:pool.submit(control.stage,h) for h in ('3090','4090') if not (control.ROOT/f'stage-{h}.json').exists()}
        for f in jobs.values():f.result()
    reports={h:read(control.ROOT/f'stage-{h}.json')['result'] for h in ('3090','4090')}
    assert all(v['expected']==71 and v['manifest_sha256']==control.POINTER['manifest_sha256'] for v in reports.values())
    assert reports['3090']['availability_proof']['prior_NF4']==reports['4090']['availability_proof']['prior_NF4']
    proof={'processed_old_NF4':reports['3090']['availability_proof']['prior_NF4'],
           'new_unstarted_slots':71,'new_model_GUI_scorer_calls':0,'staging_matches_both_hosts':True}
    target=control.ROOT/'admission-cross-host.json'
    if not target.exists():save(target,proof)
    assert read(target)==proof
    return proof


MODEL_START=r'''
import fcntl,json,os,socket,subprocess,sys,time
from pathlib import Path
p=Path(ROOT);o=Path(OUTPUT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import gpu_snapshot,identity,sha
from continuation_guard import verify_native_parent
assert sha(p/'manifest.json')==EXPECTED and not o.exists() and not (p/'background').exists()
assert verify_native_parent(p)['continuation_trajectories']==71
s=gpu_snapshot();u={s['gpu'][i]['uuid'] for i in range(4)}
assert all(s['gpu'][i]['free_mib']>=23000 for i in range(4)) and not any(v['uuid'] in u for v in s['compute'])
for addr,port in [('192.0.2.11',19202),('127.0.0.1',18342)]:
    with socket.socket() as test:test.bind((addr,port))
with Path('/home/researcher/jev-defense-four-gpu-20261106/inference.lock').open('a') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
o.parent.mkdir(exist_ok=True,parents=True)
disk=os.statvfs(o.parent);assert disk.f_bavail*disk.f_frsize>64*1024**3
(p/'background').mkdir(exist_ok=False)
argv=['/opt/whz/conda-envs/webmall-vlm/bin/python','-B','-u',str(p/'launch_group.py')]
with (p/'background/launcher.log').open('xb') as f:
    child=subprocess.Popen(argv,cwd=p,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,
                           stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
event={'pid':child.pid,'actual':identity(child.pid),'argv':argv,'manifest_sha256':EXPECTED,
       'startup_is_not_inference':True,'time':time.time(),'exclusive_selected_physical_cards':[0,1,2,3]}
with (p/'background/launch.json').open('x') as f:json.dump(event,f);f.flush();os.fsync(f.fileno())
print(json.dumps(event))
'''


GUI_START=r'''
import fcntl,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import identity,sha
from continuation_guard import verify_gui_parent,SITE
from paired_contract import load_plan
assert sha(p/'manifest.json')==EXPECTED and verify_gui_parent(p)['continuation_trajectories']==71
m,plan=load_plan(p)
assert plan['queue'][0]['run_id']=='paperpair-T171-blank_replace-on'
assert not any((p/x).exists() for x in ('control','batch','background','STOP'))
with SITE.open('a') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert urllib.request.urlopen('http://192.0.2.10:29980/',timeout=12).status==200
req=urllib.request.Request(m['main_url']+'/health',headers={'Authorization':'Bearer '+(p/'private.token').read_text().strip()})
with urllib.request.urlopen(req,timeout=20) as r:h=json.load(r)
assert h['phase']=='ready' and h['actor_attempts']==h['actor_replies']==h['done']==0 and h['active'] is None
assert h['expected']==len(plan['queue'])==71 and h['manifest_sha256']==EXPECTED
(p/'background').mkdir(exist_ok=False)
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(p/'gui_outer.py')]
with (p/'background/outer.log').open('xb') as f:
    child=subprocess.Popen(argv,cwd=p,env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},
                           stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
event={'actual':identity(child.pid),'argv':argv,'time':time.time(),'pre_GUI_health':h,'first_slot':plan['queue'][0]}
with (p/'background/launch.json').open('x') as f:json.dump(event,f);f.flush();os.fsync(f.fileno())
print(json.dumps(event))
'''


def start(role):
    assert read(control.ROOT/'admission-cross-host.json')['staging_matches_both_hosts']
    target=control.ROOT/f'{role}-submission.json'
    assert not target.exists(), 'Already submitted, inspect the live source.'
    if role=='model':
        result=control.remote('3090',control.prefix('3090')+MODEL_START,'start-NF4-without-repeating-native-key-terminal')
    else:
        assert (control.ROOT/'model-submission.json').exists()
        proof=nf4.model_proof()
        assert proof['result']['capacity']['new_engineering_generation_calls']==0
        result=control.remote('4090',control.prefix('4090')+GUI_START,'start-only-NF4-frozen-unstarted-suffix')
        result['verified_model_lease']=proof
    save(target,result)
    return result['result']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('freeze','stage','start-model','start-browser','inspect','verify-model'))
    p.add_argument('host',nargs='?',choices=('3090','4090'))
    a=p.parse_args()
    if a.action=='freeze':result=freeze()
    else:
        setup()
        if a.action=='stage':result=stage()
        elif a.action=='inspect':result=control.inspect(a.host)
        elif a.action=='verify-model':result=nf4.model_proof()
        else:result=start(a.action.removeprefix('start-'))
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
