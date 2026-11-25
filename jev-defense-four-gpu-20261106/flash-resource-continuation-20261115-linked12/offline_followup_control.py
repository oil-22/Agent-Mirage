"""Prepare/stage, then submit the unchanged approved offline10 after all29 exits.

Preparation and staging cannot submit a model command. Submission requires the
sealed two-root completion admission plus freshly verified processes/resources.
The old and new preparations share one command name and one ten-call authority.
"""
import argparse
import ast
import base64
import io
import json
import time
import zipfile
from pathlib import Path
from control import HERE, remote, save, sha

PRIOR = HERE / 'approved-offline-aggregate-preparation-01'
PREP = HERE / 'approved-offline-aggregate-preparation-02'
PACKAGE = PREP / 'package'
REMOTE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/evidence-discipline-offline-20261115-continuation'
OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/evidence-discipline-offline-20261115-continuation'
OLD_REMOTE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/evidence-discipline-offline-development-20261114-01'
OLD_OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/evidence-discipline-offline-development-20261114-01'
COMMAND_NAME = 'evidence-discipline-offline-development-20261114-01.json'
PRIOR_SHA = '95a94d00923da3115036cf766bc0859c1ab909dc35ca1617a5968899e0f6cd33'


def load(path):
    return json.loads(Path(path).read_bytes())


def sealed(path):
    records = load(path / 'seal.json')
    assert records and all(sha(path / n) == h for n, h in records.items())


def prepare():
    assert not PREP.exists(), 'Inspect the immutable existing preparation'
    original = PRIOR / 'package'
    assert sha(original / 'offline-manifest.json') == PRIOR_SHA
    manifest = load(original / 'offline-manifest.json')
    assert len(manifest['files']) == 85
    for name, digest in manifest['files'].items():
        assert sha(original / name) == digest
        if name.endswith('.py'):
            ast.parse((original / name).read_text('utf8'))
    # Preserve the first aggregate preparation. Correct only its stale location
    # descriptor in a new manifest; all85 actual payload files stay identical.
    for name in manifest['files']:
        target = PACKAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write((original / name).read_bytes())
    save(PACKAGE / 'offline-manifest.json', {**manifest, 'remote_package': REMOTE,
         'previous_aggregate_preparation_manifest_sha256': PRIOR_SHA,
         'location_descriptor_only_corrected_before_first_stage': True})
    assert all(sha(PACKAGE / n) == h for n, h in manifest['files'].items())
    boundary = load(PRIOR / 'CPU-logical-cover-checks.json')
    assert boundary['passed'] == 12 and boundary['manifest_sha256'] == PRIOR_SHA
    save(PREP / 'preparation.json', {'time': time.time(), 'prior_preparation': str(PRIOR),
         'prior_manifest_sha256': PRIOR_SHA,
         'manifest_sha256': sha(PACKAGE / 'offline-manifest.json'),
         'all85_payload_files_identical': True,
         'original_plan_worker_native_inputs_budget_suffix_unchanged': True,
         'only_remote_package_descriptor_changed': True,
         'prior_pure_cover_checks_reference': str(PRIOR / 'CPU-logical-cover-checks.json'),
         'prior_pure_cover_checks_sha256': sha(PRIOR / 'CPU-logical-cover-checks.json'),
         'new_model_GUI_calls': 0, 'stage_or_submission_executed': False})
    print(json.dumps({'preparation': str(PREP), 'files': 85,
                      'manifest_sha256': sha(PACKAGE / 'offline-manifest.json'),
                      'new_model_GUI_calls': 0}))


