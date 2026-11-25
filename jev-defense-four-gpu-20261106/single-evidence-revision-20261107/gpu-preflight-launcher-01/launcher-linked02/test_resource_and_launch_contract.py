"""CPU-only safety boundary controls. No /proc/GPU/network/model actions."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import resource_gate as gate
import launch_once as launch


def fixture():
    holder = {**launch.HOLDER, 'state': 'S'}
    worker = {'pid': 3000123, 'uid': 1033, 'start_ticks': '20000', 'state': 'R',
              'command': launch.PYTHON + ' -u ' + str(launch.PACKAGE / 'native_image_gpu_preflight.py')}
    parent = {'pid': 3000122, 'uid': 1033, 'start_ticks': '19999', 'state': 'S',
              'command': launch.PYTHON + ' ' + str(launch.PACKAGE / 'launch_once.py')}
    lease = {'holder': holder, 'gpu': [{'index': i, 'uuid': 'GPU-CPU-FIXTURE-' + str(i)} for i in [4, 5, 6, 7]]}
    paths = sorted(gate.expected_lock_paths(lease))
    lease['lock_records'] = [{'path': path, 'fd': i + 3, 'inode': 9000 + i} for i, path in enumerate(paths)]
    locks = [{**row, 'device': 2065, 'held_lock_lines': ['lock: 1: FLOCK ADVISORY WRITE 2568295 08:11:9000 0 EOF'],
              'fdinfo': 'CPU fixture; never actual proc evidence'} for row in lease['lock_records']]
    snapshot = {'holder_identity': holder, 'self_identity': worker,
                'actual_allowed_identities': {worker['pid']: worker, parent['pid']: parent},
                'holder_locks': copy.deepcopy(locks), 'self_locks': copy.deepcopy(locks),
                'inherited_fd_numbers': list(range(3, 12)), 'cuda_visible_devices': '7',
                'gpu': {'cards': {i: {'index': i, 'uuid': 'GPU-CPU-FIXTURE-' + str(i), 'free_mib': 24253} for i in [4, 5, 6, 7]},
                        'compute': []}, 'captured_unix': 0}
    allowed = {worker['pid']: worker, parent['pid']: parent}
    return lease, holder, allowed, snapshot


class ResourceBoundaries(unittest.TestCase):
    def setUp(self):
        self.lease, self.holder, self.allowed, self.snapshot = fixture()

    def check(self, empty=True, floor=23000):
        return gate.validate_snapshot(self.lease, self.holder, self.allowed, self.snapshot, empty, floor)

    def reject(self, empty=True, floor=23000):
        with self.assertRaises(gate.ResourceGateError):
            self.check(empty, floor)

    def test_valid_initial_empty_and_nine_inherited_locks(self):
        self.assertTrue(self.check()['owned_task_group'])

    def test_valid_worker_on_gpu7_after_load_does_not_require_empty_headroom(self):
        self.snapshot['gpu']['cards'][7]['free_mib'] = 2000
        self.snapshot['gpu']['compute'] = [{'pid': 3000123, 'uuid': 'GPU-CPU-FIXTURE-7'}]
        self.assertTrue(self.check(False)['owned_task_group'])

    def test_late_foreign_same_UID_compute_rejected(self):
        self.snapshot['gpu']['compute'] = [{'pid': 3000999, 'uuid': 'GPU-CPU-FIXTURE-7', 'uid': 1033}]
        self.reject(False)

    def test_registered_launcher_cannot_compute(self):
        self.snapshot['gpu']['compute'] = [{'pid': 3000122, 'uuid': 'GPU-CPU-FIXTURE-7'}]
        self.reject(False)

    def test_worker_cannot_escape_gpu7(self):
        self.snapshot['gpu']['compute'] = [{'pid': 3000123, 'uuid': 'GPU-CPU-FIXTURE-6'}]
        self.reject(False)

    def test_compute_preexisting_initial_load_rejected(self):
        self.snapshot['gpu']['compute'] = [{'pid': 3000123, 'uuid': 'GPU-CPU-FIXTURE-7'}]
        self.reject(True)

    def test_stale_holder_start_ticks_rejected(self):
        self.snapshot['holder_identity'] = {**self.holder, 'start_ticks': '99999'}
        self.reject()

    def test_stale_holder_full_command_rejected(self):
        self.snapshot['holder_identity'] = {**self.holder, 'command': 'unrelated same-user process'}
        self.reject()

    def test_registered_process_PID_reuse_rejected(self):
        self.snapshot['actual_allowed_identities'][3000122] = {**self.allowed[3000122], 'start_ticks': 'changed'}
        self.reject()

    def test_bare_PID_allowlist_rejected(self):
        self.allowed = [3000123, 3000122]
        self.reject()

    def test_missing_lock_FD_rejected(self):
        self.snapshot['self_locks'].pop()
        self.reject()

    def test_wrong_inherited_inode_rejected(self):
        self.snapshot['self_locks'][0]['inode'] += 1
        self.reject()

    def test_wrong_inherited_device_rejected(self):
        self.snapshot['self_locks'][0]['device'] += 1
        self.reject()

    def test_non_FLOCK_or_wrong_owner_rejected(self):
        for text in ['lock: 1: POSIX ADVISORY WRITE 2568295 08:11:9000 0 EOF',
                     'lock: 1: FLOCK ADVISORY WRITE 12345 08:11:9000 0 EOF']:
            with self.subTest(text=text):
                self.snapshot['self_locks'][0]['held_lock_lines'] = [text]
                self.reject()

    def test_duplicate_inherited_FDs_rejected(self):
        self.snapshot['inherited_fd_numbers'][-1] = self.snapshot['inherited_fd_numbers'][0]
        self.reject()

    def test_GPU_UUID_change_rejected(self):
        self.snapshot['gpu']['cards'][7]['uuid'] = 'GPU-CPU-OTHER'
        self.reject()

    def test_initial_floor_cannot_be_lowered(self):
        self.reject(floor=22999)

    def test_initial_low_free_rejected(self):
        self.snapshot['gpu']['cards'][6]['free_mib'] = 22999
        self.reject()

    def test_worker_visible_devices_expansion_rejected(self):
        self.snapshot['gpu']['compute'] = [{'pid': 3000123, 'uuid': 'GPU-CPU-FIXTURE-7'}]
        self.snapshot['cuda_visible_devices'] = '4,5,6,7'
        self.reject(False)

    def test_out_of_scope_foreign_compute_does_not_authorize_managing_it(self):
        self.snapshot['gpu']['compute'] = [{'pid': 42, 'uuid': 'GPU-FOREIGN-0'}]
        self.assertTrue(self.check()['owned_task_group'])


def spec_fixture():
    return {'schema': 'single-jev-image-four-control-launch-v1', 'approved_for_new_auxiliary_preflight': True,
            'launcher_source_sha256': 'a' * 64, 'resource_gate_source_sha256': 'b' * 64,
            'worker_source': {'path': str(launch.PACKAGE / 'native_image_gpu_preflight.py'), 'sha256': 'c' * 64},
            'manifest': {'path': str(launch.BASE / 'single-evidence-revision-20261107/frozen-gpu-manifest.json'), 'sha256': 'd' * 64},
            'lease': {'path': str(gate.LEASE_PATH), 'sha256': 'e' * 64},
            'expected_holder': dict(launch.HOLDER), 'python': launch.PYTHON,
            'output_root': str(launch.BASE / 'new-single-jev-image-preflight-01'), 'model': dict(launch.MODEL),
            'limits': {'initial_auxiliary_requests': 4, 'automatic_format_retries': 0,
                       'actual_total_auxiliary_requests': 4, 'overall_package_auxiliary_cap': 8,
                       'unused_format_allowance_automatically_spent': False, 'primary_requests': 0,
                       'GUI_actions': 0, 'scorer_calls': 0, 'physical_compute_GPUs': [7],
                       'reservation_GPUs': [4, 5, 6, 7], 'semantic_resampling': False}}


class LaunchContract(unittest.TestCase):
    def test_finite_new_worker_spec_valid(self):
        launch.validate_spec(spec_fixture())

    def test_unreviewed_spec_rejected(self):
        spec = spec_fixture()
        spec['approved_for_new_auxiliary_preflight'] = False
        with self.assertRaises(gate.ResourceGateError):
            launch.validate_spec(spec)

    def test_old_worker_or_primary_rejected(self):
        spec = spec_fixture()
        spec['worker_source']['path'] = str(launch.RUNTIME / 'preflight_service.py')
        with self.assertRaises(gate.ResourceGateError):
            launch.validate_spec(spec)

    def test_retry_or_budget_expansion_rejected(self):
        for key, value in [('automatic_format_retries', 1), ('actual_total_auxiliary_requests', 8), ('primary_requests', 1)]:
            spec = spec_fixture()
            spec['limits'][key] = value
            with self.subTest(key=key), self.assertRaises(gate.ResourceGateError):
                launch.validate_spec(spec)

    def test_path_traversal_rejected(self):
        spec = spec_fixture()
        spec['output_root'] = str(launch.BASE) + '/../../foreign-output'
        with self.assertRaises(gate.ResourceGateError):
            launch.validate_spec(spec)

    def test_persistent_once_only_claim_cannot_be_repeated(self):
        with tempfile.TemporaryDirectory() as d:
            path = launch.claim_once(Path(d) / 'claims', 'f' * 64, {'CPU_fixture': True})
            first = path.read_bytes()
            with self.assertRaises(FileExistsError):
                launch.claim_once(Path(d) / 'claims', 'f' * 64, {'CPU_fixture': 'duplicate'})
            self.assertEqual(first, path.read_bytes())

    def test_journal_hash_chain_binds_order_and_payload(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'journal.jsonl'
            j = launch.Journal(path)
            j.append('CPU_fixture_started', {'models': 0})
            j.append('CPU_fixture_complete', {'models': 0})
            j.close()
            rows = [json.loads(x) for x in path.read_text().splitlines()]
            previous = '0' * 64
            for i, row in enumerate(rows):
                digest = row.pop('sha256')
                self.assertEqual(i, row['index'])
                self.assertEqual(previous, row['previous_sha256'])
                self.assertEqual(digest, hashlib.sha256(launch.canonical(row)).hexdigest())
                previous = digest


if __name__ == '__main__':
    unittest.main(verbosity=2)
