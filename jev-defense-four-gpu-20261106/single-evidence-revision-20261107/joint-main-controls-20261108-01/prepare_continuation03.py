"""New linked placement-only continuation of unfinished C05-C08, never old results."""
import ast
import base64
import copy
import difflib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RETRY = HERE / 'technical-continuation-03'
RUNTIME = RETRY / 'runtime-package'
PARENT = HERE / 'terminal-collection/1794141466927603400/original'
BASE = '/home/researcher/jev-defense-four-gpu-20261106'
REMOTE = BASE + '/runtime-preparation/joint-main-controls-20261108-03'
OUTPUT = BASE + '/single-evidence-revision-20261107/joint-main-controls-20261108-03'
PARENT_REMOTE = BASE + '/single-evidence-revision-20261107/joint-main-controls-20261108-02'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def replace_once(source, old, new):
    assert source.count(old) == 1, old[:150]
    return source.replace(old, new)


def prepare():
    assert not RETRY.exists()
    RETRY.mkdir()
    parent_terminal = json.loads((PARENT / 'worker/terminal.json').read_bytes())
    audit = json.loads((PARENT.parent / 'collection-audit.json').read_bytes())
    assert audit['terminal']['all_SHA_verified'] and not audit['errors']
    assert parent_terminal['status'] == 'technical_failure'
    assert parent_terminal['attempted']['judge'][-1] == {'case': 'C05', 'call': '06'}
    assert len(parent_terminal['attempted']['judge']) == 6
    assert len(parent_terminal['completed']['judge']) == 5
    assert len(parent_terminal['completed']['auxiliary']) == 4
    shutil.copytree(HERE / 'technical-retry-02/runtime-package', RUNTIME)
    old_manifest = json.loads((RUNTIME / 'manifest.json').read_bytes())
    (RUNTIME / 'manifest.json').rename(RUNTIME / 'parent02-manifest.json')
    original_plan = json.loads((RUNTIME / 'plan.json').read_bytes())
    (RUNTIME / 'plan.json').rename(RUNTIME / 'parent02-plan.json')
    plan = copy.deepcopy(original_plan)
    plan['auxiliary'] = []
    plan['judges'] = [v for v in plan['judges'] if v['id'] in ['C05','C06','C07','C08']]
    assert [v['id'] for v in plan['judges']] == ['C05','C06','C07','C08']
    plan['limits'].update(auxiliary=0, judge=8)
    plan['primary_layer_counts'] = [19,24,21]
    plan['prior_auxiliary_calls_in_24_cap'] = 12
    plan['prior_judge_calls_in_original_16_cap'] = 6
    plan['maximum_total_judge_after_continuation'] = 14
    plan['maximum_total_auxiliary_after_this_batch'] = 12
    plan['only_unfinished_infrastructure_failure_and_unattempted_sources'] = True
    plan['capacity_scope'] = 'Only these four original full inputs; no full-GUI maximum-history guarantee'
    save(RUNTIME / 'plan.json', plan)
    continuation = {
        'parent_remote_root': PARENT_REMOTE,
        'parent_terminal_manifest_sha256': sha(PARENT / 'terminal-manifest.json'),
        'parent_terminal_sha256': sha(PARENT / 'worker/terminal.json'),
        'parent_exit_sha256': sha(PARENT / 'exit.json'),
        'parent_worker_and_launcher_exited_before_retry': True,
        'parent_failed_request_sha256': sha(PARENT / 'worker/judges/06/request.json'),
        'parent_failed_prepared': json.loads((PARENT / 'worker/judges/06/prepared.json').read_bytes()),
        'original_judge_cap':16, 'prior_calls_including_OOM':6, 'new_judge_cap':8,
        'prior_completed_logical_controls':['C01','C02','C03','C04'],
        'new_logical_controls':['C05','C06','C07','C08'],
        'auxiliary_calls_in_this_continuation':0,
        'previous_4_auxiliary_outputs_preserved_without_reexecution': True,
        'placement_only_condition_change':[{'before':[18,24,22],'after':[19,24,21]}],
        'bitwise_outputs_across_placements_not_asserted':True,
        'new_output':OUTPUT,
    }
    save(RUNTIME / 'continuation.json', continuation)
    p = RUNTIME / 'joint_worker.py'
    old = p.read_text(encoding='utf8')
    src = old
    src = replace_once(src, "{'auxiliary': 4, 'judge': 16, 'actor': 0, 'GUI': 0, 'scorer': 0,", "{'auxiliary': 0, 'judge': 8, 'actor': 0, 'GUI': 0, 'scorer': 0,")
    src = replace_once(src, "    assert len(plan['auxiliary']) == 4 and len(plan['judges']) == 8", """    assert not plan['auxiliary'] and [v['id'] for v in plan['judges']] == ['C05','C06','C07','C08']
    continuation = json.loads((package / 'continuation.json').read_bytes())
    parent = Path(continuation['parent_remote_root'])
    assert sha(parent / 'terminal-manifest.json') == continuation['parent_terminal_manifest_sha256']
    for n,h in json.loads((parent / 'terminal-manifest.json').read_bytes()).items():
        assert sha(parent / n) == h, 'Original preserved terminal changed: ' + n
    assert sha(parent / 'worker/terminal.json') == continuation['parent_terminal_sha256']
    assert sha(parent / 'exit.json') == continuation['parent_exit_sha256']
    parent_t = json.loads((parent / 'worker/terminal.json').read_bytes())
    assert parent_t['status'] == 'technical_failure'
    assert len(parent_t['attempted']['judge']) == continuation['prior_calls_including_OOM'] == 6
    assert parent_t['attempted']['judge'][-1] == {'case':'C05','call':'06'}
    assert len(parent_t['completed']['judge']) == 5 and len(parent_t['completed']['auxiliary']) == 4
    assert 6 + plan['limits']['judge'] <= continuation['original_judge_cap'] == 16
    assert not ({v['id'] for v in plan['judges']} & set(continuation['prior_completed_logical_controls']))
    for n in ['worker/process.json','launcher-process.json']:
        old_pid = json.loads((parent / n).read_bytes())['pid']
        assert not Path('/proc',str(old_pid)).exists(), 'Old process still exists; no duplicate allocation'""")
    src = replace_once(src, "0 if i < 18 else 1 if i < 42 else 2", "0 if i < 19 else 1 if i < 43 else 2")
    src = replace_once(src, "'primary_layer_counts': [18, 24, 22]", "'primary_layer_counts': [19, 24, 21]")
    src = replace_once(src, "                save(target / 'prepared.json', prepared)", """                save(target / 'prepared.json', prepared)
                if target == root / 'judges/01':
                    assert set(prepared) == set(continuation['parent_failed_prepared'])
                    for n,v in prepared.items():
                        assert all(v[k] == continuation['parent_failed_prepared'][n][k]
                                   for k in ['shape','dtype','bytes','sha256']), 'Failed input changed: ' + n""")
    src = replace_once(src, "                result = original_generate(**kwargs)", """                try:
                    result = original_generate(**kwargs)
                except BaseException:
                    save(target / 'failed-memory.json', support.memory(torch))
                    raise""")
    src = replace_once(src, "assert call_count['value'] < 16, 'Frozen judge budget'", "assert call_count['value'] < 8, 'Frozen continuation judge budget; prior6+new8<=16'")
    src = replace_once(src, "            attempted['judge'].append({'case': current_case['id'], 'call': rid})", """            if rid == '01':
                assert current_case['id'] == 'C05'
                assert sha(target / 'request.json') == continuation['parent_failed_request_sha256'], 'Original failed full request differs'
            attempted['judge'].append({'case': current_case['id'], 'call': rid})""")
    src = replace_once(src, "            'both_models_jointly_resident_and_generated': True, 'full_GUI_capacity_or_efficacy_proven': False,", """            'both_models_jointly_resident': True, 'auxiliary_loaded_with_zero_new_auxiliary_calls': True,
            'prior_auxiliary_results_preserved': True, 'parent_judge_calls_including_OOM': 6,
            'cumulative_judge_calls_in_original16cap': 6 + call_count['value'],
            'full_GUI_capacity_or_efficacy_proven': False,""")
    p.write_text(src, encoding='utf8')
    (RETRY / 'worker-technical-diff.txt').write_text(''.join(difflib.unified_diff(old.splitlines(True), src.splitlines(True),
        fromfile='immutable-attempt02-worker',tofile='new-continuation03-worker')), encoding='utf8')
    p = RUNTIME / 'launch_joint_once.py'
    p.write_text(p.read_text(encoding='utf8').replace('joint-main-controls-20261108-02','joint-main-controls-20261108-03'), encoding='utf8')
    checks=[]
    for p in RUNTIME.rglob('*.py'):
        ast.parse(p.read_text(encoding='utf8')); checks.append('AST:' + p.relative_to(RUNTIME).as_posix())
    assert sha(RUNTIME/'resource_gate.py') == sha(HERE/'technical-retry-02/runtime-package/resource_gate.py')
    for p in (RUNTIME/'release').rglob('*.py'):
        assert sha(p) == sha(HERE/'technical-retry-02/runtime-package'/p.relative_to(RUNTIME)), p
    for row in plan['judges']:
        assert sha(RUNTIME / row['path']) == row['sha256']
    assert not plan['auxiliary'] and continuation['new_judge_cap']*1 + 6 <= 16
    for bad_ids in [['C01','C06','C07','C08'], ['C05','C05','C07','C08'], ['C05','C06','C07']]:
        assert bad_ids != [r['id'] for r in plan['judges']]
    save(RUNTIME / 'technical-continuation-checks.json', {'all_runtime_Python_AST_parsed':len(checks),
        'all_native_release_sources_and_resource_gate_SHA_unchanged':True,
        'four_full_input_files_SHA_unchanged':True,'no_auxiliary_replay':True,
        'only_C05_C06_C07_C08_admitted':True,'prior6_plus_new8_le_original16cap':True,
        'old_completion_negative_results_not_retried':True,'CPU_checks_are_not_capacity_proof':True})
    m = copy.deepcopy(old_manifest)
    m['outputs'] = OUTPUT
    m['worker_source_sha256'] = sha(RUNTIME/'joint_worker.py')
    m['files'] = {p.relative_to(RUNTIME).as_posix():sha(p) for p in sorted(RUNTIME.rglob('*')) if p.is_file()}
    save(RUNTIME/'manifest.json',m)
    save(RETRY/'freeze.json', {'manifest_sha256':sha(RUNTIME/'manifest.json'),'new_judge_cap':8,
        'new_auxiliary_cap':0,'placement':[19,24,21],'parent_terminal_preserved':str(PARENT)})
    print(json.dumps({'prepared':str(RETRY),'manifest_sha256':sha(RUNTIME/'manifest.json'),'no_models_called':True}))