def stage():
    assert not (PREP / 'stage-receipt.json').exists(), 'Inspect the existing stage'
    manifest = load(PACKAGE / 'offline-manifest.json')
    assert manifest['remote_package'] == REMOTE and manifest['output'] == OUTPUT
    for name, digest in manifest['files'].items():
        assert sha(PACKAGE / name) == digest
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in list(manifest['files']) + ['offline-manifest.json']:
            z.writestr(name, (PACKAGE / name).read_bytes())
    code = ('ROOT=' + repr(REMOTE) + '\nOLD_OUTPUT=' + repr(OLD_OUTPUT)
            + '\nOLD_PACKAGE=' + repr(OLD_REMOTE) + '\nCOMMAND_NAME=' + repr(COMMAND_NAME)
            + '\nEXPECTED=' + repr(sha(PACKAGE / 'offline-manifest.json')) + '\n' + r'''
import ast,base64,hashlib,io,json,os,sys,zipfile
from pathlib import Path
assert os.getuid()==1033
assert not Path(OLD_OUTPUT).exists()and not(Path(OLD_PACKAGE)/'previous-GUI-admission.json').exists()
command_dir=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/commands')
assert not list(command_dir.glob(Path(COMMAND_NAME).stem+'*')),'The single shared authorization command already exists'
r=Path(ROOT);r.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for name in z.namelist():
  target=r/name;assert target.resolve().is_relative_to(r.resolve())
  target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb')as f:f.write(z.read(name))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(r/'offline-manifest.json')==EXPECTED
m=json.loads((r/'offline-manifest.json').read_bytes())
assert m['remote_package']==str(r)
for name,h in m['files'].items():
 assert sha(r/name)==h,name
 if name.endswith('.py'):ast.parse((r/name).read_text())
sys.path.insert(0,str(r));import offline_guard as g
g.verify_package()
assert 'torch'not in sys.modules and not Path(m['output']).exists()
assert not(r/'previous-GUI-admission.json').exists()
print(json.dumps({'time':__import__('time').time(),'remote_package':str(r),'files':len(m['files']),
 'manifest_sha256':EXPECTED,'torch_imported':False,'new_model_GPU_GUI_calls':0,'worker_submitted':False,
 'old_preparation_not_submitted':True,'same_once_only_authorization_command':COMMAND_NAME}))
''')
    raw, op = remote('3090', code, 'stage-approved10-aggregate-without-model-submit',
                     private_prefix='PAYLOAD=' + repr(base64.b64encode(payload.getvalue()).decode()) + '\n')
    result = json.loads(raw)
    save(PREP / 'stage-receipt.json', {'result': result, 'operation': str(op)})
    print(json.dumps(result))


