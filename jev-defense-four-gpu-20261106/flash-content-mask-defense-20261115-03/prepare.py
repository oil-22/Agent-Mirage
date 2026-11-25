"""Prepare four distinct development trials only after the parent is sealed."""
import ast
import hashlib
import json
import secrets
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent/'flash-late-corruption-defense-20261115-02'
P = HERE/'package'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, value):
    with path.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

def checked(pointer):
    value = json.loads(pointer.read_bytes())
    root = Path(value['root'])
    assert sha(root/'seal.json') == value['seal_sha256']
    for name, h in json.loads((root/'seal.json').read_bytes()).items():
        assert sha(root/name) == h, name
    return value, root

def main():
    assert not P.exists()
    publication, pub = checked(PRIOR/'completed-publication-current.json')
    published = json.loads((pub/'results.json').read_bytes())
    assert published['all12_complete_source_reviewed']
    audit, ar = checked(PRIOR/'completed-group-audit-current.json')
    summary = json.loads((ar/'summary.json').read_bytes())
    assert summary['processed_GUI_trajectories'] == 12
    assert summary['all_original_model_GUI_launcher_identities_exited']
    old = PRIOR/'package'
    m = json.loads((old/'manifest.json').read_bytes())
    for name, h in m['files'].items():
        assert sha(old/name) == h, name
    for host in ['3090', '4090']:
        prior = json.loads((HERE/('prior-'+host+'.json')).read_bytes())['result']
        assert prior['expected_trajectories'] == 12 and prior['all_twelve_terminal']
        assert all(not row['same_live'] for row in prior['processes'])
    shutil.copytree(old, P)
    replaced = ['manifest.json', 'plan.json', 'analysis-plan.json', 'private.token',
                'continuation_guard.py', 'injection.py', 'user-current-authorization.json',
                'prior-3090.json', 'prior-4090.json']
    # Remove only exact named files in this newly made copy; parents are immutable.
    for name in replaced:
        (P/name).unlink()
    for name in ['continuation_guard.py', 'injection.py', 'prior-3090.json', 'prior-4090.json']:
        shutil.copyfile(HERE/name, P/name)
    shutil.copyfile(HERE/'user-authorization.json', P/'user-current-authorization.json')
    with (P/'private.token').open('x', encoding='utf8') as f:
        f.write(secrets.token_hex(32))
    queue = []
    for task, arms in [(0, ['baseline', 'gate']), (94, ['gate', 'baseline'])]:
        queue.extend({'run_id': f'mask15-T{task:03}-late_content_mask3-{arm}',
                      'task_id': task, 'condition': 'late_content_mask3',
                      'gate_enabled': arm == 'gate'} for arm in arms)
    version = 'content-mask-three-capture-single-Flash-development-v3'
    plan = json.loads((old/'plan.json').read_bytes())
    plan.update({'version': version, 'created': time.time(), 'queue': queue,
        'expected_trajectories': 4, 'matched_pairs': 2, 'conditions': ['late_content_mask3'],
        'injection': {'min_main_decision': 10, 'fixed_consecutive_capture_count': 3,
            'trigger': 'first changed raw capture following click/type/press/back/tab at or after decision10',
            'mask_rectangle': 'x0=width*3//10,y0=height*17//100,to bottom-right; pure white',
            'target_OCR_task_answer_used_for_mask': False, 'same_capture_rule_both_arms': True,
            'recaptures_consume_dose': True, 'after_episode': 'fresh unmodified live raw PNG',
            'if_never_triggered': 'untriggered, never defense success'},
        'current_user_authorization_sha256': sha(P/'user-current-authorization.json'),
        'parent_terminal_publication': publication, 'parent_completed_raw_audit': audit,
        'excluded_prior_terminals': [row['run_id'] for row in json.loads((old/'plan.json').read_bytes())['queue']],
        'interpretation': 'Adaptive selected development; retain all four outcomes. Definite baseline Mirage plus verified refusal/fresh recapture and corresponding error avoidance required for a local effect. No guaranteed success, overall rate or significance from selected pairs.'})
    save(P/'plan.json', plan)
    save(P/'analysis-plan.json', {'tasks': [0, 94], 'trajectories': 4, 'pairs': 2,
        'condition': 'late_content_mask3', 'known_source_adaptive_development': True,
        'primary': 'complete source-reviewed boundary-inclusive Mirage; native WAIT excluded',
        'mechanism': 'actual injected PNG -> NO -> genuine same-live recapture -> YES -> native action',
        'normal_frame_NO_reviewed_separately': True, 'all_failures_uncertainty_retained': True,
        'main_system_full_history_original_budgets_unchanged': True,
        'single_Flash_prompt_revision_no_context_unchanged': True,
        'no_old_terminal_reruns': True, 'all8_reserved_GPUs_counted': True,
        'new_paid_API_calls': 0})
    files = {str(q.relative_to(P)).replace('\\', '/'): sha(q)
             for q in P.rglob('*') if q.is_file() and q.name != 'private.token'}
    manifest = {**m, 'version': version, 'study': version, 'created': time.time(),
        'files': files, 'auth_token_sha256': sha(P/'private.token'),
        'package3090': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/'+HERE.name,
        'package4090': '/data/researcher/jev-defense-four-gpu-20261106/'+HERE.name,
        'output3090': '/data/researcher/jev-defense-four-gpu-20261106/'+HERE.name,
        'trajectories': 4, 'remaining_queue': queue,
        'current_user_authorization_sha256': sha(P/'user-current-authorization.json'),
        'source_prior_manifest_sha256': sha(old/'manifest.json'),
        'prior_terminal_publication': publication, 'prior_completed_raw_audit': audit,
        'new_GUI_queue': True, 'new_capacity_calls': 0, 'formal_Mirage_efficacy_proven': False}
    save(P/'manifest.json', manifest)
    exact = ['gui_experiment.py', 'primary_server.py', 'historical_memory.py',
        'expanded_guard.py', 'launch_group.py', 'gui_outer.py', 'actor-template.json',
        'native-parser-source.py', 'flash/gate-contract.json', 'flash/gate_core.py',
        'flash/flash_runtime.py', 'flash/flash_service.py', 'release/defense/qwen_backend.py']
    for name in exact:
        assert sha(P/name) == sha(old/name), name
    for name, h in files.items():
        assert sha(P/name) == h
        if name.endswith('.py'):
            ast.parse((P/name).read_text('utf8'))
    save(HERE/'preparation.json', {'time': time.time(), 'files': len(files),
        'manifest_sha256': sha(P/'manifest.json'), 'queue': queue,
        'unchanged_original_core_files': exact, 'parent_publication': publication,
        'parent_audit': audit, 'only_injection_condition_changed': True,
        'new_model_GUI_calls': 0})
    print(json.dumps({'files': len(files), 'trajectories': 4,
                     'manifest_sha256': sha(P/'manifest.json'), 'new_model_GUI_calls': 0}))

if __name__ == '__main__':
    main()
