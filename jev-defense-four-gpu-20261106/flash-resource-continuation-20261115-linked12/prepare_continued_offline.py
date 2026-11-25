"""Prepare equivalent all-29 admission for the already approved, unchanged offline10.

Only completion/resource provenance is adapted for two immutable GUI roots.
The original approved ten bodies, suffix, CPU receipts, worker and model code
are retained. This preparation cannot submit a command or make a model call.
"""
import ast
import hashlib
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'flash-ample-memory-gui-20261114-linked11'
PREP = HERE / 'approved-offline-aggregate-preparation-01'
PACKAGE = PREP / 'package'
REMOTE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/evidence-discipline-offline-20261115-continuation'
OUTPUT = '/data/researcher/jev-defense-four-gpu-20261106/evidence-discipline-offline-20261115-continuation'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, v):
    with p.open('x', encoding='utf8') as f:
        json.dump(v, f, ensure_ascii=False, indent=2)


def main():
    old = OLD / 'evidence-discipline-offline-preparation-01/package'
    old_manifest = json.loads((old / 'offline-manifest.json').read_bytes())
    assert sha(old / 'offline-manifest.json') == 'dd275e2ce505716b1cf20b98f0fb09ee866a24f9e96157f1f018292aa9fb5232'
    assert not (old.parent / 'submission.json').exists()
    assert not (PACKAGE / 'offline-manifest.json').exists()
    for name, h in old_manifest['files'].items():
        assert sha(old / name) == h, name
        if name == 'offline_guard.py':
            continue
        target = PACKAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write((old / name).read_bytes())
    guard = (old / 'offline_guard.py').read_text(encoding='utf8')
    tree = ast.parse(guard)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_completion')
    lines = guard.splitlines(keepends=True)
    replacement = ('def validate_completion(status, terminal, group_exit, admission, expected):\n'
                   '    from aggregate_completion import validate\n'
                   '    return validate(P, status, terminal, group_exit, admission, expected)\n')
    lines[function.lineno - 1:function.end_lineno] = [replacement]
    guard = ''.join(lines)
    before = "               PREVIOUS_PACKAGE / 'flash/service/process.json']"
    root = '/data/researcher/jev-defense-four-gpu-20261106/flash-resource-continuation-20261115-linked12'
    package = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-resource-continuation-20261115-linked12'
    after = "               PREVIOUS_PACKAGE / 'flash/service/process.json',\n" + \
            "               Path(" + repr(root + '/launcher-process.json') + "),\n" + \
            "               Path(" + repr(root + '/primary/process.json') + "),\n" + \
            "               Path(" + repr(package + '/flash/service/process.json') + ")]"
    assert guard.count(before) == 1
    guard = guard.replace(before, after)
    ast.parse(guard)
    with (PACKAGE / 'offline_guard.py').open('x', encoding='utf8', newline='\n') as f:
        f.write(guard)
    original = json.loads((HERE / 'package/parent-bindings.json').read_bytes())
    contract = json.loads((HERE / 'package/technical-continuation-contract.json').read_bytes())
    bindings = {'parent_package': original['package3090'], 'parent_output': original['output3090'],
                'parent_manifest_sha256': original['manifest_sha256'],
                'parent_postexit_seal_sha256': original['postexit_seal_sha256'],
                'continuation_output': root, 'continuation_package': package,
                'continuation_manifest_sha256': sha(HERE / 'package/manifest.json'),
                'contract': contract,
                'authorized_plan_sha256': '98d7880006a38f06115a62c10a64ffeca35d351f4a0683b92f37dfb081ceea9a',
                'old_offline_manifest_sha256': sha(old / 'offline-manifest.json'),
                'old_unsubmitted_offline_package_preserved': True}
    assert sha(PACKAGE / 'development-plan.json') == bindings['authorized_plan_sha256']
    save(PACKAGE / 'aggregate-bindings.json', bindings)
    files = {str(p.relative_to(PACKAGE)).replace('\\', '/'): sha(p) for p in PACKAGE.rglob('*') if p.is_file() and p.name != 'offline-manifest.json' and '__pycache__' not in p.parts}
    for name in files:
        if name.endswith('.py'):
            ast.parse((PACKAGE / name).read_text(encoding='utf8'))
    manifest = {**old_manifest, 'files': files, 'output': OUTPUT,
                'previous_prepared_manifest_sha256': sha(old / 'offline-manifest.json'),
                'completion_admission': 'exact original29 across parent16 and continuation13; failed partial remains technical',
                'aggregate_binding_sha256': sha(PACKAGE / 'aggregate-bindings.json')}
    save(PACKAGE / 'offline-manifest.json', manifest)
    unchanged = {n: sha(PACKAGE / n) for n in old_manifest['files'] if n != 'offline_guard.py'}
    assert all(h == old_manifest['files'][n] for n, h in unchanged.items())
    save(PREP / 'preparation.json', {'time': time.time(), 'prepared_only': True,
        'manifest_sha256': sha(PACKAGE / 'offline-manifest.json'), 'files': len(files),
        'unchanged_original_files': unchanged, 'original_approved_plan_unchanged': True,
        'ten_call_bodies_CPU_inputs_worker_generation_and_suffix_unchanged': True,
        'original_prepared_package_not_modified_or_submitted': True,
        'new_admission_requires_all29_logical_normal_terminals_and_all_process_exits': True,
        'failed_parent_not_relabelled': True, 'new_model_GUI_calls': 0,
        'staged_or_submitted': False, 'formal_changed_GUI_authorized': False})
    print(json.dumps({'preparation': str(PREP), 'files': len(files), 'manifest_sha256': sha(PACKAGE / 'offline-manifest.json'), 'unchanged_original_files': len(unchanged), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
