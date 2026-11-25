"""Create one linked, zero-call technical repair; preserve the approved inputs."""
import argparse
import ast
import base64
import io
import json
import time
import zipfile
from pathlib import Path

from control import HERE, remote, save, sha
from offline_followup_control import PREP as PRIOR, REMOTE as OLD_REMOTE, OUTPUT as OLD_OUTPUT

PREP = HERE / 'approved-offline-receipt-repair-01'
PACKAGE = PREP / 'package'
REMOTE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/evidence-discipline-offline-20261115-receipt-repair01'
OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/evidence-discipline-offline-20261115-receipt-repair01'
AUDIT = HERE / 'offline10-postexit-audit-1794681468201898100'

HELPER = r'''"""Bind the exact approved wrapper receipt to its sealed native CPU result."""
import hashlib
import json
from pathlib import Path

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def load(path):
    return json.loads(Path(path).read_bytes())

def verify_cpu_receipt(package, source, frozen, manifest):
    package, source = Path(package), Path(source)
    wrapper_path = package / 'CPU-receipts' / ('case-%02d.json' % frozen['case'])
    require(digest(wrapper_path) == frozen['native_CPU_input_receipt_sha256'], 'Approved wrapper receipt changed')
    wrapper = load(wrapper_path)
    require(wrapper['remote_case'] == str(source), 'Approved native CPU source path changed')
    require(digest(source / 'seal.json') == wrapper['remote_seal_sha256'] == manifest['CPU_case_seals'][str(frozen['case'])], 'Original native CPU seal changed')
    seal = load(source / 'seal.json')
    require('result.json' in seal and 'proposed-full-body.json' in seal, 'Incomplete original native CPU seal')
    for name, expected in seal.items():
        require(digest(source / name) == expected, 'Original native CPU member changed: ' + name)
    result = load(source / 'result.json')
    require(result == wrapper['result'], 'Sealed native result differs from approved wrapper payload')
    require(result['source_body_sha256'] == frozen['original_body_sha256'], 'Original full body identity changed')
    require(digest(source / 'proposed-full-body.json') == frozen['proposed_full_body_sha256'] == result['proposed_full_body_sha256'], 'Approved proposed full body changed')
    require(result['full_input_token_delta'] == 292 and result['full_original_PNGs_and_non_system_history_preserved'] is True, 'Original input conditions changed')
    return result

def verify_zero_call_parent(package):
    package = Path(package)
    contract = load(package / 'linked-zero-call-failure.json')
    old = Path(contract['output'])
    require(digest(old / 'postexit-seal.json') == contract['postexit_seal_sha256'], 'Preserved zero-call attempt seal changed')
    seal = load(old / 'postexit-seal.json')
    require({str(f.relative_to(old)) for f in old.rglob('*') if f.is_file() and f.name != 'postexit-seal.json'} == set(seal), 'Preserved zero-call attempt file set changed')
    for name, expected in seal.items():
        require(digest(old / name) == expected, 'Preserved zero-call attempt member changed: ' + name)
    terminal, exit_record = load(old / 'worker/terminal.json'), load(old / 'exit.json')
    require(terminal['status'] == 'preserved_failure' and terminal['attempted_calls'] == 0 and terminal['completed_reply_cases'] == [], 'A previous approved model call has already been spent')
    require(exit_record['exit_code'] == exit_record['child_exit'] == 1, 'Unexpected prior technical terminal')
    require('Frozen CPU receipt changed' in load(old / 'worker/failure.json')['error'], 'Different parent failure')
    from offline_guard import identity
    for name in ['launcher-process.json', 'worker/process.json']:
        saved = load(old / name)
        try:
            actual = identity(saved['pid'])
        except FileNotFoundError:
            actual = None
        same = actual is not None and actual['state'] not in ['Z', 'X'] and all(actual[k] == saved[k] for k in ['pid', 'uid', 'command', 'start_ticks'])
        require(not same, 'Prior zero-call worker/launcher is still live')
    return {'prior_attempted_calls': 0, 'remaining_shared_maximum_calls': 10, 'old_postexit_seal_sha256': contract['postexit_seal_sha256']}
'''