def submit():
    assert (RETRY/'freeze.json').exists() and not (RETRY/'actual-submission').exists()
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w',zipfile.ZIP_DEFLATED) as z:
        for p in RUNTIME.rglob('*'):
            if p.is_file():z.writestr(p.relative_to(RUNTIME).as_posix(),p.read_bytes())
    manifest_sha=sha(RUNTIME/'manifest.json')
    command={'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',REMOTE+'/launch_joint_once.py',
        '--manifest',REMOTE+'/manifest.json','--manifest-sha256',manifest_sha,'--output',OUTPUT],
        'script_sha256':sha(RUNTIME/'launch_joint_once.py')}
    code='PAYLOAD='+repr(base64.b64encode(raw.getvalue()).decode())+'\nREMOTE='+repr(REMOTE)+'\nCOMMAND='+repr(command)+'\nSHA='+repr(manifest_sha)+'\n'+r'''
from pathlib import Path
import json,hashlib,base64,io,zipfile,os,subprocess,time
assert os.getuid()==1033
b=Path('/home/researcher/jev-defense-four-gpu-20261106')
old=b/'single-evidence-revision-20261107/joint-main-controls-20261108-02'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(old/'terminal-manifest.json')=='f8a6eecf9bdb9e7a5bcbd99751a7b4cd9285f6e1ea78121ff88682f761baa48c'
for n in ['worker/process.json','launcher-process.json']:
 assert not Path('/proc',str(json.loads((old/n).read_bytes())['pid'])).exists()
root=Path(REMOTE);assert not root.exists();root.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD))) as z:
 for n in z.namelist():assert(root/n).resolve().is_relative_to(root.resolve())
 z.extractall(root)
assert sha(root/'manifest.json')==SHA
m=json.loads((root/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(root/n)==h,n
lease_path=b/'resource-attempt-20261106-01/lease.json'
assert sha(lease_path)==m['lease_sha256']
lease=json.loads(lease_path.read_bytes());h=lease['holder'];p=Path('/proc',str(h['pid']))
tail=(p/'stat').read_text().rsplit(')',1)[1].split()
assert p.stat().st_uid==h['uid'] and tail[19]==h['start_ticks']
assert (p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()==h['command']
for row in lease['lock_records']:
 fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path'] and fd.stat().st_ino==row['inode'] and 'FLOCK' in info and 'WRITE 2568295' in info
target={r['uuid'] for r in lease['gpu']}
cards=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
for line in cards.splitlines():
 i,u,f=[x.strip() for x in line.split(',')]
 if int(i) in [4,5,6,7]:assert u in target and int(f)>=23000
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(line.split(',')[0].strip() in target for line in compute.splitlines() if line.strip())
assert not Path(COMMAND['argv'][-1]).exists()
commands=b/'resource-attempt-20261106-01/commands'
assert all(p.with_suffix('.claimed').exists() for p in commands.glob('*.json'))
path=commands/'joint-main-controls-20261108-03.json';temp=commands/('.joint-continuation-'+str(os.getpid())+'.tmp')
data=json.dumps(COMMAND,ensure_ascii=False,indent=2).encode()
with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
os.link(temp,path);temp.unlink()
print(json.dumps({'submitted_once':True,'remote_package':str(root),'remote_output':COMMAND['argv'][-1],
 'manifest_sha256':SHA,'command_sha256':sha(path),'actual_held_GPU_locks':9,
 'old_failed_terminal_preserved':True,'new_auxiliary_calls':0,'maximum_new_judge_calls':8,
 'time_unix':time.time(),'model_calls_by_submitter':0}))
'''
    dest=RETRY/'actual-submission';dest.mkdir()
    (dest/'source.py').write_text(code,encoding='utf8')
    res=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','-o','BatchMode=yes',
        '3090','/opt/whz/conda-envs/webmall-vlm/bin/python','-'],input=code.encode(),capture_output=True,timeout=60)
    (dest/'stdout.json').write_bytes(res.stdout);(dest/'stderr.txt').write_bytes(res.stderr)
    if res.returncode:raise RuntimeError(res.stderr.decode(errors='replace'))
    d=json.loads(res.stdout);save(RETRY/'launch.json',d);print(json.dumps(d))


if __name__=='__main__':
    {'prepare':prepare,'submit':submit}[sys.argv[1]]()
