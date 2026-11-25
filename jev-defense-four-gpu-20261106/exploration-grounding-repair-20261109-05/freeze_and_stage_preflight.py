"""Freeze a new finite control package; staging does not submit or allocate GPUs."""
import argparse
import ast
import base64
import io
import json
from pathlib import Path
import shutil
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
GUI = BASE / 'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0, str(GUI))
from remote_control import remote, save, sha

NAME = 'source-bound-controls-20261109-08'
TARGET = BASE / NAME
REMOTE_PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + NAME
REMOTE_OUTPUT = '/home/researcher/jev-defense-four-gpu-20261106/' + NAME


def freeze():
    TARGET.mkdir(exist_ok=False)
    package = TARGET / 'runtime-package'
    package.mkdir()
    source = BASE / 'stateless-auxiliary-20261109-07' / 'integrated-runtime-linked03'
    source_seal = json.loads((source / 'integrated-source-seal.json').read_bytes())
    for name, expected in source_seal.items():
        assert sha(source / name) == expected, name
    closure = HERE / 'source-controls-integrity-closure-01.json'
    controls = HERE / 'source-controls-01'
    binding = json.loads(closure.read_bytes())
    for name, expected in binding['files'].items():
        assert sha(controls / name) == expected, name
    for name in ['release', 'grammar-vendor']:
        shutil.copytree(source / name, package / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    selected = ['model_runtime.py', 'resource_gate.py', 'preflight_support.py',
                'aux_identity_support.py', 'four_gpu_contract.py', 'primary-reference.json',
                'auxiliary-identity-reference.json', 'bounded_auxiliary.py', 'bounded_schema.py',
                'native_format_bridge.py', 'auxiliary_grammar_import.py',
                'auxiliary-grammar-identity.json', 'stateless_boundary.py']
    for name in selected:
        shutil.copyfile(source / name, package / name)
    for name in ['controls_worker.py', 'exploratory_action_scope.py']:
        shutil.copyfile(HERE / name, package / name)
    native_parser = BASE / 'repair-evidence-20261109-01' / 'controls-package' / 'native-parser-source.py'
    shutil.copyfile(native_parser, package / 'native-parser-source.py')
    launcher = (GUI / 'runtime-package' / 'launch_gui_service_once.py').read_text(encoding='utf8')
    launcher = launcher.replace('full-gui-bounded-evidence-20261109-03', NAME)
    launcher = launcher.replace('launch_gui_service_once.py', 'launch_controls_once.py')
    launcher = launcher.replace('gpu_server.py', 'controls_worker.py')
    launcher = launcher.replace('GUI_is_external_and_bound_to_plan', 'no_GUI_in_static_control_batch')
    (package / 'launch_controls_once.py').write_text(launcher, encoding='utf8', newline='\n')
    sys.path.insert(0, str(source / 'release'))
    import image_evidence as contract
    inputs = package / 'control-inputs'
    inputs.mkdir()
    auxiliary = []
    for name, scene in [('U01', 'catalog'), ('U02', 'catalog'), ('U03', 'footer')]:
        original = controls / 'public' / 'images' / (scene + '.png')
        request = contract.build_image_only_request(original.read_bytes(), 'Qwen/Qwen3.5-9B',
                                                     'c202236235762e1c871ad0ccb60c8ee5ba337b9a')
        save(inputs / (name + '.json'), request)
        auxiliary.append({'id': name, 'path': 'control-inputs/' + name + '.json',
                           'sha256': sha(inputs / (name + '.json')),
                           'same_image_repeated_by_predeclared_lifecycle_control': name == 'U02'})
    judges = []
    control_manifest = json.loads((controls / 'manifest.json').read_bytes())
    for row in control_manifest['controls']:
        original = controls / 'public' / row['file']
        frozen = json.loads(original.read_bytes())
        image_path = controls / 'public' / frozen['image']
        assert sha(image_path) == frozen['image_sha256']
        image_base64 = base64.b64encode(image_path.read_bytes()).decode()
        view = {
            'observation_id': 'new-constructed-' + row['id'],
            'messages': [{'role': 'user', 'content': [
                {'type': 'text', 'text': 'Task: ' + frozen['task']},
                {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + image_base64}}]}],
            'images': [{'raw_base64': image_base64, 'role': 'current'}],
            'recent_action': '', 'execution_feedback': '', 'observed_at': control_manifest['time'],
        }
        path = inputs / (row['id'] + '.json')
        save(path, {'id': row['id'], 'view': view, 'candidate': frozen['candidate'],
                    'public_source_file_sha256': sha(original)})
        judges.append({'id': row['id'], 'path': path.relative_to(package).as_posix(), 'sha256': sha(path)})
    save(package / 'controls-plan.json', {
        'schema': 'new-source-bound-exploration-and-stateless-controls-v1',
        'auxiliary': auxiliary, 'judges': judges,
        'conditions': control_manifest['prompt_conditions'],
        'limits': {'auxiliary': 3, 'judge': 32, 'actor': 0, 'GUI': 0, 'scorer': 0,
                   'paid_API': 0, 'format_retries_per_judge_control': 1},
        'each_judge_case_condition_once_only': True,
        'auxiliary_repeated_image_is_predeclared_independence_probe_not_semantic_retry': True,
        'no_semantic_resampling_or_retry_completed_case': True,
        'model_parameters_precision_native_prompts_and_strict_validator_retained': True,
        'complete_current_source_images_and_all_existing_history_kept': True,
        'these_constructed_views_have_no_prior_actor_history_not_a_truncation': True,
        'not_full_GUI_or_efficacy': True,
        'tradeoffs': [control_manifest['tradeoff'],
                     'Removing exact-image reply reuse adds auxiliary calls and latency within the original60cap.',
                     'Schema decoding is auxiliary-only, changes its token choices and does not certify image truth.',
                     'Strict original final string-length checks can still reject an output admitted by the byte grammar.'],
    })
    admission = BASE / 'stateless-auxiliary-20261109-07' / 'integrated-CPU-admission-1794208461068876000' / 'original' / 'result' / 'receipt.json'
    assert json.loads(admission.read_bytes())['passed'] is True
    lease = BASE / 'resource-attempt-20261106-01' / 'lease.json'
    expected = json.loads(lease.read_bytes())['holder']
    for path in package.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf8'), filename=str(path))
    assert not any('PRIVATE' in p.name or p.name == 'private.token' for p in package.rglob('*'))
    manifest = {
        'schema': 'new-finite-source-bound-preflight-v1',
        'authorized_finite_joint_development': True,
        'authorization': 'User active sustained defense objective and explicit independent one-image auxiliary requirement.',
        'expected_holder': expected, 'lease_sha256': sha(lease), 'output': REMOTE_OUTPUT,
        'no_old_terminal_resume': True,
        'source_controls_closure_sha256': sha(closure),
        'source_first_private_expectations_sha256': control_manifest['private_review_sha256'],
        'PRIVATE_expectations_excluded_from_worker': True,
        'new_integrated_CPU_mock_admission_sha256': sha(admission),
        'actual_GPU_cache_release_not_previously_proven': True,
        'original_native_parser_source_sha256': sha(native_parser),
        'worker_source_sha256': sha(package / 'controls_worker.py'),
        'files': {p.relative_to(package).as_posix(): sha(p) for p in package.rglob('*') if p.is_file()},
    }
    save(package / 'manifest.json', manifest)
    save(TARGET / 'preparation.json', {
        'time': time.time(), 'manifest_sha256': sha(package / 'manifest.json'),
        'local_package': str(package), 'remote_package': REMOTE_PACKAGE, 'remote_output': REMOTE_OUTPUT,
        'stage_only_no_submission': True, 'launch_ready': False,
        'must_first_close_preserve_and_audit_current_four_GUI_tracks': True,
        'limits': json.loads((package / 'controls-plan.json').read_bytes())['limits'],
        'new_actual_model_GUI_calls': 0, 'efficacy_proven': False})
    print(json.dumps({'frozen': str(package), 'manifest_sha256': sha(package / 'manifest.json'),
                      'source_bound_judge_pairs': 8, 'auxiliary_independence_probes': 3,
                      'GPU_launch_not_submitted': True}))