def build():
    assert not PREP.exists(), 'Inspect the immutable existing repair preparation'
    audit_seal = json.loads((AUDIT / 'seal.json').read_bytes())
    assert all(sha(AUDIT / n) == h for n, h in audit_seal.items())
    admission = json.loads((AUDIT / 'admission.json').read_bytes())['result']
    summary = json.loads((AUDIT / 'summary.json').read_bytes())
    assert summary['actual_existing_worker_launcher_exits_verified'] and summary['attempted_calls'] == 0
    original = PRIOR / 'package'
    old_manifest = json.loads((original / 'offline-manifest.json').read_bytes())
    assert sha(original / 'offline-manifest.json') == '7061f192dccda4ac304fa79126760f3247145faac1db22538750411d376cb81b'
    PACKAGE.mkdir(parents=True)
    for name, expected in old_manifest['files'].items():
        assert sha(original / name) == expected
        target = PACKAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write((original / name).read_bytes())
    plan = json.loads((PACKAGE / 'development-plan.json').read_bytes())
    assert sha(PACKAGE / 'development-plan.json') == '98d7880006a38f06115a62c10a64ffeca35d351f4a0683b92f37dfb081ceea9a'
    cpu = HERE.parent / 'flash-ample-memory-gui-20261114-linked11/evidence-discipline-native-CPU-1794656543839272000'
    assert sha(cpu / 'seal.json') == '2c9ffb55d8cd7a8f83ccc5ae92f184fa84f258b4f5f9eeaf4d881d9f584853e1'
    assert all(sha(cpu / n) == h for n, h in json.loads((cpu / 'seal.json').read_bytes()).items())
    for row in plan['inputs']:
        name = 'case-%02d.json' % row['case']
        assert sha(cpu / name) == row['native_CPU_input_receipt_sha256']
        target = PACKAGE / 'CPU-receipts' / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((cpu / name).read_bytes())
    (PACKAGE / 'receipt_binding.py').write_text(HELPER, encoding='utf8')
    save(PACKAGE / 'linked-zero-call-failure.json', {
        'output': OLD_OUTPUT, 'package': OLD_REMOTE,
        'postexit_seal_sha256': admission['output_postexit_seal_sha256'],
        'local_fresh_postexit_audit': str(AUDIT), 'audit_seal_sha256': sha(AUDIT / 'seal.json'),
        'old_model_calls': 0, 'shared_original_maximum_new_model_calls': 10,
        'old_failure_and_eight_GPU_reserved_seconds_retained': True,
        'metadata_reader_only_repair_not_new_experimental_condition': True})
    worker = (PACKAGE / 'offline_worker.py').read_text('utf8')
    before = """            require(sha(source / 'result.json') == frozen['native_CPU_input_receipt_sha256'], 'Frozen CPU receipt changed')
            cpu = load(source / 'result.json')"""
    after = "            cpu = verify_cpu_receipt(P, source, frozen, manifest)"
    assert worker.count(before) == 1
    worker = worker.replace(before, after)
    boundary = "        import primary_server\n"
    assert worker.count(boundary) == 1
    worker = worker.replace(boundary, "        for frozen in plan['inputs']:\n            verify_cpu_receipt(P, Path(frozen['proposed_full_body']).parent, frozen, manifest)\n" + boundary)
    worker = 'from receipt_binding import verify_cpu_receipt\n' + worker
    original_ast = ast.parse((original / 'offline_worker.py').read_text('utf8'))
    changed_ast = ast.parse(worker)
    for name in ['checked_generate', 'install_previous_memory_implementation']:
        assert ast.dump(next(x for x in original_ast.body if isinstance(x, ast.FunctionDef) and x.name == name)) == ast.dump(next(x for x in changed_ast.body if isinstance(x, ast.FunctionDef) and x.name == name))
    (PACKAGE / 'offline_worker.py').write_text(worker, encoding='utf8')
    launcher = (PACKAGE / 'offline_launcher.py').read_text('utf8')
    before = '    manifest, plan = guard.verify_package()\n'
    assert launcher.count(before) == 1
    launcher = launcher.replace(before, before + '    verify_zero_call_parent(P)\n')
    launcher = 'from receipt_binding import verify_zero_call_parent\n' + launcher
    ast.parse(launcher)
    (PACKAGE / 'offline_launcher.py').write_text(launcher, encoding='utf8')
    files = {str(p.relative_to(PACKAGE)).replace('\\', '/'): sha(p) for p in PACKAGE.rglob('*') if p.is_file()}
    changed = [n for n, h in old_manifest['files'].items() if files[n] != h]
    assert changed == ['offline_worker.py', 'offline_launcher.py'] or set(changed) == {'offline_worker.py', 'offline_launcher.py'}
    assert all(files[n] == h for n, h in old_manifest['files'].items() if n.startswith('native/'))
    save(PACKAGE / 'offline-manifest.json', {**old_manifest, 'files': files,
        'version': 'approved-evidence-discipline-offline10-linked-receipt-repair01',
        'remote_package': REMOTE, 'output': OUTPUT,
        'prior_failed_manifest_sha256': sha(original / 'offline-manifest.json'),
        'linked_zero_call_failure_seal_sha256': admission['output_postexit_seal_sha256'],
        'same_plan_authorization_full_inputs_suffix_generation_and_budget': True,
        'created': time.time()})
    save(PREP / 'preparation.json', {'time': time.time(), 'old_manifest_sha256': sha(original / 'offline-manifest.json'),
        'new_manifest_sha256': sha(PACKAGE / 'offline-manifest.json'), 'changed_existing_files': changed,
        'all_native_sources_identical': True, 'generate_and_memory_implementation_AST_identical': True,
        'authorized_plan_and_suffix_unchanged': True, 'original_local_wrapper_receipts_staged_byte_identically': 10,
        'old_attempt_actual_model_calls': 0, 'shared_maximum_calls': 10,
        'condition_change': False, 'new_model_GPU_GUI_calls': 0, 'staged_or_submitted': False})
    save(PREP / 'seal.json', {'preparation.json': sha(PREP / 'preparation.json')})
    print(json.dumps({'preparation': str(PREP), 'manifest_sha256': sha(PACKAGE / 'offline-manifest.json'),
        'changed_existing_files': changed, 'new_model_GPU_GUI_calls': 0}))


