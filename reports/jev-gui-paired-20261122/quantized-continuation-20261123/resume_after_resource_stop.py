"""Once-only startup for the original 39 untouched NF4 slots, with no changed experiment conditions."""

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import secrets
import shutil
import time

import resume_frozen_suffix as old
from prepare import edit, read, save, sha

HERE = Path(__file__).resolve().parent
CURRENT = HERE/'resource-stop-resume-current.json'
control = old.control
STAGE, PARENT = 'NF4-resume-02', 'NF4-resume-01'
CUT, COUNT = 61, 39
FAILED, FIRST = 'paperpair-T058-silent_drop-on', 'paperpair-T058-silent_drop-off'


def verify(folder):
    for name, value in read(folder/'seal.json').items():
        assert Path(name).name == name and sha(folder/name) == value


def bound_receipt(path, host):
    verify(path)
    assert read(path/'transport.json')['host'] == host
    return read(path/'stdout.bin')


def freeze(ledger, release, failure, resources):
    assert not CURRENT.exists()
    for p in (ledger, release, failure, resources):
        verify(p)
    led, rel, err, gpu = (read(p/n) for p,n in (
        (ledger,'private-linked.json'),(release,'index.json'),(failure,'index.json'),(resources,'index.json')))
    assert rel['ledger_seal_sha256'] == err['ledger_seal_sha256'] == sha(ledger/'seal.json')
    assert rel['phase'] == 'technical_failure' and rel['stage'] == PARENT and rel['cutoff_in_original_100'] == CUT
    assert err['release_audit_sha256'] == sha(release/'seal.json') and err['run'] == FAILED and err['no_original_retry']
    for host in ('3090','4090'):
        for record, key in ((rel['hosts'][host],'operation_seal'),(err['hosts'][host],'operation_seal_sha256')):
            p = Path(record['operation'])
            assert sha(p/'seal.json') == record[key] and bound_receipt(p, host) == record['result']
    p = Path(gpu['operation'])
    assert sha(p/'seal.json') == gpu['operation_seal_sha256'] and bound_receipt(p, '3090') == gpu['result']
    uuids = [gpu['result']['gpu'][str(i)]['uuid'] for i in range(4)]
    assert uuids[3] == err['hosts']['3090']['result']['GPU_UUID']

    old.setup()
    parent, old_path = control.MANIFEST, control.PACKAGE
    parent_ptr = control.POINTER
    plan = read(old_path/'plan.json')
    full = read(old_path/'parent-full-plan.json')['queue']
    assert plan['queue'] == full[29:] and len(full) == 100
    assert full == [r['slot'] for r in led['rows']] and all(r['evidence'] for r in led['rows'][:CUT])
    untouched = [r['run_id'] for r in full[CUT:]]
    assert len(untouched) == COUNT and untouched[0] == FIRST and full[CUT-1]['run_id'] == FAILED
    assert untouched == rel['verified_never_started_in_stage'] == err['unstarted_frozen_ids']
    assert all(r['status'] == 'not_started_at_collection' and r['evidence'] is None for r in led['rows'][CUT:])
    suffix_done = led['rows'][29:CUT]
    hashes = {r['slot']['run_id']:r['evidence']['terminal_sha256'] for r in suffix_done}
    end_hashes = {r['slot']['run_id']:r['evidence']['terminal_sha256'] for r in suffix_done if r['evidence']['model_run_end_bound']}
    assert len(hashes) == 32 and len(end_hashes) == 31 and FAILED not in end_hashes
    assert hashes[FAILED] == err['terminal_sha256'] == suffix_done[-1]['evidence']['terminal_sha256']
    collection = led['collections'][PARENT]
    src = Path(collection['path'])
    verify(src)
    assert sha(src/'seal.json') == collection['seal_sha256']
    assert read(src/'index.json')[PARENT]['GUI_terminals'] == 32

    case = 'paper-paired-nf4-untouched-after-resource-stop-' + str(time.time_ns())
    root = HERE/case
    dst = root/'runtime'
    dst.mkdir(parents=True,exist_ok=False)
    for name, digest in parent['files'].items():
        f = dst/name
        f.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(old_path/name, f)
        assert sha(f) == digest
    shutil.copyfile(HERE/'verify_resource_parent.py', dst/'verify_resource_parent.py')
    (dst/'private.token').write_text(secrets.token_hex(32)+'\n',encoding='ascii')
    (dst/'plan.json').write_text(json.dumps({**plan,'queue':full[CUT:]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    failed = err['hosts']['3090']['result']
    failed_step = suffix_done[-1]['evidence']['steps'][-1]
    rp, gp = (rel['hosts'][h]['result'] for h in ('3090','4090'))
    # The archived paths are POSIX even though this preparer runs on Windows.
    conflict = failed['resource_conflict_file'].removeprefix(parent['output3090']+'/')
    assert conflict.startswith('primary/resource-conflicts/') and failed['request_seal_sha256']==failed_step['main']['seal_sha256']
    save(dst/'resource-stop-resume-link.json',{
        'parent_package':{h:parent['package'+h] for h in ('3090','4090')},
        'parent_manifest_sha256':parent_ptr['manifest_sha256'],'parent_plan_sha256':parent_ptr['plan_sha256'],
        'cutoff_in_original_100':CUT,'never_started_run_ids':untouched,
        'terminal_sha256_by_run':hashes,'model_end_sha256_by_run':end_hashes,'failed_run_id':FAILED,
        'failed_request_id':err['request_id'],'failed_request_directory':failed_step['main']['runtime_request_directory'],
        'failed_request_seal_sha256':failed['request_seal_sha256'],
        'resource_conflict_name':conflict,'resource_conflict_sha256':failed['resource_conflict_sha256'],
        'model_postexit_sha256':rp['postexit_sha256'],'model_journal_head':rp['primary_chain_head'],
        'Flash_journal_head':rp['Flash_chain_head'],'GUI_postexit_sha256':gp['postexit_sha256'],
        'failed_controller_chain_head':suffix_done[-1]['evidence']['controller_head'],
        'original_GPU_UUIDs_in_order':uuids,
        'release_reader_seal_sha256':sha(release/'seal.json'),'failure_reader_seal_sha256':sha(failure/'seal.json')})
    edit(dst/'paired_contract.py',[('assert split == 29', 'assert split == 61')])
    edit(dst/'continuation_guard.py',[
        ("assert m['preserved_prefix_count'] == 29", "assert m['preserved_prefix_count'] == 61"),
        ("    return {'host': host, 'preserved_prefix': 29, 'prior_NF4': parent,",
         "    from verify_resource_parent import verify_resource_parent\n"
         "    resource_parent = verify_resource_parent(package, host, full, gone, events, check_gui)\n"
         "    return {'host': host, 'preserved_prefix': 61, 'prior_NF4': parent, 'resource_stop_NF4': resource_parent,"),
        ("'continuation_trajectories': 71", "'continuation_trajectories': 39")])
    files = {p.relative_to(dst).as_posix():sha(p) for p in dst.rglob('*') if p.is_file() and p.name != 'private.token'}
    modified = {n for n,h in parent['files'].items() if files[n]!=h}
    added = files.keys()-parent['files'].keys()
    assert modified == {'plan.json','paired_contract.py','continuation_guard.py'}
    assert added == {'verify_resource_parent.py','resource-stop-resume-link.json'}
    for name in files:
        if name.endswith('.py'):
            ast.parse((dst/name).read_bytes(),filename=name)
    manifest = {**parent,'files':files,'preserved_prefix_count':CUT,'trajectories':COUNT,
        'plan_sha256':files['plan.json'],'auth_token_sha256':sha(dst/'private.token'),
        'package3090':f'/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/{case}',
        'package4090':f'/data/researcher/jev-defense-four-gpu-20261106/{case}/runtime',
        'output3090':f'/data/researcher/jev-defense-four-gpu-20261106/{case}/model-attempt-01'}
    save(dst/'manifest.json',manifest)
    save(root/'continuation-boundary.json',{
        'identical_runtime_files':sorted(parent['files'].keys()-modified),'changed_files':sorted(modified),
        'added_files':sorted(added),'uncalled_model_GUI_scorer_paid_APIs':True,
        'previous_stage_preserved':PARENT,'only_unstarted_original_slots':untouched,
        'original_ledger_seal_sha256':sha(ledger/'seal.json'),'fresh_resource_admission_required':True})
    pointer = {'root':str(root),'runtime':str(dst),'manifest_sha256':sha(dst/'manifest.json'),
        'plan_sha256':manifest['plan_sha256'],'stage_id':STAGE,'measurement_version':'NF4',
        'preserved_prefix':CUT,'unstarted_suffix':COUNT,'first_run':FIRST,
        'closed_parent_collection':collection,
        'closed_parent_release':{'path':str(release.resolve()),'seal_sha256':sha(release/'seal.json')},
        'parent_stage':PARENT,'parent_manifest_sha256':parent_ptr['manifest_sha256']}
    save(CURRENT,pointer)
    return pointer


def setup():
    control.POINTER = read(CURRENT)
    control.ROOT = Path(control.POINTER['root'])
    control.PACKAGE = Path(control.POINTER['runtime'])
    assert sha(control.PACKAGE/'manifest.json') == control.POINTER['manifest_sha256']
    control.MANIFEST = read(control.PACKAGE/'manifest.json')
    assert all(sha(control.PACKAGE/n)==h for n,h in control.MANIFEST['files'].items())


def stage():
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(control.stage,h) for h in ('3090','4090') if not (control.ROOT/f'stage-{h}.json').exists()]
        for f in jobs:
            f.result()
    sources = {}
    for host in ('3090','4090'):
        f = control.ROOT/f'stage-{host}.json'
        r = read(f)
        data = r['result']
        assert bound_receipt(Path(r['operation']),host) == data
        assert data['expected'] == COUNT and data['manifest_sha256'] == control.POINTER['manifest_sha256']
        assert data['plan_sha256'] == control.POINTER['plan_sha256'] and not data['new_model_GUI_scorer_calls']
        sources[host] = sha(f)
    left, right = (read(control.ROOT/f'stage-{host}.json')['result']['availability_proof'] for host in ('3090','4090'))
    assert left['resource_stop_NF4'] == right['resource_stop_NF4']
    assert left['prior_NF4'] == right['prior_NF4']
    assert all(p['continuation_trajectories'] == COUNT and p['existing_trajectories_reexecuted'] == 0 for p in (left,right))
    result = {'same_immutable_sources_on_both_hosts':sources,'defense_conditions_changed':False,
        'preserved_previous_run_boundary':left['resource_stop_NF4'],'stage_GPU_or_model_calls':0}
    target = control.ROOT/'admission-cross-host.json'
    if not target.exists():
        save(target,result)
    assert read(target)==result
    return result


RESOURCE = r'''
import json,os,sys
from pathlib import Path
p=Path(ROOT); o=Path(OUTPUT); sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import gpu_snapshot,sha
assert os.getuid()==1033 and sha(p/'manifest.json')==EXPECTED
expected=json.loads((p/'resource-stop-resume-link.json').read_bytes())['original_GPU_UUIDs_in_order']
s=gpu_snapshot(); cards=[{'index':i,**s['gpu'][i]} for i in range(4)]
assert [c['uuid'] for c in cards]==expected
compute=[a for a in s['compute'] if a['uuid'] in expected]
fs=os.statvfs('/data'); disk=fs.f_bavail*fs.f_frsize
previous_attempt_gate=(p/'background').exists() or o.exists()
print(json.dumps({'same_verified_UUIDs':True,'cards':cards,'compute':compute,
    'disk_available_bytes':disk,'submission_or_output_already_exists':previous_attempt_gate,
    'can_attempt_fresh_lock_admission':not(previous_attempt_gate or compute) and
     disk>64*1024**3 and all(c['free_mib']>=23000 for c in cards),
    'not_a_GPU_reservation':True,'new_model_GUI_scorer_calls':0}))
'''


def probe():
    return control.remote('3090',control.prefix('3090')+RESOURCE,'read-NF4-recovery-resource-admission')


MODEL_START = old.MODEL_START.replace("==71","==39")
GUI_START = old.GUI_START.replace("==71","==39").replace(old.FIRST, FIRST)
assert old.MODEL_START.count("==71") == 1 and old.GUI_START.count("==71") == 2 and old.FIRST in old.GUI_START


def start(role):
    cross = read(control.ROOT/'admission-cross-host.json')
    assert all(sha(control.ROOT/f'stage-{h}.json')==v for h,v in cross['same_immutable_sources_on_both_hosts'].items())
    target = control.ROOT/f'{role}-submission.json'
    assert not target.exists(), 'Inspect the existing receipt; do not resubmit.'
    if role == 'model':
        pre = probe()
        assert pre['result']['can_attempt_fresh_lock_admission'], 'Original four cards are not allocatable.'
        result = control.remote('3090',control.prefix('3090')+MODEL_START,'submit-NF4-untouched-after-resource-stop')
        result['fresh_resource_precheck'] = pre
    else:
        assert (control.ROOT/'model-submission.json').is_file()
        proof = old.nf4.model_proof()
        assert proof['result']['capacity']['new_engineering_generation_calls'] == 0
        result = control.remote('4090',control.prefix('4090')+GUI_START,'submit-GUI-39-untouched-NF4')
        result['verified_model_lease'] = proof
    save(target,result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='verb',required=True)
    p = sub.add_parser('freeze')
    for name in ('ledger','release','failure','resources'):
        p.add_argument(name,type=Path)
    for name in ('stage','probe','verify-model'):
        sub.add_parser(name)
    p = sub.add_parser('start')
    p.add_argument('role',choices=('model','gui'))
    p = sub.add_parser('inspect')
    p.add_argument('host',choices=('3090','4090'))
    a = parser.parse_args()
    if a.verb == 'freeze':
        result = freeze(a.ledger,a.release,a.failure,a.resources)
    else:
        setup()
        if a.verb == 'start':
            result = start(a.role)
        elif a.verb == 'inspect':
            result = control.inspect(a.host)
        else:
            result = {'stage':stage,'probe':probe,'verify-model':old.nf4.model_proof}[a.verb]()
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