def stage():
    package = TARGET / 'runtime-package'
    manifest_sha = sha(package / 'manifest.json')
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in package.rglob('*'):
            if path.is_file():
                archive.write(path, path.relative_to(package).as_posix())
    code = 'TARGET=' + repr(REMOTE_PACKAGE) + '\nEXPECTED=' + repr(manifest_sha) + '\n' + r'''
from pathlib import Path
import ast,base64,hashlib,io,json,os,zipfile
root=Path(TARGET);root.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(BUNDLE)))as archive:
 for name in archive.namelist():assert(root/name).resolve().is_relative_to(root.resolve())
 archive.extractall(root)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'manifest.json')==EXPECTED
manifest=json.loads((root/'manifest.json').read_bytes())
for name,expected in manifest['files'].items():assert sha(root/name)==expected,name
for path in root.rglob('*.py'):ast.parse(path.read_text(encoding='utf8'),filename=str(path))
assert not any('PRIVATE'in p.name or p.name=='private.token'for p in root.rglob('*'))
print(json.dumps({'staged':str(root),'UID':os.getuid(),'files_SHA_verified':len(manifest['files']),
 'manifest_sha256':EXPECTED,'launch_submitted':False,'new_model_GPU_GUI_calls':0}))
'''
    text, operation = remote('3090', code, 'stage-new-source-bound-stateless-and-click-preflight',
                              timeout=80, private_prefix='BUNDLE=' + repr(base64.b64encode(bundle.getvalue()).decode()) + '\n')
    save(TARGET / 'staging.json', {'result': json.loads(text), 'operation': str(operation)})
    print(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'stage'])
    {'freeze': freeze, 'stage': stage}[parser.parse_args().action]()