def stage():
    assert not (PREP / 'stage-receipt.json').exists()
    manifest = json.loads((PACKAGE / 'offline-manifest.json').read_bytes())
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, expected in manifest['files'].items():
            assert sha(PACKAGE / name) == expected
            z.writestr(name, (PACKAGE / name).read_bytes())
        z.writestr('offline-manifest.json', (PACKAGE / 'offline-manifest.json').read_bytes())
    code = 'ROOT=' + repr(REMOTE) + '\nEXPECTED=' + repr(sha(PACKAGE / 'offline-manifest.json')) + '\n' + r'''
import ast,base64,hashlib,io,json,os,sys,time,zipfile
from pathlib import Path
assert os.getuid()==1033
p=Path(ROOT);p.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for name in z.namelist():
  target=p/name;assert target.resolve().is_relative_to(p.resolve());target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb')as f:f.write(z.read(name))
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
assert sha(p/'offline-manifest.json')==EXPECTED
manifest=json.loads((p/'offline-manifest.json').read_bytes())
for name,h in manifest['files'].items():
 assert sha(p/name)==h
 if name.endswith('.py'):ast.parse((p/name).read_text())
sys.path.insert(0,str(p));import offline_guard as guard
from receipt_binding import verify_cpu_receipt,verify_zero_call_parent
m,plan=guard.verify_package();parent=verify_zero_call_parent(p)
for frozen in plan['inputs']:verify_cpu_receipt(p,Path(frozen['proposed_full_body']).parent,frozen,m)
assert 'torch'not in sys.modules and not Path(m['output']).exists()
print(json.dumps({'time':time.time(),'manifest_sha256':EXPECTED,'files':len(m['files']),
 'all10_approved_wrapper_to_original_remote_result_bindings_passed':True,'parent':parent,
 'torch_imported':False,'new_model_GPU_GUI_calls':0,'worker_submitted':False}))
'''
    raw, op = remote('3090', code, 'stage-linked-zero-call-receipt-repair-no-model',
        private_prefix='PAYLOAD=' + repr(base64.b64encode(payload.getvalue()).decode()) + '\n')
    save(PREP / 'stage-receipt.json', {'result': json.loads(raw), 'operation': str(op)})
    print(raw)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['build', 'stage'])
    a = p.parse_args()
    {'build': build, 'stage': stage}[a.action]()
