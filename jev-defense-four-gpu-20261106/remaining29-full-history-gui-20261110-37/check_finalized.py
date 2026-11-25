"""Verify the approved final source integration without a model/browser import."""
import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
sys.path.insert(0, str(PACKAGE))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []
    gate = importlib.import_module('source_decision_gate')
    decision = gate.require_finalized(PACKAGE / 'gpu_server.py')
    assert decision['choice'] == 'adopt_exact_decoded_native_STOP_answer_source'
    checks.append('finalized_gate_binds_actual_human_choice_and_remaining29_scope')
    continuation = importlib.import_module('continuation_manifest')
    plan = json.loads((PACKAGE / 'plan.json').read_bytes())
    queue = continuation.remaining_queue(plan)
    assert len(queue) == 29 and len(continuation.completed_request_ids()) == 362
    checks.append('exact29_queue_and_three_terminal_exclusions_plus362_request_IDs')
    old = HERE.parent / 'remaining-full-history-gui-20261110-33/runtime-package'
    assert (PACKAGE / 'plan.json').read_bytes() == (old / 'plan.json').read_bytes()
    assert (PACKAGE / 'protocol.py').read_bytes() == (old / 'protocol.py').read_bytes()
    checks.append('full32_original_plan_and_all_budget_protocol_bytes_unchanged')
    proposal = HERE.parent / 'native-answer-origin-staging-20261110-34/source-bound-controller-CPU-1794281207228532200/proposed-release'
    for name in ['defense/core.py', 'decoded_answer_source.py']:
        assert sha(PACKAGE / 'release' / name) == sha(proposal / name)
    checks.append('Controller_and_exact_source_helper_match_previously_sealed_approved_proposal')
    for name in ['model_runtime.py', 'prefill_residency.py', 'resident_schedule.py',
                 'bounded_auxiliary.py', 'bounded_schema.py', 'unicode_length_guard.py',
                 'stateless_boundary.py', 'gui_transport.py', 'complete_actor_history.py',
                 'fixed-prompt.txt', 'actor-template.json', 'native-parser-source.py',
                 'release/defense/prompts.py', 'release/image_evidence.py', 'resource_gate.py']:
        assert sha(PACKAGE / name) == sha(old / name), name
    checks.append('all_model_prompt_image_history_action_precision_and_resource_guard_sources_unchanged')
    protocol = importlib.import_module('protocol')
    budget = protocol.RunBudget(plan, json.loads((PACKAGE / 'carryover/state.json').read_bytes()))
    first = queue[0]
    budget.admit('/begin', {'trajectory_id': first['run_id'], 'request_id': '0' * 31 + '1'})
    assert budget.counts == {'actor': 0, 'judge': 0, 'evidence': 0} and not first['observer_enabled']
    checks.append('new_first_stale_noaux_starts_zero_not_old_carried_counts')
    manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
    for name, digest in manifest['files'].items():
        assert sha(PACKAGE / name) == digest, name
    assert manifest['outputs'].endswith(HERE.name) and manifest['model_url'].endswith(':19142')
    assert not any(name in sys.modules for name in ['torch', 'transformers', 'PIL', 'playwright', 'fcntl'])
    checks.append('complete_final_manifest_and_new_namespace_without_model_browser_or_GPU_import')
    print(json.dumps({'passed': True, 'checks': checks, 'new_model_GPU_GUI_scorer_paid_calls': 0,
                      'old21_source_tests_and_completed_model_controls_not_rerun': True,
                      'semantic_GPU_fit_or_efficacy_not_proven_by_this_check': True}, ensure_ascii=True))


if __name__ == '__main__':
    main()
