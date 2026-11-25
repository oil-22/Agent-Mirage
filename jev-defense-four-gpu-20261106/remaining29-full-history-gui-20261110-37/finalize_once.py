"""Finalize exactly the source-condition choice actually supplied by the human."""
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
TEMPLATE_PARENT = BASE / 'remaining29-runtime-template-20261110-36'
PROPOSAL_PARENT = BASE / 'native-answer-origin-staging-20261110-34'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def verified(pointer):
    root = Path(pointer['root'])
    assert sha(root / 'seal.json') == pointer['seal_sha256']
    for name, digest in read(root / 'seal.json').items():
        assert sha(root / name) == digest, name
    return root


def main():
    package = HERE / 'runtime-package'
    assert not package.exists() and not (HERE / 'preparation.json').exists(), 'Inspect existing attempt; no duplicate finalization'
    decision = read(HERE / 'human-source-condition-decision.json')
    assert decision['source'] == 'explicit_human_reply_to_existing_source_condition_question'
    assert decision['choice'] == 'adopt_exact_decoded_native_STOP_answer_source'
    assert decision['verbatim_human_reply'] == '采用修复，继续剩余 29 条（推荐）'
    assert decision['scope'] == 'original32_minus_three_immutable_terminals_remaining29'
    template_pointer = read(TEMPLATE_PARENT / 'preparation-created.json')
    template_root = verified(template_pointer)
    template = template_root / 'runtime-template'
    before = read(template / 'manifest.json')
    assert before['template_only'] and before['launch_ready'] is False
    proposal_pointer = read(PROPOSAL_PARENT / 'preparation-created.json')
    proposal = verified(proposal_pointer)
    source = proposal / 'proposed-release'
    package.mkdir()
    for name in before['files']:
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template / name, target)
    (package / 'private.token').write_text(secrets.token_hex(32), encoding='ascii')
    assert sha(package / 'private.token') != before['auth_token_sha256']
    shutil.copyfile(HERE / 'human-source-condition-decision.json', package / 'human-source-condition-decision.json')
    changed = []
    for path in sorted(source.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        target = package / 'release' / relative
        if not target.exists() or target.read_bytes() != path.read_bytes():
            changed.append(relative.as_posix())
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    assert set(changed) == {'defense/core.py', 'decoded_answer_source.py'}
    # Exact approved source files, including the already-reviewed development
    # version metadata. No extra Controller change is introduced here.
    assert sha(package / 'release/defense/core.py') == sha(source / 'defense/core.py')
    assert sha(package / 'release/decoded_answer_source.py') == sha(source / 'decoded_answer_source.py')
    admission = read(package / 'admission.json')
    admission.update(admit_new_GUI_development=True, source_condition_decision_received=True,
                     source_condition_choice=decision['choice'], staging_template_only=False,
                     human_decision_receipt_sha256=sha(package / 'human-source-condition-decision.json'),
                     authorization='Actual human reply adopts sealed exact native STOP answer source for remaining29; original scope/caps and three terminal exclusions retained')
    (package / 'admission.json').write_text(json.dumps(admission, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = copy.deepcopy(before)
    manifest.update(schema='GUI-original32-remaining29-human-approved-native-answer-origin-v1',
                    template_only=False, launch_ready=True, authorized_finite_joint_development=True,
                    source_condition_choice=decision['choice'], source_condition_decision_received=True,
                    human_decision_receipt_sha256=sha(package / 'human-source-condition-decision.json'),
                    approved_source_proposal=proposal_pointer,
                    approved_Controller_source_sha256=sha(package / 'release/defense/core.py'),
                    exact_decoded_answer_helper_sha256=sha(package / 'release/decoded_answer_source.py'),
                    auth_token_sha256=sha(package / 'private.token'),
                    original_Controller_and_all_forward_sources_unchanged=False,
                    all_forward_prompts_history_native_actions_and_budgets_unchanged=True,
                    Controller_changes_exactly_sealed_approved_source_mapping=True,
                    original_source_condition_boundary_retained_in_analysis=True,
                    previous_human_decision_blocker_resolved=True,
                    resource_ownership_or_available_port_not_guaranteed_by_local_finalization=True)
    manifest['source_condition_tradeoffs'] += (
        ' Human explicitly selected the exact native STOP answer source repair on2026-11-10. '
        'The exact sealed proposed Controller and helper are now used. Exact decoded characters bind back to raw candidate bytes; '
        'no paraphrase/normalization/concatenation/number correction or automatic truth/allow decision. '
        'This changes admissible source representation; original three endpoints remain under their original versions. '
        'Original32 scope and all16 pairs remain; remaining29 are not a silent replacement sample.')
    manifest['files'] = {path.relative_to(package).as_posix(): sha(path)
                         for path in sorted(package.rglob('*'))
                         if path.is_file() and path.name not in ['manifest.json', 'private.token']}
    save(package / 'manifest.json', manifest)
    for path in package.rglob('*.py'):
        compile(path.read_text(encoding='utf-8'), str(path), 'exec')
    for name, digest in before['files'].items():
        if name not in ['admission.json', 'release/defense/core.py']:
            assert sha(package / name) == digest, name
    result = subprocess.run([sys.executable, '-B', str(HERE / 'check_finalized.py')], capture_output=True)
    (HERE / 'CPU-finalization.stdout.txt').write_bytes(result.stdout)
    (HERE / 'CPU-finalization.stderr.txt').write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    checks = json.loads(result.stdout)
    save(HERE / 'preparation.json', {
        'time': time.time(), 'source_template': template_pointer, 'approved_proposal': proposal_pointer,
        'manifest_sha256': sha(package / 'manifest.json'), 'human_decision_sha256': sha(HERE / 'human-source-condition-decision.json'),
        'Controller_release_changes_only': changed, 'CPU_checks': checks,
        'new_model_GPU_GUI_scorer_paid_calls': 0, 'actual_launch_not_yet_performed': True,
        'original_full32_scope_preserved': True, 'only29_never_started_tracks_admitted': True,
        'three_original_terminals_and362_requests_cannot_be_reused': True,
        'no_prompt_history_image_precision_action_or_budget_change': True,
        'efficacy_established': False,
    })
    save(HERE / 'CPU-admission.json', {'passed': True, 'manifest_sha256': sha(package / 'manifest.json'),
                                     'source_choice_explicitly_human_authorized': True,
                                     'tracks': 29, 'new_model_GPU_GUI_scorer_paid_calls': 0})
    save(HERE / 'preparation-seal.json', {path.relative_to(HERE).as_posix(): sha(path)
        for path in sorted(HERE.rglob('*')) if path.is_file() and path.name != 'private.token'})
    print(json.dumps({'manifest_sha256': sha(package / 'manifest.json'), 'tracks': 29,
                      'first_run': read(package / 'continuation.json')['remaining_run_ids'][0],
                      'CPU_checks': checks, 'new_model_GPU_GUI_scorer_paid_calls': 0}, ensure_ascii=True))


if __name__ == '__main__':
    main()
