"""Linked zero-model-call resource-check repair; original terminal stays immutable."""
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
PROJECT = HERE.parents[1]
RETRY = HERE / 'technical-retry-02'
RUNTIME = RETRY / 'runtime-package'
BASE = '/home/researcher/jev-defense-four-gpu-20261106'
REMOTE = BASE + '/runtime-preparation/joint-main-controls-20261108-02'
OUTPUT = BASE + '/single-evidence-revision-20261107/joint-main-controls-20261108-02'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, v):
    with Path(p).open('x', encoding='utf8') as f:
        json.dump(v, f, ensure_ascii=False, indent=2); f.write('\n')


def remote(code, target):
    target.mkdir(exist_ok=False)
    (target / 'source.py').write_text(code, encoding='utf8')
    r = subprocess.run(['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes',
        '3090', '/opt/whz/conda-envs/webmall-vlm/bin/python', '-'], input=code.encode(), capture_output=True, timeout=120)
    (target / 'stdout.json').write_bytes(r.stdout); (target / 'stderr.txt').write_bytes(r.stderr)
    if r.returncode:
        print(r.stderr.decode()); raise RuntimeError('New linked operation failed; inspect original evidence')
    return json.loads(r.stdout)


def prepare():
    assert not RETRY.exists(); RETRY.mkdir()
    code = r'''
from pathlib import Path
import json,hashlib,base64,io,zipfile,os,time
r=Path('/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/joint-main-controls-20261108-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((r/'terminal-manifest.json').read_bytes())
for n,h in m.items():assert sha(r/n)==h,n
t=json.loads((r/'worker/terminal.json').read_bytes());assert t['attempted']=={'auxiliary':[],'judge':[]}and t['status']=='technical_failure'
for n in ['worker/process.json','launcher-process.json']:
 p=json.loads((r/n).read_bytes())['pid'];assert not Path('/proc',str(p)).exists()
assert not (r/'worker/loaded.json').exists()
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED)as z:
 for p in r.rglob('*'):
  if p.is_file():z.writestr(str(p.relative_to(r)),p.read_bytes())
print(json.dumps({'original_root':str(r),'original_terminal_manifest_sha256':sha(r/'terminal-manifest.json'),
 'original_entries_verified':len(m),'actual_original_workers_exited':True,'original_model_loads_or_calls':0,
 'preserved_zip_base64':base64.b64encode(buf.getvalue()).decode(),'time_unix':time.time()}))
'''
    d = remote(code, RETRY / 'failure-collection-control')
    collected = RETRY / 'original-failure'; collected.mkdir()
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(d.pop('preserved_zip_base64')))) as z:
        for n in z.namelist():
            assert (collected / n).resolve().is_relative_to(collected.resolve())
        z.extractall(collected)
    for n, h in json.loads((collected / 'terminal-manifest.json').read_bytes()).items():
        assert sha(collected / n) == h
    save(RETRY / 'failure-preservation.json', d)
    shutil.copytree(HERE / 'runtime-package', RUNTIME)
    # New source package; the old sealed source and output are never edited.
    old_manifest = json.loads((RUNTIME / 'manifest.json').read_bytes())
    (RUNTIME / 'manifest.json').rename(RUNTIME / 'parent-manifest.json')
    p = RUNTIME / 'resource_gate.py'; source = p.read_text(encoding='utf8')
    needle = "    actual_cards = {int(k): v for k, v in snapshot['gpu']['cards'].items()}"
    addition = '''    additional = snapshot.get('additional_owned_inference_mutex_locks', [])
    require(len(additional) <= 1, 'More than one additional caller lock')
    if additional:
        row = additional[0]
        expected_path = '/home/researcher/jev-defense-four-gpu-20261106/inference.lock'
        require(lease.get('inference_lock') == expected_path and row['path'] == expected_path,
                'Additional lock is not the exact task inference mutex')
        require(row['fd'] not in fds, 'Inference mutex collides with a resource FD')
        st = snapshot['inference_mutex_file']
        require(st['uid'] == EXPECTED_UID and st['inode'] == row['inode'] and st['device'] == row['device'],
                'Additional inference mutex inode/device/UID differs')
        require(len(row['held_lock_lines']) == 1, 'Ambiguous inference mutex FLOCK')
        pieces = row['held_lock_lines'][0].split()
        require('FLOCK' in pieces and 'ADVISORY' in pieces and 'WRITE' in pieces,
                'Inference mutex is not actually exclusively flocked')
        require(pieces[pieces.index('WRITE') + 1] == str(current),
                'Inference mutex is not independently owned by this caller')
'''
    assert source.count(needle) == 1
    source = source.replace(needle, addition + needle)
    needle = '    try:\n        result = validate_snapshot(lease, expected_holder, registered, snapshot, require_empty, minimum_free_mib)'
    addition = '''    resource_fds = {int(row['fd']) for row in lease['lock_records']}
    all_caller_locks = snapshot['self_locks']
    snapshot['self_locks'] = [row for row in all_caller_locks if row['fd'] in resource_fds]
    additional = [row for row in all_caller_locks if row['fd'] not in resource_fds]
    snapshot['additional_owned_inference_mutex_locks'] = additional
    if additional:
        stat = Path('/home/researcher/jev-defense-four-gpu-20261106/inference.lock').stat()
        snapshot['inference_mutex_file'] = {'uid': stat.st_uid, 'inode': stat.st_ino, 'device': stat.st_dev}
'''
    assert source.count(needle) == 1
    p.write_text(source.replace(needle, addition + needle), encoding='utf8')
    p = RUNTIME / 'launch_joint_once.py'; source = p.read_text(encoding='utf8')
    source = source.replace('joint-main-controls-20261108-01', 'joint-main-controls-20261108-02')
    p.write_text(source, encoding='utf8')
    for p in RUNTIME.rglob('*.py'):
        ast.parse(p.read_text(encoding='utf8'))
    spec = importlib.util.spec_from_file_location('linked_joint_gate', RUNTIME / 'resource_gate.py')
    gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
    test = HERE.parent / 'gpu-preflight-launcher-01/test_resource_and_launch_contract.py'
    function = next(n for n in ast.parse(test.read_text(encoding='utf8')).body if isinstance(n, ast.FunctionDef) and n.name == 'fixture')
    ns = {'copy': copy, 'gate': gate, 'launch': types.SimpleNamespace(HOLDER=old_manifest['expected_holder'],
        PYTHON='/opt/whz/conda-envs/webmall-vlm/bin/python', PACKAGE=Path(REMOTE))}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(test), 'exec'), ns)
    def fixture(extra=True):
        lease, holder, allowed, snap = ns['fixture']()
        lease['inference_lock'] = BASE + '/inference.lock'; snap['cuda_visible_devices'] = '4,5,6,7'
        snap['gpu']['compute'] = [{'pid': snap['self_identity']['pid'], 'uuid': 'GPU-CPU-FIXTURE-' + str(i)} for i in [4, 5, 6, 7]]
        if extra:
            snap['additional_owned_inference_mutex_locks'] = [{'fd': 12, 'path': lease['inference_lock'],
                'inode': 777, 'device': 2065, 'held_lock_lines': ['lock: 1: FLOCK ADVISORY WRITE 3000123 08:11:777 0 EOF']}]
            snap['inference_mutex_file'] = {'uid': 1033, 'inode': 777, 'device': 2065}
        return lease, holder, allowed, snap
    passed = []
    for extra in [False, True]:
        lease, holder, allowed, snap = fixture(extra)
        assert gate.validate_snapshot(lease, holder, allowed, snap, False)['owned_task_group']
        passed.append('valid_nine_GPU_locks_with_owned_mutex_' + str(extra))
    for name, change in [
        ('mutex_foreign_owner', lambda s: s['additional_owned_inference_mutex_locks'][0].update(held_lock_lines=['lock: 1: FLOCK ADVISORY WRITE 999 08:11:777 0 EOF'])),
        ('mutex_wrong_inode', lambda s: s['inference_mutex_file'].update(inode=778)),
        ('mutex_foreign_UID', lambda s: s['inference_mutex_file'].update(uid=1001)),
        ('mutex_wrong_path', lambda s: s['additional_owned_inference_mutex_locks'][0].update(path='/tmp/foreign.lock')),
        ('extra_unapproved_lock', lambda s: s['additional_owned_inference_mutex_locks'].append(copy.deepcopy(s['additional_owned_inference_mutex_locks'][0]))),
        ('mutex_resource_FD_collision', lambda s: s['additional_owned_inference_mutex_locks'][0].update(fd=3)),
        ('GPU_lock_still_required', lambda s: s['self_locks'].pop()),
        ('GPU_foreign_compute', lambda s: s['gpu']['compute'][0].update(pid=999)),
        ('stale_holder', lambda s: s['holder_identity'].update(start_ticks='stale')),
    ]:
        lease, holder, allowed, snap = fixture(); snap = copy.deepcopy(snap); change(snap)
        try:
            gate.validate_snapshot(lease, holder, allowed, snap, False)
        except gate.ResourceGateError:
            passed.append('reject_' + name)
        else:
            raise AssertionError('Resource boundary admitted ' + name)
    save(RUNTIME / 'linked-mutex-boundary-checks.json', {'count': len(passed), 'passed': passed,
        'original_nine_resource_locks_still_required': True, 'model_allocations_or_calls': 0})
    changed = ['resource_gate.py', 'launch_joint_once.py']
    save(RUNTIME / 'technical-repair.json', {'parent_terminal_manifest_sha256': d['original_terminal_manifest_sha256'],
        'parent_model_loads_or_calls': 0, 'changed_sources': changed,
        'repair': 'Validate the one independently-owned inference mutex in addition to all nine inherited GPU locks',
        'worker_source_unchanged': sha(RUNTIME / 'joint_worker.py') == sha(HERE / 'runtime-package/joint_worker.py'),
        'input_plan_models_generation_and_limits_unchanged': True, 'new_attempt_output': OUTPUT})
    m = copy.deepcopy(old_manifest); m['outputs'] = OUTPUT
    m['files'] = {p.relative_to(RUNTIME).as_posix(): sha(p)for p in sorted(RUNTIME.rglob('*'))if p.is_file()}
    save(RUNTIME / 'manifest.json', m)
    save(RETRY / 'freeze.json', {'manifest_sha256': sha(RUNTIME / 'manifest.json'), 'passed_new_boundaries': len(passed),
        'only_two_source_changes': changed})
    print(json.dumps({'prepared': str(RETRY), 'manifest_sha256': sha(RUNTIME / 'manifest.json'), 'CPU_checks': len(passed)}))


