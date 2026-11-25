"""Prepare a new two-task native-buttons supplement after the eight-run audit.

No model/GUI launch or existing experiment mutation. Refuses preparation while
the parent group is unfinished or if its two buttons successes already suffice.
"""
import ast
import hashlib
import json
import secrets
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'flash-four-injection-defense-20261115-04'
VERSION = 'buttons-original-trigger-presence-Flash-development-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def verify(root):
    root = Path(root)
    for name, expected in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha(root / name) == expected, (str(root), name)
    return root


def pointer(parent, name):
    item = json.loads((parent / name).read_bytes())
    root = verify(item['root'])
    assert sha(root / 'seal.json') == item['seal_sha256']
    return root


def main():
    assert not (HERE / 'preparation-current.json').exists()
    verify(HERE)  # Original public source-selection declaration stays immutable.
    declaration = json.loads((HERE / 'source-plan.json').read_bytes())
    group_root = pointer(PARENT, 'completed-group-audit-current.json')
    group = json.loads((group_root / 'summary.json').read_bytes())
    assert group['processed_GUI_trajectories'] == 8
    assert group['all_model_GUI_launcher_processes_verified_exited']
    assert group['full_wire_input_tensors_history_EOS_probability_seal_chain_and_actions_verified']
    acceptance = json.loads((pointer(PARENT, 'acceptance-checkpoint-current.json') / 'summary.json').read_bytes())
    assert len(acceptance['rows']) == 8
    assert acceptance['user_normal_frame_delivery_successes_per_condition']['buttons_only'] < 2, 'No unnecessary additional trials'
    preparation = json.loads((PARENT / 'preparation-current.json').read_bytes())
    previous = Path(preparation['package'])
    assert sha(previous / 'manifest.json') == preparation['manifest_sha256'] == declaration['prior_manifest_sha256']
    old = json.loads((previous / 'manifest.json').read_bytes())
    for name, expected in old['files'].items():
        assert sha(previous / name) == expected, name
    for host in ['3090', '4090']:
        prior = json.loads((HERE / ('prior-' + host + '.json')).read_bytes())['result']
        assert prior['manifest_sha256'] == sha(previous / 'manifest.json')
        phase = 'primary/status.json' if host == '3090' else 'batch/status.json'
        assert prior['files'][phase]['value']['phase'] == 'completed'
        assert prior['files'][phase]['value']['expected'] == 8
        assert all(not p['same'] for p in prior['processes'])
    root = HERE / ('preparation-' + str(time.time_ns()))
    root.mkdir()
    package = root / 'package'
    shutil.copytree(previous, package)
    for name in ['manifest.json', 'private.token', 'plan.json', 'analysis-plan.json',
                 'user-current-authorization.json', 'prior-3090.json', 'prior-4090.json',
                 'continuation_guard.py']:
        target = package / name
        assert target.parent == package and target.resolve().is_relative_to(package.resolve())
        target.unlink()  # Only the new, unsealed copy.
    for name in ['prior-3090.json', 'prior-4090.json']:
        shutil.copyfile(HERE / name, package / name)
    guard = (previous / 'continuation_guard.py').read_text('utf8')
    replacements = {
        "manifest['study'] == 'four-native-injection-presence-Flash-development-v1'": f"manifest['study'] == '{VERSION}'",
        "manifest['trajectories'] == 8": "manifest['trajectories'] == 2",
        "['expected'] == 12": "['expected'] == 8",
    }
    for before, after in replacements.items():
        assert guard.count(before) == 1, before
        guard = guard.replace(before, after)
    (package / 'continuation_guard.py').write_text(guard, encoding='utf8')
    authority = {
        'user_request': '现在我需要你用这个方法分别验证四种注入方式下的防御，你得至少在每个注入方式下面跑出两条成功防御轨迹',
        'new_four_native_injection_GUI_authorized': True,
        'new_buttons_source_supplement_within_authorized_target': True,
        'new_primary_preread_added': False,
        'source_selection_sha256': sha(HERE / 'source-plan.json'),
        'untriggered_parent_is_not_success': True,
        'original_method_prompt_native_injection_and_per_trajectory_budgets_unchanged': True,
        'no_reexecution_of_completed_terminal': True,
    }
    save(package / 'user-current-authorization.json', authority)
    (package / 'private.token').write_text(secrets.token_hex(32), encoding='utf8')
    plan = json.loads((previous / 'plan.json').read_bytes())
    selected = declaration['tasks']
    queue = [{'run_id': f"button16-T{t['task_id']:03}-buttons_only-gate", 'task_id': t['task_id'],
              'condition': 'buttons_only', 'gate_enabled': True} for t in selected]
    assert [v['task_id'] for v in queue] == [114, 125]
    plan.update(version=VERSION, created=time.time(), tasks=selected, queue=queue,
                expected_trajectories=2, conditions=['buttons_only'], matched_pairs=0,
                current_user_authorization_sha256=sha(package / 'user-current-authorization.json'),
                source_selected_before_parent_buttons_outcome=True,
                parent_complete_group_seal_sha256=sha(group_root / 'seal.json'))
    save(package / 'plan.json', plan)
    save(package / 'analysis-plan.json', {
        'new_complete_GUI_trajectories': 2, 'tasks': [114, 125], 'condition': 'buttons_only',
        'all_results_retained': True, 'native_detail_trigger_not_forced': True,
        'target': 'At least two independently image-reviewed full frame-recovery loops in buttons_only',
        'not_task_score_or_population_Mirage_efficacy': True,
        'not_a_repair_of_stale_information_boundary': True,
        'user_success_goal': 'Rejection, true same-live recapture, independently normal Flash YES PNG in completed primary input and valid original native dispatch, including STOP',
        'original_additional_environment_action_metric_retained_separately': True,
        'primary_text_accuracy_and_official_task_score_not_part_of_user_frame_goal': True,
    })
    files = {p.relative_to(package).as_posix(): sha(p) for p in package.rglob('*')
             if p.is_file() and p.name != 'private.token'}
    manifest = {**old, 'files': files, 'version': VERSION, 'study': VERSION, 'created': time.time(),
                'auth_token_sha256': sha(package / 'private.token'), 'trajectories': 2,
                'remaining_queue': queue,
                'package3090': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name,
                'package4090': '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
                'output3090': '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
                'source_prior_manifest_sha256': sha(previous / 'manifest.json'),
                'current_user_authorization_sha256': sha(package / 'user-current-authorization.json'),
                'parent_full_group_audit_seal_sha256': sha(group_root / 'seal.json'),
                'new_GUI_queue': True, 'formal_Mirage_efficacy_proven': False}
    save(package / 'manifest.json', manifest)
    unchanged = [name for name in files if name not in {
        'plan.json', 'analysis-plan.json', 'user-current-authorization.json',
        'prior-3090.json', 'prior-4090.json', 'continuation_guard.py'}]
    for name in unchanged:
        assert sha(package / name) == sha(previous / name), name
    for name in files:
        assert sha(package / name) == files[name]
        if name.endswith('.py'):
            ast.parse((package / name).read_text('utf8'))
    save(root / 'preparation.json', {
        'package': str(package), 'manifest_sha256': sha(package / 'manifest.json'),
        'unchanged_source_members': unchanged, 'native_injection_and_Flash_gate_byte_identical': True,
        'parent_11_CPU_route_checks_reused_by_exact_source_identity': True,
        'new_model_GUI_calls': 0, 'parent_terminals_not_reexecuted': True,
    })
    (root / 'prepare-source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    save(HERE / 'preparation-current.json', {'root': str(root), 'package': str(package),
         'manifest_sha256': sha(package / 'manifest.json'), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), 'package': str(package), 'trajectories': 2,
                      'new_model_GUI_calls': 0, 'resource_admission_still_required': True}))


if __name__ == '__main__':
    main()
