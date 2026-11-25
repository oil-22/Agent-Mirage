"""Freeze, stage, and explicitly submit ONE new finite task to the existing holder."""
import argparse
import ast
import base64
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import types
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REV = HERE.parent
PROJECT = REV.parent
REMOTE_BASE = '/home/researcher/jev-defense-four-gpu-20261106'
REMOTE_PACKAGE = REMOTE_BASE + '/runtime-preparation/joint-main-controls-20261108-01'
REMOTE_OUTPUT = REMOTE_BASE + '/single-evidence-revision-20261107/joint-main-controls-20261108-01'
RUNTIME = HERE / 'runtime-package'
HOLDER = {'pid': 2568295, 'uid': 1033, 'start_ticks': '1159211789',
    'command': '/opt/whz/conda-envs/webmall-vlm/bin/python -u ' + REMOTE_BASE +
               '/resource_control.py --root ' + REMOTE_BASE + '/resource-attempt-20261106-01 --worker'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, v):
    with Path(p).open('x', encoding='utf8') as f:
        json.dump(v, f, ensure_ascii=False, indent=2); f.write('\n')


def remote(code, target):
    assert not target.exists()
    target.mkdir()
    (target / 'source.py').write_text(code, encoding='utf8')
    r = subprocess.run(['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=15', '3090', 'python3', '-'], input=code.encode(), capture_output=True, timeout=90)
    (target / 'stdout.json').write_bytes(r.stdout); (target / 'stderr.txt').write_bytes(r.stderr)
    save(target / 'process.json', {'returncode': r.returncode, 'new_model_calls_by_this_transport': 0})
    print(r.stdout.decode());
    if r.returncode:
        print(r.stderr.decode()); raise RuntimeError('Remote action failed; preserved, never resend blindly')
    return json.loads(r.stdout)


