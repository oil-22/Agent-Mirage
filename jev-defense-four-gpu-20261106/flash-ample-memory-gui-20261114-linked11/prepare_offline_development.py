"""Build/stage the approved post-GUI worker without loading weights or submitting it."""
import ast
import base64
import hashlib
import io
import json
import shutil
import time
import zipfile
from pathlib import Path

from control import HERE, R3090, OUT, remote, save, sha

PREP = HERE / 'evidence-discipline-offline-preparation-01'
PACKAGE = PREP / 'package'
REMOTE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/evidence-discipline-offline-development-20261114-01'
OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/evidence-discipline-offline-development-20261114-01'


def load(path):
    return json.loads(path.read_bytes())


def sealed(root):
    for name, expected in load(root / 'seal.json').items():
        assert sha(root / name) == expected


def build():
    authorization = load(HERE / 'evidence-discipline-development-authorization-current.json')
    decisionroot = Path(authorization['authorization'])
    sealed(decisionroot)
    assert authorization['authorized'] and sha(decisionroot / 'decision.json') == authorization['decision_sha256']
    decision = load(decisionroot / 'decision.json')
    planpath = Path(decision['plan'])
    assert sha(planpath) == decision['plan_sha256'] == '98d7880006a38f06115a62c10a64ffeca35d351f4a0683b92f37dfb081ceea9a'
    plan = load(planpath)
    cpu = Path(decision['native_CPU_freeze'])
    sealed(cpu)
    assert sha(cpu / 'seal.json') == decision['native_CPU_seal_sha256']
    original = HERE / 'package'
    assert sha(original / 'manifest.json') == '5e7e068ac14d75d668dfeca28ac7af61cf304e73187b21ed91169e9bb06c4762'
    old = load(original / 'manifest.json')
    assert len(old['files']) == 74
    for name, expected in old['files'].items():
        assert sha(original / name) == expected
    code = 'ROOT=' + repr(OUT) + '\n' + r'''
import hashlib,json
from pathlib import Path
p=Path(ROOT)/'capacity/lifetime-validation/result.json'
proof=json.loads(p.read_bytes())
assert proof['installed']and proof['all_full_vocab_logits_and_sequence_ids_bitwise_equal']
print(json.dumps({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'prior_proof':proof,'new_model_GPU_calls':0}))
'''
    raw, operation = remote('3090', code, 'offline-prepare-reference-existing-numerical-proof')
    prior = json.loads(raw)
    PACKAGE.mkdir(exist_ok=False)
    for name in list(old['files']) + ['manifest.json']:
        target = PACKAGE / 'native' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original / name, target)
        assert sha(target) == sha(original / name)
    # All native files, including the class and its recorder, are byte-identical.
    old_ast = ast.parse((original / 'primary_server.py').read_text('utf8'))
    new_ast = ast.parse((PACKAGE / 'native/primary_server.py').read_text('utf8'))
    old_class = next(n for n in old_ast.body if isinstance(n, ast.ClassDef) and n.name == 'NativeActor')
    new_class = next(n for n in new_ast.body if isinstance(n, ast.ClassDef) and n.name == 'NativeActor')
    assert ast.dump(old_class) == ast.dump(new_class)
    for path in (PREP / 'source').glob('*.py'):
        ast.parse(path.read_text('utf8'))
        shutil.copyfile(path, PACKAGE / path.name)
    for path, name in [(decisionroot / 'decision.json', 'authorization.json'),
                       (planpath, 'development-plan.json'),
                       (planpath.parent / 'proposed-system-suffix.txt', 'proposed-system-suffix.txt')]:
        shutil.copyfile(path, PACKAGE / name)
    cases = {str(row['case']): load(cpu / ('case-%02d.json' % row['case']))['remote_seal_sha256']
             for row in plan['inputs']}
    suffix = (PACKAGE / 'proposed-system-suffix.txt').read_text('utf8')
    normalized_sha = hashlib.sha256(suffix.encode()).hexdigest()
    assert all(load(cpu / ('case-%02d.json' % row['case']))['result']['suffix_sha256'] == normalized_sha for row in plan['inputs'])
    save(PACKAGE / 'preparation-binding.json', {
        'authorization_receipt': str(decisionroot), 'authorization_seal_sha256': sha(decisionroot / 'seal.json'),
        'original_manifest_sha256': sha(original / 'manifest.json'),
        'all74_native_sources_and_NativeActor_AST_identical': True,
        'native_CPU_seal_sha256': sha(cpu / 'seal.json'),
        'suffix_original_file_bytes_sha256': sha(PACKAGE / 'proposed-system-suffix.txt'),
        'suffix_native_CPU_universal_newline_text_sha256': normalized_sha,
        'newline_distinction_explicit_and_frozen_CPU_full_bodies_authoritative': True,
        'prior_numerical_proof_operation': str(operation),
        'new_model_GPU_GUI_calls': 0, 'time': time.time()})
    save(PACKAGE / 'prior-memory-proof.json', prior)
    files = {str(p.relative_to(PACKAGE)).replace('\\', '/'): sha(p) for p in PACKAGE.rglob('*') if p.is_file()}
    save(PACKAGE / 'offline-manifest.json', {
        'version': 'approved-evidence-discipline-offline10-v1', 'files': files,
        'remote_package': REMOTE, 'output': OUTPUT, 'CPU_case_seals': cases,
        'prior_memory_proof': prior['path'], 'prior_memory_proof_sha256': prior['sha256'],
        'max_new_primary_calls': 10, 'extra_capacity_generations': 0,
        'new_Flash_GUI_scorer_paid_calls': 0, 'must_finish_original29_first': True,
        'formal_changed_GUI_release': False, 'actually_reserved_GPUs_for_cost': 8,
        'worker_NOT_submitted': True, 'created': time.time()})
    save(PREP / 'build-receipt.json', {
        'manifest_sha256': sha(PACKAGE / 'offline-manifest.json'), 'files': len(files),
        'native_class_AST_and_all74_sources_equal': True,
        'new_model_GPU_GUI_calls': 0, 'worker_submitted': False, 'time': time.time()})
    print(json.dumps({'package': str(PACKAGE), 'manifest_sha256': sha(PACKAGE / 'offline-manifest.json'), 'new_model_GPU_calls': 0}))


