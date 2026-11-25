"""Prepare a locked, local remaining29 runtime template; never deploy or launch."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / 'remaining-full-history-gui-20261110-33/runtime-package'
PRIMARY = BASE / 'remaining29-primary-outcome-staging-20261110-35'
FINAL_NAMESPACE = 'remaining29-full-history-gui-20261110-37'
EXPECTED_MANIFEST = 'e64fc8e42a144cd1cc426942093a6edaf51204fba13918286c41e51f8d7b15ef'
GATE = 'from source_decision_gate import require_finalized\nrequire_finalized(__file__)\n'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def insert_gate(text):
    tree = ast.parse(text)
    assert isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant)
    lines = text.splitlines(keepends=True)
    end = tree.body[0].end_lineno
    value = ''.join(lines[:end]) + GATE + ''.join(lines[end:])
    assert value.replace(GATE, '', 1) == text
    return value


def replace_one(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def main():
    assert not (HERE / 'preparation-created.json').exists(), 'Already prepared'
    assert sha(OLD / 'manifest.json') == EXPECTED_MANIFEST
    old_manifest = read(OLD / 'manifest.json')
    for name, digest in old_manifest['files'].items():
        assert sha(OLD / name) == digest, name
    primary = read(PRIMARY / 'preparation-created.json')
    source = Path(primary['root'])
    assert sha(source / 'seal.json') == primary['seal_sha256']
    for name, digest in read(source / 'seal.json').items():
        assert sha(source / name) == digest, name
    pending = read(source / 'pending-condition.json')
    assert pending['answer_received'] is False and pending['deployed'] is False
    root = HERE / ('preparation-' + str(time.time_ns()))
    root.mkdir()
    for name in ['prepare_once.py', 'continuation_manifest.py', 'source_decision_gate.py', 'check_template.py']:
        shutil.copyfile(HERE / name, root / name)
    package = root / 'runtime-template'
    package.mkdir()
    # Copy exact source-manifest members only. Never copy old runtime logs,
    # claims, pycache, output files or its transport authorization token.
    for name in old_manifest['files']:
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / name, target)
    token = package / 'private.token'
    token.write_text(secrets.token_hex(32), encoding='ascii')
    assert sha(token) != old_manifest['auth_token_sha256']
    for name in ['continuation_manifest.py', 'source_decision_gate.py']:
        shutil.copyfile(HERE / name, package / name)
    ledger = read(source / 'terminal-exclusions.json')
    assert len(ledger) == 3
    (package / 'predecessor-terminals').mkdir()
    terminal_copies = []
    for row in ledger:
        target = package / row['copy']
        shutil.copyfile(source / row['copy'], target)
        assert sha(target) == row['sha256']
        # Semantic labels, rates and evaluation judgments stay outside runtime.
        terminal_copies.append({k: row[k] for k in ['run_id', 'copy', 'sha256']})
    shutil.copyfile(source / 'completed-request-exclusions.json',
                    package / 'completed-request-exclusions.json')
    remaining = read(source / 'remaining29-queue.json')
    save(package / 'continuation.json', {
        'schema': 'unchanged-original32-minus-three-terminal-remaining29-v1',
        'unchanged_full32_plan_sha256': remaining['unchanged_full32_plan_sha256'],
        'excluded_run_ids': remaining['excluded_run_ids'], 'terminal_copies': terminal_copies,
        'remaining_run_ids': [x['run_id'] for x in remaining['queue']],
        'remaining_tracks': 29, 'initial_transport_counts': {'actor': 0, 'judge': 0, 'evidence': 0},
        'completed_request_exclusions_sha256': sha(package / 'completed-request-exclusions.json'),
        'all_existing_terminal_tracks_and_requests_forbidden': True,
        'primary_preparation_seal_sha256': primary['seal_sha256'],
    })
    changes = {
        'continuation_manifest.py': 'Exactly29 never-started runs; verify three immutable terminal bytes and disallow362 prior request IDs',
        'admission.json': 'STAGING denial; no condition selected and no deployment authorized',
        'source_decision_gate.py': 'Every entry point refuses pending choice before model/browser/resource imports',
        'continuation.json': 'Source-only continuation bookkeeping; no semantic expected labels',
    }
    entrypoints = ['gpu_server.py', 'launch_gui_service_once.py', 'gui_outer.py', 'run_independent_gui.py']
    for name in entrypoints:
        text = (OLD / name).read_text(encoding='utf-8')
        if name == 'gpu_server.py':
            assert text.count('19141') == 2
            text = text.replace('19141', '19142')
        if name == 'launch_gui_service_once.py':
            text = replace_one(text, 'runtime-preparation/remaining-full-history-gui-20261110-33',
                               'runtime-preparation/' + FINAL_NAMESPACE)
            text = replace_one(text, '/data/researcher/jev-defense-four-gpu-20261106/remaining-full-history-gui-20261110-33',
                               '/data/researcher/jev-defense-four-gpu-20261106/' + FINAL_NAMESPACE)
        (package / name).write_text(insert_gate(text), encoding='utf-8', newline='\n')
        changes[name] = ('Pending-choice gate only' if name in ['gui_outer.py', 'run_independent_gui.py']
                         else 'Pending-choice gate plus prospective new namespace/port; no live reservation')
    # The original admission record is already preserved by the source manifest.
    # Only the copied mutable template is changed below.
    admission = {
        'admit_new_GUI_development': False, 'source_condition_decision_received': False,
        'source_condition_choice': None, 'staging_template_only': True,
        'scope': 'original32_minus_three_immutable_terminals_remaining29',
        'original_caps_images_full_main_history_and_native_actions_preserved': True,
        'pending_existing_user_question_no_duplicate': True,
        'primary_preparation': primary, 'formal_efficacy': False,
    }
    (package / 'admission.json').write_text(json.dumps(admission, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = copy.deepcopy(old_manifest)
    manifest.update(
        schema='STAGING-locked-original32-remaining29-runtime-template-v1',
        template_only=True, launch_ready=False, authorized_finite_joint_development=False,
        source_condition_choice=None, source_condition_decision_received=False,
        tracks=29, skipped_completed_terminal_tracks=3, total_original_tracks=32,
        outputs='/data/researcher/jev-defense-four-gpu-20261106/' + FINAL_NAMESPACE,
        GUI_output='/data/researcher/jev-defense-four-gpu-20261106/' + FINAL_NAMESPACE + '/batch',
        model_url='http://192.0.2.11:19142', planned_port_only_not_checked_or_reserved=True,
        original31_manifest_sha256=EXPECTED_MANIFEST,
        original32_full_plan_sha256=sha(package / 'plan.json'),
        continuation_sha256=sha(package / 'continuation.json'),
        auth_token_sha256=sha(token), worker_source_sha256=sha(package / 'gpu_server.py'),
        holder_identity_not_reverified_for_this_template=True,
        source_preparation=primary, new_model_GPU_GUI_scorer_paid_calls=0,
        original_Controller_and_all_forward_sources_unchanged=True,
        source_condition_tradeoffs=old_manifest['source_condition_tradeoffs'] +
        ' STAGING ONLY: all three existing terminal tracks are excluded; remaining29 retain original order/caps. '
        'Source-condition choice is pending. Port19142 and the new namespace are prospective only. '
        'No runtime permission, resource lease revalidation, GPU fit or efficacy is established.')
    manifest['files'] = {p.relative_to(package).as_posix(): sha(p)
                         for p in sorted(package.rglob('*'))
                         if p.is_file() and p.name not in ['manifest.json', 'private.token']}
    save(package / 'manifest.json', manifest)
    for path in package.rglob('*.py'):
        compile(path.read_text(encoding='utf-8'), str(path), 'exec')
    result = subprocess.run([sys.executable, '-B', str(HERE / 'check_template.py'), str(package)], capture_output=True)
    (root / 'CPU-checks.stdout.txt').write_bytes(result.stdout)
    (root / 'CPU-checks.stderr.txt').write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    checks = json.loads(result.stdout)
    assert checks['passed'] and checks['new_model_GPU_GUI_scorer_paid_calls'] == 0
    save(root / 'preparation.json', {
        'schema': 'locked-local-runtime-template-preparation-only-v1',
        'manifest_sha256': sha(package / 'manifest.json'), 'source_manifest_sha256': EXPECTED_MANIFEST,
        'changes': changes, 'CPU_check_groups': checks['groups'],
        'original_forward_Controller_prompts_history_images_actions_budgets_unchanged': True,
        'original_full32_plan_bytes_unchanged': True, 'all_three_terminals_excluded': True,
        'all_remaining29_start_zero': True, 'completed_request_IDs_disallowed': 362,
        'source_condition_not_selected_or_deployed': True, 'actual_runtime_launch_ready': False,
        'new_remote_files_resources_services_or_GPU_allocations': 0,
        'new_model_GPU_GUI_scorer_paid_calls': 0, 'efficacy_established': False,
        'old21_source_tests_or_completed_model_controls_rerun': False,
        'pending_existing_user_decision': True, 'goal': 'active',
    })
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p)
                              for p in sorted(root.rglob('*')) if p.is_file()})
    for name, digest in read(root / 'seal.json').items():
        assert sha(root / name) == digest
    pointer = {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
               'manifest_sha256': sha(package / 'manifest.json'),
               'preparation_sha256': sha(root / 'preparation.json'),
               'CPU_check_groups': len(checks['groups']),
               'source_condition_pending': True, 'launch_ready': False,
               'new_model_GPU_GUI_scorer_paid_calls': 0}
    save(HERE / 'preparation-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=True))


if __name__ == '__main__':
    main()
