"""New CPU controls for the two independent-review findings; no real queries."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import resource_gate as gate
import launch_once as launch
from test_resource_and_launch_contract import fixture


def fake_query(compute):
    def run(argv, **kwargs):
        if '--query-gpu=index,uuid,memory.free' in argv:
            raw = ''.join('%s, GPU-CPU-FIXTURE-%s, 24253\n' % (i, i) for i in [4, 5, 6, 7])
        else:
            raw = compute
        return SimpleNamespace(returncode=0, stdout=raw, stderr='')
    return run


class LinkedSafety(unittest.TestCase):
    def test_unrelated_compute_proc_is_not_read_and_raw_row_remains(self):
        with patch.object(gate.subprocess, 'run', side_effect=fake_query('GPU-OUTSIDE-0, 42, 1000\n')):
            with patch.object(gate, 'identity', side_effect=PermissionError('outside proc must not be read')) as call:
                value = gate.gpu_state()
        self.assertEqual(call.call_count, 0)
        self.assertEqual(value['compute'][0]['pid'], 42)
        self.assertTrue(value['compute'][0]['identity_not_required_outside_task_GPU_scope'])

    def test_unreadable_target_identity_is_preserved_then_refused(self):
        with patch.object(gate.subprocess, 'run', side_effect=fake_query('GPU-CPU-FIXTURE-7, 3000123, 1000\n')):
            with patch.object(gate, 'identity', side_effect=PermissionError('CPU target proc fixture')):
                value = gate.gpu_state()
        self.assertEqual(value['compute'][0]['identity_read_error']['type'], 'PermissionError')
        lease, holder, allowed, snapshot = fixture()
        snapshot['gpu'] = value
        with self.assertRaises(gate.ResourceGateError):
            gate.validate_snapshot(lease, holder, allowed, snapshot, False)

    def test_actual_compute_identity_mismatch_refused(self):
        lease, holder, allowed, snapshot = fixture()
        snapshot['gpu']['compute'] = [{'pid': 3000123, 'uuid': 'GPU-CPU-FIXTURE-7',
                                      'actual_identity': {**allowed[3000123], 'start_ticks': 'changed'}}]
        with self.assertRaises(gate.ResourceGateError):
            gate.validate_snapshot(lease, holder, allowed, snapshot, False)

    def test_resource_evidence_survives_failure_record(self):
        evidence = {'actual_identity': {'uid': 1001, 'command': 'CPU foreign process fixture'},
                    'fdinfo': 'CPU fixture held-lock evidence'}
        try:
            error = gate.ResourceGateError('CPU conflict fixture')
            error.resource_evidence = evidence
            raise error
        except gate.ResourceGateError as exc:
            record = launch.failure_record(exc)
        self.assertEqual(record['resource_evidence'], evidence)
        self.assertIn('CPU conflict fixture', record['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
