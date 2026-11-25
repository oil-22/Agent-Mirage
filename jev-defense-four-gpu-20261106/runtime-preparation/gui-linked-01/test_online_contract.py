"""CPU admission and provenance failure controls; no model imports or calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from online_contract import admit, begin, finish, initial_state, validate_plan, validate_completed_stage_shutdown
from online_service import health_result, journal

PLAN = Path(__file__).resolve().parents[2] / 'policy-preparation/image-observer-policy/gui-plan.json'


class OnlineAdmission(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(PLAN.read_bytes())
        self.state = initial_state(self.plan)
        self.run = self.plan['queue'][0]['run_id']
        begin(self.state, self.plan, self.run)

    def envelope(self, operation='actor', attempt=1, decision=1, run=None):
        return {'trajectory_id': run or self.run, 'decision_index': decision,
            'attempt_index': attempt, 'request_id': 'a' * 32,
            'payload': {'operation': operation}}

    def test_finite_four_runs_keep_caps_and_baseline_zero_observer(self):
        rows = validate_plan(self.plan)
        self.assertEqual([r['caps']['observe'] for r in rows.values()], [0, 60, 0, 60])

    def test_first_actor_and_judge_have_independent_native_counters(self):
        admit(self.state, self.plan, self.envelope('actor'), 'primary')
        admit(self.state, self.plan, self.envelope('judge'), 'primary')
        self.assertEqual(self.state['runs'][self.run]['calls'], {'actor': 1, 'judge': 1, 'observe': 0})

    def test_baseline_cannot_call_flash(self):
        with self.assertRaises(ValueError): admit(self.state, self.plan, self.envelope(), 'pplx_flash')

    def test_repeated_attempt_cannot_run_again(self):
        admit(self.state, self.plan, self.envelope(), 'primary')
        with self.assertRaises(ValueError): admit(self.state, self.plan, self.envelope(), 'primary')

    def test_actor_budget_seventy_is_not_seventy_one(self):
        row = self.state['runs'][self.run]
        row['calls']['actor'] = 69
        admit(self.state, self.plan, self.envelope(attempt=70), 'primary')
        with self.assertRaises(ValueError): admit(self.state, self.plan, self.envelope(attempt=71), 'primary')

    def test_judge_budget_one_forty_is_not_one_forty_one(self):
        self.state['runs'][self.run]['calls']['judge'] = 139
        admit(self.state, self.plan, self.envelope('judge', attempt=140), 'primary')
        with self.assertRaises(ValueError): admit(self.state, self.plan, self.envelope('judge', attempt=141), 'primary')

    def test_observer_sixty_is_a_hard_trajectory_cap(self):
        finish(self.state, self.run, 'completed')
        self.run = self.plan['queue'][1]['run_id']; begin(self.state, self.plan, self.run)
        self.state['runs'][self.run]['calls']['observe'] = 59
        admit(self.state, self.plan, self.envelope(attempt=60), 'pplx_flash')
        with self.assertRaises(ValueError): admit(self.state, self.plan, self.envelope(attempt=61), 'pplx_flash')

    def test_step_fifty_and_monotonic_order_are_enforced(self):
        admit(self.state, self.plan, self.envelope(decision=50), 'primary')
        for decision in (49, 51, True):
            with self.assertRaises(ValueError): admit(self.state, self.plan,
                self.envelope(attempt=2, decision=decision), 'primary')

    def test_other_trajectory_cannot_borrow_active_ones_budget(self):
        with self.assertRaises(ValueError): admit(self.state, self.plan,
            self.envelope(run=self.plan['queue'][1]['run_id']), 'primary')

    def test_second_run_cannot_start_before_first_finishes(self):
        with self.assertRaises(ValueError): begin(self.state, self.plan, self.plan['queue'][1]['run_id'])

    def test_terminal_run_cannot_restart_or_skip_order(self):
        finish(self.state, self.run, 'completed')
        for run in (self.run, self.plan['queue'][2]['run_id']):
            with self.assertRaises(ValueError): begin(self.state, self.plan, run)

    def test_technical_failure_prevents_automatic_next_run(self):
        finish(self.state, self.run, 'technical_failure')
        with self.assertRaises(ValueError): begin(self.state, self.plan, self.plan['queue'][1]['run_id'])

    def test_stopped_run_is_terminal_and_not_a_success(self):
        finish(self.state, self.run, 'stopped')
        self.assertEqual(self.state['phase'], 'terminal_failure')
        with self.assertRaises(ValueError): admit(self.state, self.plan, self.envelope(), 'primary')

    def test_extra_context_and_non_native_operation_are_rejected(self):
        value = self.envelope(); value['history'] = 'extra'
        with self.assertRaises(ValueError): admit(self.state, self.plan, value, 'primary')
        with self.assertRaises(ValueError): admit(self.state, self.plan, self.envelope('arbitrary'), 'primary')

    def test_unreviewed_cap_or_queue_change_is_rejected(self):
        value = copy.deepcopy(self.plan); value['limits']['max_actor_calls'] = 71
        with self.assertRaises(ValueError): validate_plan(value)
        value = copy.deepcopy(self.plan); value['queue'].reverse()
        with self.assertRaises(ValueError): validate_plan(value)


class JournalChain(unittest.TestCase):
    def test_native_client_ready_gui_phase_requires_both_actual_peers(self):
        resources = {'actual_allowed_pids': [1, 2]}
        self.assertEqual(health_result('primary', {}, resources, True)['phase'], 'ready_gui')
        self.assertNotEqual(health_result('primary', {}, resources, False)['phase'], 'ready_gui')
        self.assertNotEqual(health_result('primary', {}, {'actual_allowed_pids': [1]}, True)['phase'], 'ready_gui')

    def test_cross_role_append_is_hash_chained(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'journal.jsonl'
            first = journal(path, 'primary', {'wire_sha256': 'a' * 64})
            second = journal(path, 'observer', {'wire_sha256': 'b' * 64})
            rows = [json.loads(row) for row in path.read_bytes().splitlines()]
            self.assertEqual(rows[1]['previous_sha256'], first)
            self.assertEqual(rows[1]['sha256'], second)

    def test_mutated_prior_request_breaks_chain_and_stops_append(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'journal.jsonl'
            journal(path, 'primary', {'wire_sha256': 'a' * 64})
            row = json.loads(path.read_bytes()); row['payload']['wire_sha256'] = 'b' * 64
            path.write_text(json.dumps(row) + '\n', encoding='utf8')
            with self.assertRaises(RuntimeError): journal(path, 'observer', {})


class CompletedStageShutdown(unittest.TestCase):
    def setUp(self):
        flags = ('infrastructure_only', 'accepted_for_completed_stage_only',
            'no_real_model_failure_bypassed', 'both_stopped_before_exit', 'exact_calls_primary1_helper0',
            'all_existing_inference_requests_complete', 'capacity_natural_EOS_and_forward_audit_preserved',
            'request_seals_unchanged', 'original_exit_codes_preserved', 'old_launcher_sends_worker_USR1')
        self.cap = '5a89138010f8cf005cbcd03bc2a4b249af0e253178666388fb17652bb0571fb8'
        self.proof = {**{key: True for key in flags}, 'status': 'passed',
            'classification': 'completed_stage_control_exit_after_stopped_receipts',
            'pending_request_count': 0, 'target_compute_process_count': 0,
            'primary_request_count': 1, 'helper_request_count': 0,
            'group': '/known/completed/group', 'terminal_manifest_sha256': 't' * 64,
            'capacity_audit_receipt_sha256': self.cap,
            'actual_worker_exit_codes': {'primary': -10, 'pplx_flash': 0},
            'old_launcher_source_sha256': '6847f75f2733172ad0eece2568c3abd3e9655357d82182b63046db3dab41d54e',
            'old_worker_source_sha256': '482d98e9674d0e568106b9ebfadd5e7a3a61f3ce6d6ba26f7d36b453e6b034aa'}

    def check(self):
        validate_completed_stage_shutdown(self.proof, '/known/completed/group', 't' * 64,
            {'primary': -10, 'pplx_flash': 0}, self.cap)

    def test_exact_completed_infrastructure_case_preserves_nonzero_exit(self):
        self.check(); self.assertEqual(self.proof['actual_worker_exit_codes']['primary'], -10)

    def test_other_signal_or_model_failure_is_never_normalized(self):
        self.proof['actual_worker_exit_codes']['primary'] = -9
        with self.assertRaises(ValueError): self.check()
        self.setUp(); self.proof['no_real_model_failure_bypassed'] = False
        with self.assertRaises(ValueError): self.check()

    def test_pending_or_remaining_compute_prevents_release(self):
        for key in ('pending_request_count', 'target_compute_process_count'):
            self.setUp(); self.proof[key] = 1
            with self.assertRaises(ValueError): self.check()

    def test_unfinished_or_changed_seals_prevent_release(self):
        for key in ('both_stopped_before_exit', 'request_seals_unchanged',
                    'capacity_natural_EOS_and_forward_audit_preserved'):
            self.setUp(); self.proof[key] = False
            with self.assertRaises(ValueError): self.check()

    def test_other_capacity_or_stage_cannot_reuse_this_exception(self):
        for key in ('capacity_audit_receipt_sha256', 'group', 'terminal_manifest_sha256'):
            self.setUp(); self.proof[key] = 'different'
            with self.assertRaises(ValueError): self.check()

    def test_extra_or_repeated_completed_model_calls_prevent_release(self):
        for key in ('primary_request_count', 'helper_request_count'):
            self.setUp(); self.proof[key] += 1
            with self.assertRaises(ValueError): self.check()

    def test_unbound_old_shutdown_source_is_rejected(self):
        self.proof['old_launcher_source_sha256'] = 'x' * 64
        with self.assertRaises(ValueError): self.check()


if __name__ == '__main__': unittest.main()
