"""Prepare a NEW 32-trajectory development package; never launches old queues.

The current 22 control run must finish and be audited/reviewed before admission.
No semantic pass or efficacy is implied by preparing or hashing this package.
"""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
MAIN = BASE / 'complete-history-main-preflight-20261109-22/runtime-package'
GUI = BASE / 'full-gui-bounded-evidence-20261109-03/runtime-package'
HISTORY = BASE / 'independent-gui-runner-preparation-20261109-21/prepared-source-linked03'
PACKAGE = HERE / 'runtime-package'
REMOTE_PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name
SERVICE_OUTPUT = '/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name
GUI_PACKAGE = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new)


def main():
    assert not PACKAGE.exists(), 'Once-only source preparation'
    shutil.copytree(MAIN, PACKAGE, ignore=shutil.ignore_patterns(
        '__pycache__', '*.pyc', 'manifest.json', 'private.token', 'CPU-admission',
        'inputs', 'frozen-readings', 'controls-plan.json', 'worker.py',
        'launch_balanced_once.py'))
    for name in ['gpu_server.py', 'launch_gui_service_once.py', 'gui_outer.py',
                 'native_environment.py']:
        shutil.copy2(GUI / name, PACKAGE / name)
    for name in ['run_independent_gui.py', 'complete_actor_history.py',
                 'gui_transport.py', 'protocol.py', 'native-bindings-public.json']:
        shutil.copy2(HISTORY / name, PACKAGE / name)

    launcher = PACKAGE / 'launch_gui_service_once.py'
    text = launcher.read_text(encoding='utf8')
    text = text.replace('full-gui-bounded-evidence-20261109-03', HERE.name)
    launcher.write_text(text, encoding='utf8', newline='\n')

    # Only the orchestration entry point/bindings change. Generation remains the
    # native backend and the runtime/auxiliary code actually exercised in 22/18.
    outer = PACKAGE / 'gui_outer.py'
    text = outer.read_text(encoding='utf8')
    text = replace_once(text, "str(HERE/'run_single_evidence_gui.py')", "str(HERE/'run_independent_gui.py')")
    text = replace_once(text,
        "'--native-task','/data/researcher/jev-defense-validation-20261103/task-restore-1793683370167273452/classifieds_112.PRIVATE.json',",
        "'--native-bindings',str(HERE/'native-bindings-public.json'),")
    text = replace_once(text,
        "assert json.loads((HERE/'environment-preflight/receipt.json').read_bytes())['status']=='passed'",
        "assert json.loads((HERE/'environment-preflight/receipt.json').read_bytes())['status']=='passed'\n"
        "    assert json.loads((HERE/'admission.json').read_bytes())['admit_new_GUI_development'] is True")
    outer.write_text(text, encoding='utf8', newline='\n')

    runner = PACKAGE / 'run_independent_gui.py'
    old = runner.read_text(encoding='utf8')
    # This information already exists in PublicView.execution_feedback. Include
    # the exact lawful native feedback in the actor's own messages too, in both
    # arms, without treating an executor return as a visual postcondition.
    text = replace_once(old,
        "     if raw is not None:blocks.append(block(raw))\n     msgs=transcript.current_messages(blocks)",
        "     if execution_feedback:blocks.append({'type':'text','text':'Previous native execution feedback (execution alone does not confirm the visible result): '+execution_feedback})\n"
        "     if raw is not None:blocks.append(block(raw))\n     msgs=transcript.current_messages(blocks)")
    text = replace_once(text,
        "  if (run/'complete.json').exists():state['completed']+=1;continue",
        "  assert not run.exists(),'Fresh finite queue only; no old completed or unfinished run is resumed'")
    runner.write_text(text, encoding='utf8', newline='\n')
    (HERE / 'runner-changes.diff').write_text(''.join(difflib.unified_diff(
        old.splitlines(True), text.splitlines(True), fromfile='21 linked03', tofile='23 new package')),
        encoding='utf8', newline='\n')

    plan = json.loads((HISTORY / 'plan.json').read_bytes())
    assert len(plan['queue']) == 32
    for row in plan['queue']:
        # New identities, never a pointer to an original terminal or old queue.
        row['run_id'] = row['run_id'].replace('independent8-fullhistory-20261109-21',
                                            'independent8-fullhistory-20261109-23')
        if '20261109-23' not in row['run_id']:
            row['run_id'] = 'fullhistory23-' + row['run_id']
    plan.update(
        policy='single-image-balanced-visual-evidence-v6-development',
        stage='new_independent_matched_full_history_GUI_development',
        authorization='Existing user sustained defense goal; one stateless image-only auxiliary, full lawful main history, original trajectory budgets',
        original_32_track_plan_sha256=sha(HISTORY / 'plan.json'),
        actual_auxiliary_base='Qwen/Qwen3.5-9B',
        actual_auxiliary_revision='c202236235762e1c871ad0ccb60c8ee5ba337b9a',
        decision_adapter_loaded=False,
        fixed_prompt_sha256=sha(PACKAGE / 'fixed-prompt.txt'),
        primary_core_sha256=sha(PACKAGE / 'release/defense/core.py'),
        evidence_contract_sha256=sha(PACKAGE / 'release/image_evidence.py'),
        native_bindings_file_sha256=sha(PACKAGE / 'native-bindings-public.json'),
        primary_layer_counts=[22, 23, 19],
        primary_physical_GPUs=[4, 5, 6, 7],
        primary_visual_and_embedding_share_auxiliary_card=True,
        total_new_primary_call_cap=32 * (70 + 140),
        total_new_auxiliary_call_cap=16 * 60,
        old_4_track_total_cap_metadata_corrected_for_32_new_tracks=True,
        success_claim='Eight source-selected tasks, 32 new development tracks; no guaranteed reduction or general-population efficacy claim',
        complete_accepted_actor_history=True,
        exact_native_execution_feedback_added_to_both_actor_arms=True,
        historical_frames_never_certify_current_state=True,
        auxiliary_same_input_reply_memoization=False,
        per_call_empty_KV_and_release_required=True,
        old_completed_or_technical_terminal_queues_never_resumed=True,
        exact_total_reason_guard09_integrated=False,
        semantic_control_failures_and_long_history_capacity_not_resolved=True,
        source_condition_tradeoff=(
            'Both arms now retain the actual accepted full image/message history and exact native executor feedback; '
            'this increases context/memory relative to the defective old runner. One auxiliary sees only the complete '
            'currently delivered image and fixed v6 prompt, with per-call KV isolation and Unicode length constrained '
            'decoding. Readings may omit or misread facts/boxes; missing readings are never automatic permission or '
            'refusal. Known contradictory judge explanations, page-count mistakes, source errors and false blocks '
            'remain experimental risks. Full-input capacity or Mirage reduction is not guaranteed. Original strict '
            'validators, BF16/SDPA, native actions, scoring, output caps and each trajectory recovery/call budget remain.'),
        formal_efficacy_established=False)
    assert len({row['run_id'] for row in plan['queue']}) == 32
    save(PACKAGE / 'plan.json', plan)
    save(PACKAGE / 'auxiliary-config.json', {
        'model': plan['actual_auxiliary_base'], 'revision': plan['actual_auxiliary_revision'],
        'decision_adapter_loaded': False, 'only_current_full_image_and_fixed_prompt': True,
        'max_calls_per_trajectory': 60, 'no_retry': True,
        'same_input_reply_memoization': False, 'per_call_empty_KV_and_release': True,
        'auxiliary_structural_and_Unicode_length_mask': True})

    # A fresh same-browser setup check for the new first task. This does not
    # rerun the completed eight-task initialization, old controls, or any scorer.
    text = (GUI / 'environment_preflight.py').read_text(encoding='utf8')
    text = replace_once(text, 'import hashlib,io,json,os,subprocess,sys,time,traceback',
                        'import fcntl,hashlib,io,json,os,subprocess,sys,time,traceback')
    text = replace_once(text,
        "    target=HERE/'environment-preflight';target.mkdir(exist_ok=False)",
        "    target=HERE/'environment-preflight';target.mkdir(exist_ok=False)\n"
        "    site_lock=(HERE.parent/'.full-gui-site29980.lock').open('a');fcntl.flock(site_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)")
    text = replace_once(text,
        "        original=BASE/'task-restore-1793683370167273452/classifieds_112.PRIVATE.json'",
        "        bindings=json.loads((HERE/'native-bindings-public.json').read_bytes())\n"
        "        first=next(row for row in bindings['tasks']if row['task_id']==0)\n"
        "        original=Path(first['original_private_path']);assert sha(original)==first['original_private_SHA']")
    (PACKAGE / 'environment_preflight.py').write_text(text, encoding='utf8', newline='\n')

    for path in PACKAGE.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf8'), filename=str(path))
    equal = ['model_runtime.py', 'bounded_auxiliary.py', 'unicode_length_guard.py',
             'stateless_boundary.py', 'auxiliary_grammar_import.py', 'bounded_schema.py',
             'release/defense/qwen_backend.py', 'release/defense/core.py',
             'release/defense/schema.py', 'release/defense/prompts.py',
             'release/image_evidence.py', 'release/evidence_observer.py']
    for name in equal:
        assert (PACKAGE / name).read_bytes() == (MAIN / name).read_bytes(), name
    receipt = {
        'time': time.time(), 'source_preparation_only': True, 'launch_ready': False,
        'GUI_tracks_started': 0, 'new_model_GUI_scorer_paid_calls': 0,
        'tracks': 32, 'task_count': 8, 'matched_pairs': 16,
        'main_preflight22_must_be_terminal_audited_and_reviewed_before_admission': True,
        'native_source_binding_and_same_live_site_preflight_required': True,
        'new_32_queue_not_old_terminal_reexecution': True,
        'core_schema_backend_generation_and_auxiliary_runtime_equal_to22': {name: sha(PACKAGE / name) for name in equal},
        'history_helper_equal_to_native_CPU_tested21': sha(PACKAGE / 'complete_actor_history.py'),
        'new_exact_executor_feedback_in_actor_history_in_both_arms': True,
        'model_and_GUI_remote_packages': {'service': REMOTE_PACKAGE, 'GUI': GUI_PACKAGE},
        'outputs': {'service': SERVICE_OUTPUT, 'GUI': GUI_PACKAGE + '/batch'},
        'known_semantic_failures_not_relabelled_as_passes': True,
        'long_history_fit_or_efficacy_established': False,
        'previous_goal_turn_classification': 'no_progress_for_experiment_goal; answered prompt/output question',
        'next_safe_action': 'Inspect existing22 handles, complete actual reply review and source-bound admission; no duplicate submission',
    }
    save(HERE / 'preparation-receipt.json', receipt)
    save(HERE / 'source-seal.json', {path.relative_to(PACKAGE).as_posix(): sha(path)
                                  for path in sorted(PACKAGE.rglob('*')) if path.is_file()})
    print(json.dumps({'prepared': str(PACKAGE), 'tracks': 32, 'launch_ready': False,
                      'receipt_sha256': sha(HERE / 'preparation-receipt.json'), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
