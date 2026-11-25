"""Exercise new queue admission/counters against the original source-bound plan."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
OLD = HERE.parent / 'prefill-scheduled-full-history-gui-20261109-32/runtime-package'
sys.path.insert(0, str(PACKAGE))
from protocol import RunBudget
from continuation_manifest import remaining_queue, completed_request_ids
from terminal_outcome_classification import classify_run_termination


def main():
    plan = json.loads((PACKAGE / 'plan.json').read_bytes())
    carry = json.loads((PACKAGE / 'carryover/state.json').read_bytes())
    checks = []
    def check(label, value):
        assert value, label
        checks.append(label)
    def refused(label, call):
        try:
            call()
        except (AssertionError, ValueError):
            checks.append(label)
        else:
            raise AssertionError('Should refuse: ' + label)
    counter = [0]
    def ident():
        counter[0] += 1
        return format(counter[0], '032x')
    def begin(budget):
        return budget.admit('/begin', dict(trajectory_id=budget.queue[budget.index]['run_id'], request_id=ident()))
    def call(budget, op, index, **updates):
        body = dict(trajectory_id=budget.active, request_id=ident(), decision_index=1,
                    attempt_index=index, payload={'operation': op})
        body.update(updates)
        return budget.admit('/evidence' if op == 'evidence' else '/', body)
    queue = remaining_queue(plan)
    check('unchanged_complete_original32_plan_bytes', (PACKAGE / 'plan.json').read_bytes() == (OLD / 'plan.json').read_bytes())
    check('exact_original_tail31_and_order', queue == plan['queue'][1:])
    check('first_remaining_original_auxiliary_track', queue[0]['observer_enabled'] and queue[0]['run_id'] == 'fullhistory23-T000-clean-aux')
    check('old_terminal_id_absent', carry['original_track'] not in {q['run_id'] for q in queue})
    check('111_old_model_requests_explicitly_excluded', len(completed_request_ids()) == 111)
    budget = RunBudget(plan, carry)
    begin(budget)
    check('first_new_counts_zero_not_carried17and50', budget.counts == dict(actor=0, judge=0, evidence=0))
    call(budget, 'evidence', 1)
    call(budget, 'actor', 1)
    call(budget, 'judge', 1)
    check('first_new_attempt_one_for_each_role', budget.counts == dict(actor=1, judge=1, evidence=1))
    refused('old_completed_model_request_id_refused', lambda: call(budget, 'actor', 2, request_id=next(iter(completed_request_ids()))))
    refused('old_carried_actor18_is_not_new_first_attempt', lambda: call(budget, 'actor', 18))
    refused('old_carried_judge51_is_not_new_first_attempt', lambda: call(budget, 'judge', 51))
    refused('wrong_original_queue_order_refused', lambda: call(budget, 'actor', 2, trajectory_id=queue[1]['run_id']))
    refused('excluded_terminal_track_not_admitted', lambda: call(budget, 'actor', 2, trajectory_id=carry['original_track']))
    refused('step51_refused', lambda: call(budget, 'actor', 2, decision_index=51))
    for op, cap in [('actor', 70), ('judge', 140), ('evidence', 60)]:
        limited = RunBudget(plan, carry); begin(limited)
        for n in range(1, cap + 1):
            call(limited, op, n)
        check(op + '_original_cap_exactly_reachable', limited.counts[op] == cap)
        refused(op + '_original_cap_plus_one_refused', lambda: call(limited, op, cap + 1))
    all_runs = RunBudget(plan, carry)
    for item in queue:
        begin(all_runs)
        assert all_runs.counts == dict(actor=0, judge=0, evidence=0)
        if not item['observer_enabled']:
            refused('noaux_evidence_refused_' + item['run_id'], lambda: call(all_runs, 'evidence', 1))
        call(all_runs, 'actor', 1)
        all_runs.admit('/end', dict(trajectory_id=all_runs.active, request_id=ident(), status='completed', terminal_receipt_sha256='a' * 64))
    check('all31_begin_zero_and_exact_finite_terminal', all_runs.terminal and len(all_runs.done) == 31 and not all_runs.failed)
    for status in ['technical_failure', 'stopped']:
        failed = RunBudget(plan, carry); begin(failed)
        failed.admit('/end', dict(trajectory_id=failed.active, request_id=ident(), status=status, terminal_receipt_sha256='b' * 64))
        check('original_hard_stop_preserved_' + status, failed.failed and failed.terminal)
        refused('no_auto_retry_after_' + status, lambda: begin(failed))
    local = classify_run_termination('blocked', 'point_verifier_error:verifier_call_cap', 'complete', 140, 140)
    check('real_exact_local_cap_is_logical_terminal', local['local_verifier_budget_exhausted'] and local['technical_status'] == 'no_reported_infrastructure_failure' and local['new_calls_or_retries_granted'] == 0)
    for reason, scoring, count, expected in [
        ('point_verifier_error:HTTP500', 'complete', 140, 'verifier_failure'),
        ('point_verifier_error:verifier_call_cap', 'complete', 139, 'verifier_failure'),
        ('point_verifier_error:verifier_call_cap', 'failed', 140, 'scoring_failure'),
        ('completion_verifier_error:invalid_contract', 'complete', 140, 'verifier_failure')]:
        value = classify_run_termination('blocked', reason, scoring, count, 140)
        check('real_failures_preserved_' + reason + '_' + scoring + '_' + str(count), value['technical_status'] == expected)
    unchanged = ['release/defense/core.py', 'release/defense/prompts.py', 'release/image_evidence.py',
        'release/evidence_observer.py', 'model_runtime.py', 'prefill_residency.py', 'resident_schedule.py',
        'bounded_auxiliary.py', 'bounded_schema.py', 'unicode_length_guard.py', 'stateless_boundary.py',
        'gui_transport.py', 'complete_actor_history.py', 'actor-template.json', 'fixed-prompt.txt', 'native-parser-source.py']
    for name in unchanged:
        assert (PACKAGE / name).read_bytes() == (OLD / name).read_bytes(), name
    check('all_original_model_forward_and_acceptance_sources_unchanged', True)
    server = (PACKAGE / 'gpu_server.py').read_text(encoding='utf8').replace('19141', '19140')
    check('server_only_new_transport_port', server == (OLD / 'gpu_server.py').read_text(encoding='utf8'))
    m = json.loads((PACKAGE / 'manifest.json').read_bytes())
    for name, expected in m['files'].items():
        assert hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == expected, name
    check('complete_new_frozen_package_SHA', True)
    print(json.dumps(dict(passed=True, CPU_checks=len(checks), checks=checks,
        real_model_negative_WAIT_or_GUI_controls=False, new_model_GUI_scorer_calls=0)))


if __name__ == '__main__':
    main()