def stage():
    assert not (PREP / 'stage-receipt.json').exists()
    manifest = load(PACKAGE / 'offline-manifest.json')
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in list(manifest['files']) + ['offline-manifest.json']:
            z.writestr(name, (PACKAGE / name).read_bytes())
    code = 'ROOT=' + repr(REMOTE) + '\nEXPECTED=' + repr(sha(PACKAGE / 'offline-manifest.json')) + '\n' + r'''
import ast,base64,hashlib,io,json,sys,zipfile
from pathlib import Path
r=Path(ROOT);r.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for name in z.namelist():
  target=r/name;assert target.resolve().is_relative_to(r.resolve())
  target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb')as f:f.write(z.read(name))
assert hashlib.sha256((r/'offline-manifest.json').read_bytes()).hexdigest()==EXPECTED
m=json.loads((r/'offline-manifest.json').read_bytes())
for name,h in m['files'].items():
 assert hashlib.sha256((r/name).read_bytes()).hexdigest()==h
 if name.endswith('.py'):ast.parse((r/name).read_text())
sys.path.insert(0,str(r));import offline_guard
offline_guard.verify_package()
assert 'torch'not in sys.modules and not Path(m['output']).exists()
assert not(r/'previous-GUI-admission.json').exists()
print(json.dumps({'remote_package':str(r),'files':len(m['files']),'manifest_sha256':EXPECTED,'torch_imported':False,'new_model_GPU_GUI_calls':0,'worker_submitted':False}))
'''
    raw, operation = remote('3090', code, 'stage-offline-approved10-without-submit',
                            private_prefix='PAYLOAD=' + repr(base64.b64encode(payload.getvalue()).decode()) + '\n')
    result = json.loads(raw)
    save(PREP / 'stage-receipt.json', {'result': result, 'operation': str(operation)})
    print(json.dumps(result))


if __name__ == '__main__':
    import sys
    {'build': build, 'stage': stage}[sys.argv[1]]()
