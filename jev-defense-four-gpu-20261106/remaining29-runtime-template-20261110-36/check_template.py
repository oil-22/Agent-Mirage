"""CPU-only new continuation checks; no model or browser controls are repeated."""
import builtins
import copy
import hashlib
import importlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile


PACKAGE = Path(sys.argv[1]).resolve()
BASE = Path(__file__).resolve().parent.parent
OLD = BASE / 'remaining-full-history-gui-20261110-33/runtime-package'
sys.path.insert(0, str(PACKAGE))
continuation = importlib.import_module('continuation_manifest')
protocol = importlib.import_module('protocol')
gate = importlib.import_module('source_decision_gate')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def main():
    groups = []

    def check(label, value):
        assert value, label
        groups.append(label)

    def refused(call):
        try:
            call()
        except (AssertionError, gate.PendingSourceDecision):
            return
        raise AssertionError('Expected source/budget refusal')

    plan = read(PACKAGE / 'plan.json')
    carry = read(PACKAGE / 'carryover/state.json')
    source = read(PACKAGE / 'continuation.json')
    queue = continuation.remaining_queue(plan)
    check('original_full32_plan_exact_bytes_and_all16_pairs_retained',
          (PACKAGE / 'plan.json').read_bytes() == (OLD / 'plan.json').read_bytes() and len(plan['queue']) == 32)
    check('remaining29_exact_original_order_minus_all_three_terminals',
          queue == [x for x in plan['queue'] if x['run_id'] not in continuation.FINISHED] and len(queue) == 29)
    check('first_remaining_original_stale_noaux',
          queue[0]['run_id'] == 'fullhistory23-T000-stale_replace-noaux' and not queue[0]['observer_enabled'])
    ids = continuation.completed_request_ids()
    check('all362_prior_ids_source_bound', len(ids) == 362)
    counter = [0]

    def ident():
        counter[0] += 1
        value = format(counter[0], '032x')
        assert value not in ids
        return value

    def begin(budget, **updates):
        body = {'trajectory_id': budget.queue[budget.index]['run_id'], 'request_id': ident()}
        body.update(updates)
        return budget.admit('/begin', body)

    def call(budget, op, **updates):
        body = {'trajectory_id': budget.active, 'request_id': ident(), 'decision_index': 1,
                'attempt_index': 1, 'payload': {'operation': op}}
        body.update(updates)
        return budget.admit('/evidence' if op == 'evidence' else '/', body)

    budget = protocol.RunBudget(plan, carry)
    for old_id in ids:
        refused(lambda old_id=old_id: begin(budget, request_id=old_id))
    check('each_prior_request_ID_refused_before_new_begin', budget.index == 0 and budget.active is None)
    for run_id in continuation.FINISHED:
        refused(lambda run_id=run_id: begin(budget, trajectory_id=run_id))
    check('each_completed_terminal_run_refused_at_transport_begin', budget.active is None)
    begin(budget)
    check('first_new_noaux_counters_zero_not_old_carried_counts',
          budget.counts == {'actor': 0, 'judge': 0, 'evidence': 0})
    refused(lambda: call(budget, 'evidence'))
    call(budget, 'actor')
    call(budget, 'judge')
    check('new_noaux_actor1_judge1_allowed_aux_refused',
          budget.counts == {'actor': 1, 'judge': 1, 'evidence': 0})
    refused(lambda: call(budget, 'actor', attempt_index=18))
    refused(lambda: call(budget, 'judge', attempt_index=51))
    refused(lambda: call(budget, 'actor', attempt_index=2, trajectory_id=queue[1]['run_id']))
    check('carried_attempt_numbers_and_wrong_run_refused', budget.counts == {'actor': 1, 'judge': 1, 'evidence': 0})
    all_runs = protocol.RunBudget(plan, carry)
    for item in queue:
        begin(all_runs)
        assert all_runs.counts == {'actor': 0, 'judge': 0, 'evidence': 0}
        if item['observer_enabled']:
            call(all_runs, 'evidence')
        else:
            refused(lambda: call(all_runs, 'evidence'))
        call(all_runs, 'actor')
        call(all_runs, 'judge')
        all_runs.admit('/end', {'trajectory_id': all_runs.active, 'request_id': ident(),
                               'status': 'completed', 'terminal_receipt_sha256': 'c' * 64})
    check('all29_synthetic_protocol_runs_begin_zero_then_finite_terminal',
          all_runs.terminal and len(all_runs.done) == 29 and not all_runs.failed)
    for end in ['technical_failure', 'stopped']:
        stopped = protocol.RunBudget(plan, carry)
        begin(stopped)
        stopped.admit('/end', {'trajectory_id': stopped.active, 'request_id': ident(),
                              'status': end, 'terminal_receipt_sha256': 'd' * 64})
        refused(lambda: begin(stopped))
        assert stopped.terminal and stopped.failed and len(stopped.done) == 1
    check('technical_and_stopped_terminals_still_stop_batch_without_retry', True)
    changed = copy.deepcopy(plan)
    changed['limits']['max_verifier_calls'] += 1
    refused(lambda: continuation.remaining_queue(changed))
    check('attempted_budget_change_refused_as_non_original_plan', True)
    # Tamper only disposable local copies, never immutable evidence or runtime.
    original_here = continuation.HERE
    with tempfile.TemporaryDirectory(prefix='mirage29-source-contract-') as temp:
        work = Path(temp)
        for name in ['plan.json', 'continuation.json', 'completed-request-exclusions.json']:
            shutil.copyfile(PACKAGE / name, work / name)
        for row in source['terminal_copies']:
            target = work / row['copy']
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(PACKAGE / row['copy'], target)
        continuation.HERE = work
        try:
            target = work / source['terminal_copies'][2]['copy']
            raw = target.read_bytes()
            target.write_bytes(raw + b'\n')
            refused(lambda: continuation.remaining_queue(plan))
            target.write_bytes(raw)
            target = work / 'completed-request-exclusions.json'
            target.write_bytes(target.read_bytes() + b'\n')
            refused(continuation.completed_request_ids)
        finally:
            continuation.HERE = original_here
    check('changed_terminal_bytes_or_request_exclusion_bytes_refused', True)
    manifest = read(PACKAGE / 'manifest.json')
    check('template_admission_explicitly_denied',
          manifest['template_only'] is True and manifest['launch_ready'] is False and
          manifest['authorized_finite_joint_development'] is False and
          read(PACKAGE / 'admission.json')['admit_new_GUI_development'] is False)
    refused(lambda: gate.require_finalized(PACKAGE / 'gpu_server.py'))
    check('source_choice_gate_refuses_template', True)
    blocked_modules = {'torch', 'transformers', 'PIL', 'playwright', 'fcntl', 'socket', 'subprocess'}
    real_import = builtins.__import__
    imported = []

    def guarded_import(name, *args, **kwargs):
        imported.append(name)
        if name.split('.')[0] in blocked_modules:
            raise RuntimeError('Unexpected pre-gate import: ' + name)
        return real_import(name, *args, **kwargs)

    def denied_entry(name):
        try:
            runpy.run_path(str(PACKAGE / name), run_name='__main__')
        except gate.PendingSourceDecision:
            return
        raise AssertionError('Entry point must raise PendingSourceDecision: ' + name)

    for name in ['gpu_server.py', 'launch_gui_service_once.py', 'gui_outer.py', 'run_independent_gui.py']:
        builtins.__import__ = guarded_import
        try:
            denied_entry(name)
        finally:
            builtins.__import__ = real_import
    check('all_four_entrypoints_refuse_before_model_browser_resource_network_imports',
          not any(name.split('.')[0] in blocked_modules for name in imported))
    changes = {'continuation_manifest.py', 'admission.json', 'gpu_server.py',
               'launch_gui_service_once.py', 'gui_outer.py', 'run_independent_gui.py'}
    old_manifest = read(OLD / 'manifest.json')
    for name, digest in old_manifest['files'].items():
        if name not in changes:
            assert sha(PACKAGE / name) == digest, name
    check('all_other_original_files_including_Controller_forward_prompts_history_and_budget_protocol_unchanged', True)
    gate_text = 'from source_decision_gate import require_finalized\nrequire_finalized(__file__)\n'
    for name in ['gpu_server.py', 'launch_gui_service_once.py', 'gui_outer.py', 'run_independent_gui.py']:
        text = (PACKAGE / name).read_text(encoding='utf-8')
        assert text.count(gate_text) == 1
        text = text.replace(gate_text, '', 1)
        if name == 'gpu_server.py':
            text = text.replace('19142', '19141')
        elif name == 'launch_gui_service_once.py':
            text = text.replace('remaining29-full-history-gui-20261110-37', 'remaining-full-history-gui-20261110-33')
        assert text == (OLD / name).read_text(encoding='utf-8'), name
    check('entrypoint_changes_exactly_gate_and_prospective_namespace_port', True)
    for name, digest in manifest['files'].items():
        assert sha(PACKAGE / name) == digest, name
    check('entire_new_template_file_manifest_verified', True)
    print(json.dumps({'passed': True, 'groups': groups,
                      'real_model_negative_WAIT_or_GUI_semantic_controls': False,
                      'no_completed_model_or_old_CPU_source_test_reexecution': True,
                      'synthetic_protocol_simulations_are_not_experiment_trajectories': True,
                      'new_model_GPU_GUI_scorer_paid_calls': 0}, ensure_ascii=True))


if __name__ == '__main__':
    main()
