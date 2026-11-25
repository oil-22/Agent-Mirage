"""CPU-only negative gates; no SSH, token, GPU or model access."""
import copy
from pathlib import Path
import unittest

import collect_ownership_transport as c


def fixture():
    cards = {str(i): 'GPU-' + str(i) for i in range(4, 8)}
    locks = [{'fd': i, 'path': '/task/lock' + str(i), 'inode': i + 10} for i in range(3, 12)]
    holder = {'pid': 1, 'uid': 1033, 'command': 'holder exact', 'start_ticks': '1'}
    state = {'phase': 'ready', 'active': None, 'next_run_index': 0, 'runs': {
        'run-' + str(i): {'status': 'not_started', 'last_decision_index': 0,
                         'calls': {'actor': 0, 'judge': 0, 'observe': 0}} for i in range(4)}}
    workers, launch = [], {}
    for role, pid in zip(c.ROLES, (3, 4)):
        identity = {'pid': pid, 'uid': 1033, 'command': 'python ' + role, 'start_ticks': str(pid)}
        value = {'role': role, 'stage': 'online_ready', 'phase': 'ready_gui', 'state': copy.deepcopy(state),
                 'exclusive_task_group': True, 'actual_allowed_pids': [3, 4], 'physical_gpu_uuids': cards}
        workers.append({'role': role, 'identity': identity, 'requests': [], 'held_locks': copy.deepcopy(locks), 'health': value})
        launch[role] = {'identity': identity, 'argv': ['python', role]}
    resources = {'exclusive_task_group': True, 'actual_allowed_pids': [3, 4], 'physical_gpu_uuids': cards}
    detail = {'time': 100, 'inspection': {'resources': resources, 'workers': workers, 'launcher': {'uid': 1033}},
              'holder': holder, 'expected_holder': dict(holder), 'holder_locks': locks,
              'launcher_locks': copy.deepcopy(locks), 'expected_locks': copy.deepcopy(locks),
              'physical_gpu_uuids': cards, 'launch_records': copy.deepcopy(launch),
              'compute_on_leased_GPUs': [{'pid': 3, 'uuid': u} for u in cards.values()] + [{'pid': 4, 'uuid': cards['7']}]}
    health = {'time': 100, 'primary': copy.deepcopy(workers[0]['health']), 'observer': copy.deepcopy(workers[1]['health']),
              'unauthenticated_rejected': True, 'actual_reverse_loopback_listeners': ['127.0.0.1:28427', '127.0.0.1:28423']}
    value = [{'role': role, 'stage': 'online_ready', 'phase': 'ready_gui', 'bearer_required': True} for role in c.ROLES]
    bridge = {'status': 'authenticated_transport_online_stage_only', 'inference_verified': False, 'GUI_run_ready': False,
              'authenticated_health': {'3090': copy.deepcopy(value), '4090': copy.deepcopy(value)}}
    return detail, health, bridge


class Tests(unittest.TestCase):
    def test_valid_exact_peers_locks_state_and_transport(self):
        cards, pids, runs = c.validate_sources(*fixture(), 101)
        self.assertEqual(pids, [3, 4]); self.assertEqual(len(cards), 4); self.assertEqual(len(runs), 4)

    def test_wrong_UID_command_or_start_time_rejected(self):
        for field, value in [('uid', 1006), ('command', 'different full command'), ('start_ticks', 'other')]:
            args = fixture(); args[0]['inspection']['workers'][0]['identity'] = {**args[0]['inspection']['workers'][0]['identity'], field: value}
            with self.assertRaises(AssertionError): c.validate_sources(*args, 101)

    def test_missing_lock_or_foreign_compute_rejected(self):
        for change in ('lock', 'foreign', 'escaped'):
            args = fixture()
            if change == 'lock': args[0]['inspection']['workers'][0]['held_locks'].pop()
            elif change == 'foreign': args[0]['compute_on_leased_GPUs'].append({'pid': 99, 'uuid': 'GPU-4'})
            else: args[0]['compute_on_leased_GPUs'].append({'pid': 4, 'uuid': 'GPU-5'})
            with self.assertRaises(AssertionError): c.validate_sources(*args, 101)

    def test_spent_or_active_run_and_preflight_health_rejected(self):
        for change in ('spent', 'active', 'preflight'):
            args = fixture(); health = args[1]['observer']
            if change == 'spent': health['state']['runs']['run-0']['calls']['actor'] = 1
            elif change == 'active': health['state']['active'] = 'run-0'
            else: health['phase'] = 'ready_preflight_only'
            with self.assertRaises(AssertionError): c.validate_sources(*args, 101)

    def test_stale_or_future_snapshot_and_nonloopback_rejected(self):
        for now in (99, 221):
            with self.assertRaises(AssertionError): c.validate_sources(*fixture(), now)
        args = fixture(); args[1]['actual_reverse_loopback_listeners'][0] = '0.0.0.0:28427'
        with self.assertRaises(AssertionError): c.validate_sources(*args, 101)

    def test_frozen_wrapper_fresh_guards_and_remote_source_syntax(self):
        path = c.BASE / 'policy-preparation/image-observer-policy/gui-once-wrapper-01/gui_once.py'
        result = c.validate_wrapper_fresh_guards(path, 'a2bc6313b807cd800d245428d77f50dd7449e970e2201c2d1a926dd7b230429f')
        self.assertTrue(result['both_health_endpoints_rechecked_before_child_spawn'])
        for source in (c.INSPECT_3090, c.HEALTH_4090, c.COPY_PROOF_4090): compile(source, '<remote-prepared>', 'exec')


if __name__ == '__main__': unittest.main(verbosity=2)