def stage_submit():
    assert (RETRY / 'freeze.json').exists() and not (RETRY / 'actual-submission').exists()
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in RUNTIME.rglob('*'):
            if p.is_file():
                z.writestr(p.relative_to(RUNTIME).as_posix(), p.read_bytes())
    manifest_sha = sha(RUNTIME / 'manifest.json')
    command = {'action': 'launch', 'argv': ['/opt/whz/conda-envs/webmall-vlm/bin/python', REMOTE + '/launch_joint_once.py',
        '--manifest', REMOTE + '/manifest.json', '--manifest-sha256', manifest_sha, '--output', OUTPUT],
        'script_sha256': sha(RUNTIME / 'launch_joint_once.py')}
    code = 'PAYLOAD=' + repr(base64.b64encode(raw.getvalue()).decode()) + '\nREMOTE=' + repr(REMOTE) + '\nCOMMAND=' + repr(command) + '\nSHA=' + repr(manifest_sha) + '\n' + r'''
import pathlib,json,hashlib,base64,io,zipfile,os,subprocess,time
assert os.getuid()==1033
b=pathlib.Path('/home/researcher/jev-defense-four-gpu-20261106');old=b/'single-evidence-revision-20261107/joint-main-controls-20261108-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in json.loads((old/'terminal-manifest.json').read_bytes()).items():assert sha(old/n)==h
t=json.loads((old/'worker/terminal.json').read_bytes());assert t['attempted']=={'auxiliary':[],'judge':[]}
for n in ['worker/process.json','launcher-process.json']:assert not pathlib.Path('/proc',str(json.loads((old/n).read_bytes())['pid'])).exists()
root=pathlib.Path(REMOTE);assert not root.exists();root.mkdir()
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for n in z.namelist():assert(root/n).resolve().is_relative_to(root.resolve())
 z.extractall(root)
assert sha(root/'manifest.json')==SHA
m=json.loads((root/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(root/n)==h,n
lease_path=b/'resource-attempt-20261106-01/lease.json';assert sha(lease_path)==m['lease_sha256'];lease=json.loads(lease_path.read_bytes())
h=lease['holder'];p=pathlib.Path('/proc')/str(h['pid']);tail=(p/'stat').read_text().rsplit(')',1)[1].split()
assert p.stat().st_uid==h['uid']and tail[19]==h['start_ticks']and(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()==h['command']
for r in lease['lock_records']:
 fd=p/'fd'/str(r['fd']);info=(p/'fdinfo'/str(r['fd'])).read_text();assert os.readlink(fd)==r['path']and fd.stat().st_ino==r['inode']and 'FLOCK'in info and 'WRITE 2568295'in info
target={r['uuid']for r in lease['gpu']}
cards=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
for line in cards.splitlines():
 i,u,f=[x.strip()for x in line.split(',')]
 if int(i)in [4,5,6,7]:assert u in target and int(f)>=23000
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(line.split(',')[0].strip()in target for line in compute.splitlines()if line.strip())
assert not pathlib.Path(COMMAND['argv'][-1]).exists()
commands=b/'resource-attempt-20261106-01/commands'
assert all(p.with_suffix('.claimed').exists()for p in commands.glob('*.json'))
assert sha(pathlib.Path(COMMAND['argv'][1]))==COMMAND['script_sha256']
path=commands/'joint-main-controls-20261108-02.json';temp=commands/('.joint-retry-'+str(os.getpid())+'.tmp')
data=json.dumps(COMMAND,ensure_ascii=False,indent=2).encode()
with temp.open('xb')as f:f.write(data);f.flush();os.fsync(f.fileno())
os.link(temp,path);temp.unlink()
print(json.dumps({'submitted_once':True,'remote_package':str(root),'remote_output':COMMAND['argv'][-1],
 'manifest_sha256':SHA,'command_sha256':sha(path),'actual_held_GPU_locks':9,'old_terminal_preserved_and_zero_calls':True,
 'time_unix':time.time(),'model_calls_by_submitter':0}))
'''
    d = remote(code, RETRY / 'actual-submission')
    save(RETRY / 'launch.json', d)
    print(json.dumps(d))


if __name__ == '__main__':
    p = sys.argv[1]
    {'prepare': prepare, 'submit': stage_submit}[p]()