def freeze():
    assert not RUNTIME.exists()
    shutil.copytree(HERE / 'payload', RUNTIME, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    copies = {
        'joint_worker.py': HERE / 'joint_worker.py', 'launch_joint_once.py': HERE / 'launch_joint_once.py',
        'aux_identity_support.py': REV / 'native_image_gpu_preflight_compact02.py',
        'preflight_support.py': PROJECT / 'capacity-replay-launcher-01/preflight_service.py',
        'four_gpu_contract.py': PROJECT / 'capacity-replay-launcher-01/four_gpu_contract.py',
        'native-parser-source.py': Path('D:/MultiModel/jev-defense-validation-20261103/recovery-evidence/run_reddit_internvl_smoke.py')}
    for name, p in copies.items():
        shutil.copyfile(p, RUNTIME / name)
    gate = (REV / 'compact-launcher-02/resource_gate.py').read_text(encoding='utf8')
    changes = {
        "require(row['pid'] == current and row['uuid'] == cards[7], 'Only caller worker may compute, only on GPU7')":
        "require(row['pid'] == current and row['uuid'] in task_uuids, 'Only joint caller worker may compute, only on GPUs4–7')",
        "require(snapshot['cuda_visible_devices'] == '7', 'Auxiliary worker visibility is not physical GPU7 only')":
        "require(snapshot['cuda_visible_devices'] == '4,5,6,7', 'Joint worker visibility differs from owned GPUs4–7')",
        "'actual_compute_role': 'single_JEV_GPU7_only'": "'actual_compute_role': 'primary_4_5_6_and_single_auxiliary_7_in_one_process'"}
    for old, new in changes.items():
        assert gate.count(old) == 1
        gate = gate.replace(old, new)
    (RUNTIME / 'resource_gate.py').write_text(gate, encoding='utf8')
    for p in RUNTIME.rglob('*.py'):
        ast.parse(p.read_text(encoding='utf8'), filename=str(p))
    spec = importlib.util.spec_from_file_location('joint_gate_CPU', RUNTIME / 'resource_gate.py')
    g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
    old_tests = REV / 'gpu-preflight-launcher-01/test_resource_and_launch_contract.py'
    fixture = next(n for n in ast.parse(old_tests.read_text(encoding='utf8')).body if isinstance(n, ast.FunctionDef) and n.name == 'fixture')
    namespace = {'copy': copy, 'gate': g, 'launch': types.SimpleNamespace(HOLDER=HOLDER,
        PYTHON='/opt/whz/conda-envs/webmall-vlm/bin/python', PACKAGE=Path(REMOTE_PACKAGE))}
    exec(compile(ast.Module(body=[fixture], type_ignores=[]), str(old_tests), 'exec'), namespace)
    def case():
        lease, holder, allowed, snapshot = namespace['fixture']()
        snapshot['cuda_visible_devices'] = '4,5,6,7'
        return lease, holder, allowed, snapshot
    passed = []
    for i in [4, 5, 6, 7]:
        lease, holder, allowed, snap = case()
        snap['gpu']['compute'] = [{'pid': snap['self_identity']['pid'], 'uuid': 'GPU-CPU-FIXTURE-' + str(i)}]
        assert g.validate_snapshot(lease, holder, allowed, snap, False)['owned_task_group']
        passed.append('joint_worker_own_compute_GPU' + str(i))
        for bad in [3000999, 3000122]:
            s = copy.deepcopy(snap); s['gpu']['compute'][0]['pid'] = bad
            try:
                g.validate_snapshot(lease, holder, allowed, s, False)
            except g.ResourceGateError:
                passed.append('reject_GPU%d_unregistered_or_launcher_%d' % (i, bad))
            else:
                raise AssertionError('Unowned/launcher compute admitted')
    for name, change in [
        ('stale_holder', lambda s: s['holder_identity'].update(start_ticks='changed')),
        ('wrong_UUID', lambda s: s['gpu']['cards'][4].update(uuid='GPU-OTHER')),
        ('missing_lock', lambda s: s['self_locks'].pop()),
        ('wrong_inode', lambda s: s['self_locks'][0].update(inode=123)),
        ('insufficient_headroom', lambda s: s['gpu']['cards'][6].update(free_mib=22999)),
    ]:
        lease, holder, allowed, snap = case(); snap = copy.deepcopy(snap); change(snap)
        try:
            g.validate_snapshot(lease, holder, allowed, snap, True)
        except g.ResourceGateError:
            passed.append('reject_' + name)
        else:
            raise AssertionError('Resource boundary wrongly admitted: ' + name)
    save(RUNTIME / 'new-resource-CPU-checks.json', {'passed': passed, 'count': len(passed),
        'GPU_model_allocations': 0, 'scope': 'new one-process multi-GPU ownership boundaries only'})
    manifest = {'schema': 'finite-primary-single-auxiliary-runtime-v1', 'authorized_finite_joint_development': True,
        'expected_holder': HOLDER, 'lease_sha256': '8f5da746fbb45c587d23a0073f8dc62dcd9510b321b4cef0995c09aa8c92a89a',
        'files': {p.relative_to(RUNTIME).as_posix(): sha(p) for p in sorted(RUNTIME.rglob('*')) if p.is_file()},
        'worker_source_sha256': sha(RUNTIME / 'joint_worker.py'),
        'PRIVATE_source_expectation_seal_local_only': sha(HERE / 'PRIVATE-source-expectations-seal.json'),
        'outputs': REMOTE_OUTPUT, 'auxiliary_count': 1, 'four_owned_GPUs': [4, 5, 6, 7],
        'no_paid_GUI_or_scorer': True, 'no_old_terminals_replayed': True}
    save(RUNTIME / 'manifest.json', manifest)
    save(HERE / 'runtime-freeze.json', {'manifest_sha256': sha(RUNTIME / 'manifest.json'),
        'files': len(manifest['files']), 'CPU_boundaries_passed': len(passed), 'new_model_calls': 0,
        'only_source_based_new_constructed_candidates': True})
    print(json.dumps({'manifest_sha256': sha(RUNTIME / 'manifest.json'), 'CPU_boundaries_passed': len(passed)}))


def stage():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in RUNTIME.rglob('*'):
            if p.is_file():
                z.writestr(p.relative_to(RUNTIME).as_posix(), p.read_bytes())
    payload = base64.b64encode(buf.getvalue()).decode()
    expected = sha(RUNTIME / 'manifest.json')
    code = 'PAYLOAD=' + repr(payload) + '\nTARGET=' + repr(REMOTE_PACKAGE) + '\nSHA=' + repr(expected) + '\n' + r'''
import base64,zipfile,io,json,hashlib,pathlib,os,time,ast
assert os.getuid()==1033
root=pathlib.Path(TARGET);assert not root.exists()
root.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD))) as z:
 for n in z.namelist():assert (root/n).resolve().is_relative_to(root.resolve())
 z.extractall(root)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'manifest.json')==SHA
m=json.loads((root/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(root/n)==h,n
for p in root.rglob('*.py'):ast.parse(p.read_text(encoding='utf8'))
print(json.dumps({'staged':str(root),'manifest_sha256':SHA,'verified_files':len(m['files']),'time_unix':time.time(),'model_calls':0}))
'''
    remote(code, HERE / 'actual-stage-01')


def submit():
    expected = sha(RUNTIME / 'manifest.json')
    command = {'action': 'launch', 'argv': ['/opt/whz/conda-envs/webmall-vlm/bin/python',
        REMOTE_PACKAGE + '/launch_joint_once.py', '--manifest', REMOTE_PACKAGE + '/manifest.json',
        '--manifest-sha256', expected, '--output', REMOTE_OUTPUT],
        'script_sha256': sha(RUNTIME / 'launch_joint_once.py')}
    code = 'COMMAND=' + repr(command) + '\nMANIFEST_SHA=' + repr(expected) + '\n' + r'''
from pathlib import Path
import json,os,hashlib,time,subprocess
assert os.getuid()==1033
b=Path('/home/researcher/jev-defense-four-gpu-20261106');r=b/'resource-attempt-20261106-01'
lease=json.loads((r/'lease.json').read_bytes());holder=lease['holder'];p=Path('/proc')/str(holder['pid'])
tail=(p/'stat').read_text().rsplit(')',1)[1].split()
actual={'pid':holder['pid'],'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':tail[19]}
assert all(str(actual[k])==str(holder[k])for k in actual) and tail[0]not in ['Z','X']
for row in lease['lock_records']:
 fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path'] and fd.stat().st_ino==row['inode'] and 'FLOCK'in info and 'WRITE '+str(holder['pid'])in info
target={x['uuid']for x in lease['gpu']}
cards=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],universal_newlines=True)
for line in cards.splitlines():
 i,u,f=[s.strip()for s in line.split(',')]
 if int(i)in [4,5,6,7]:assert u in target and int(f)>=23000
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],universal_newlines=True)
assert not any(line.split(',')[0].strip()in target for line in compute.splitlines()if line.strip())
assert not Path(COMMAND['argv'][COMMAND['argv'].index('--output')+1]).exists()
for f in (r/'commands').glob('*.json'):
 assert f.with_suffix('.claimed').exists(),'Other pending command; inspect rather than race'
script=Path(COMMAND['argv'][1]);assert hashlib.sha256(script.read_bytes()).hexdigest()==COMMAND['script_sha256']
manifest=Path(COMMAND['argv'][3]);assert hashlib.sha256(manifest.read_bytes()).hexdigest()==MANIFEST_SHA
path=r/'commands/joint-main-controls-20261108-01.json'
raw=json.dumps(COMMAND,sort_keys=True,ensure_ascii=False,indent=2).encode()
# Atomic publish: holder cannot see a partially written command.
tmp=r/'commands'/('.joint-main-'+str(os.getpid())+'.tmp')
with tmp.open('xb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
os.link(tmp,path);tmp.unlink()
print(json.dumps({'submitted_once':True,'command':str(path),'command_sha256':hashlib.sha256(raw).hexdigest(),
 'manifest_sha256':MANIFEST_SHA,'holder_actual':actual,'nine_actual_locks':len(lease['lock_records']),
 'cards':cards,'compute':compute,'time_unix':time.time(),'model_calls_by_submitter':0}))
'''
    result = remote(code, HERE / 'actual-submission-01')
    save(HERE / 'launch.json', result)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['freeze', 'stage', 'submit'])
    action = p.parse_args().action
    {'freeze': freeze, 'stage': stage, 'submit': submit}[action]()