def submit():
    assert (PREP / 'stage-receipt.json').exists()
    assert not (PREP / 'submission.json').exists(), 'Inspect existing submission; do not resubmit'
    old_preparation = HERE.parent / 'flash-ample-memory-gui-20261114-linked11/evidence-discipline-offline-preparation-01'
    assert not (old_preparation / 'submission.json').exists()
    pointer = load(HERE / 'aggregate-completion-current.json')
    admission_root = Path(pointer['root']).resolve()
    assert admission_root.parent == HERE
    sealed(admission_root)
    assert sha(admission_root / 'seal.json') == pointer['seal_sha256']
    admission = load(admission_root / 'admission.json')
    assert len(admission['terminals']) == 29 and len(admission['preserved_technical_attempts']) == 1
    # Recheck both complete GUI roots and actual process exits immediately
    # before submission. The admission already freshly audited all30 seals/chains.
    code = 'ADMISSION=' + repr(admission) + '\n' + r'''
import hashlib,json,os,time
from pathlib import Path
assert os.getuid()==1015
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid));s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
base=Path('/data/researcher/jev-defense-four-gpu-20261106');processes=[]
for label,name in [('parent','flash-ample-memory-gui-20261114-linked11'),('continuation','flash-resource-continuation-20261115-linked12')]:
 root=base/name;status=json.loads((root/'batch/status.json').read_bytes())
 assert status['phase']==('technical_failure'if label=='parent'else'completed')
 assert status['completed']==(16 if label=='parent'else 13)
 assert status['processed']==(17 if label=='parent'else 13)
 assert json.loads((root/'control/exit.json').read_bytes())['child_exit']==0
 for filename in ['process.json','runner-process.json']:
  saved=json.loads((root/'control'/filename).read_bytes());proc=Path('/proc',str(saved['pid']));actual=identity(saved['pid'])if proc.exists()else None
  same=actual is not None and actual['state']not in ['Z','X']and all(actual[k]==saved[k]for k in ['uid','command','start_ticks'])
  assert not same,'GUI remains live';processes.append({'saved':saved,'actual':actual,'same_live_process':False})
 rows=ADMISSION[label+'_terminals']
 assert len(rows)==(17 if label=='parent'else 13)
 for row in rows:
  t=Path(row['terminal']);assert t.resolve().is_relative_to(root.resolve())
  assert sha(t)==row['terminal_sha256']and sha(t.parent/'seal.json')==row['seal_sha256']
print(json.dumps({'time':time.time(),'actual_GUI_processes_exited':processes,'all30_terminal_and_seal_identities_unchanged':True,'new_model_GPU_GUI_calls':0}))
'''
    raw, gui_op = remote('4090', code, 'pre-offline-actual-both-GUI-exits-recheck')
    gui = json.loads(raw)
    code = ('ROOT=' + repr(REMOTE) + '\nEXPECTED=' + repr(sha(PACKAGE / 'offline-manifest.json'))
            + '\nADMISSION=' + repr(admission) + '\nOLD_PACKAGE=' + repr(OLD_REMOTE)
            + '\nOLD_OUTPUT=' + repr(OLD_OUTPUT) + '\nCOMMAND_NAME=' + repr(COMMAND_NAME) + '\n' + r'''
import json,os,sys,time
from pathlib import Path
assert os.getuid()==1033
p=Path(ROOT);sys.path.insert(0,str(p));import offline_guard as g
assert g.sha(p/'offline-manifest.json')==EXPECTED
m,plan=g.verify_package();assert m['remote_package']==str(p)
assert not Path(OLD_OUTPUT).exists()and not(Path(OLD_PACKAGE)/'previous-GUI-admission.json').exists()
expected=[v['run_id']for v in g.load(p/'native/plan.json')['queue']]
g.validate_completion(g.load(g.PREVIOUS_OUT/'primary/status.json'),g.load(g.PREVIOUS_OUT/'primary/terminal.json'),g.load(g.PREVIOUS_OUT/'exit.json'),ADMISSION,expected)
processes=g.previous_models_exited()
lease=g.load(g.LEASE);assert g.sha(g.LEASE)=='8f5da746fbb45c587d23a0073f8dc62dcd9510b321b4cef0995c09aa8c92a89a'
holder=lease['holder'];actual=g.identity(holder['pid'])
assert actual['state']not in ['Z','X']and all(actual[k]==holder[k]for k in ['uid','command','start_ticks'])
for row in lease['lock_records']:
 proc=Path('/proc',str(holder['pid']));fd=proc/'fd'/str(row['fd'])
 assert fd.stat().st_ino==row['inode']and os.readlink(fd)==row['path']and 'WRITE '+str(holder['pid'])in(proc/'fdinfo'/str(row['fd'])).read_text()
previous=g.load(g.PREVIOUS_OUT/'expanded-lease.json');uuids={row['index']:row['uuid']for row in previous['gpu']}
for row in lease['gpu']:assert uuids[row['index']]==row['uuid']
snapshot=g.gpu_snapshot();g.validate_gpu(snapshot,uuids)
assert not Path(m['output']).exists()
stat=os.statvfs(p);assert stat.f_bavail*stat.f_frsize>64*1024**3
commands=g.LEASE.parent/'commands'
assert not list(commands.glob(Path(COMMAND_NAME).stem+'*')),'Single ten-call authority already submitted'
assert all(path.with_suffix('.claimed').exists()for path in commands.glob('*.json'))
admissionfile=p/'previous-GUI-admission.json';g.save(admissionfile,ADMISSION)
command=commands/COMMAND_NAME
g.save(command,{'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',str(p/'offline_launcher.py'),g.sha(admissionfile)],'script_sha256':g.sha(p/'offline_launcher.py')})
print(json.dumps({'command':str(command),'command_sha256':g.sha(command),'manifest_sha256':EXPECTED,
 'admission_sha256':g.sha(admissionfile),'previous_processes_actually_exited':processes,
 'fresh_exclusive_GPU_snapshot':snapshot,'once_only':True,'maximum_new_primary_calls':10,
 'new_GUI_Flash_scorer_calls':0,'time':time.time(),'same_authorization_not_a_second_budget':True}))
''')
    raw, op = remote('3090', code, 'submit-single-authorized10-only-after-actual-all29-exits')
    result = json.loads(raw)
    save(PREP / 'submission.json', {'result': result, 'operation': str(op),
         'actual_GUI_recheck': gui, 'GUI_operation': str(gui_op),
         'aggregate_admission': str(admission_root), 'source_sha256': sha(Path(__file__))})
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'stage', 'submit'])
    args = parser.parse_args()
    {'prepare': prepare, 'stage': stage, 'submit': submit}[args.action]()
