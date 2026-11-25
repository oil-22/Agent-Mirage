"""CPU safety/control-flow fixtures only; no models, GPU or semantic pass claims."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from four_gpu_contract import (FLASH, FLASH_REVISION, canonical, digest, identity_matches,
                               primary_device_map, request_fingerprint,
                               validate_actor, validate_admission,
                               validate_decision, validate_frozen_wire,
                               validate_layout, validate_probabilities,
                               validate_resource_group, validate_observation)
from preflight_service import verify_flash_checkpoint, validate_native_state_records
import launch_preflight_group as launcher


def identity(pid=20, command='python approved.py', start='100'):
    return {'pid': pid, 'uid': 1033, 'command': command, 'start_ticks': start}


class Contract(unittest.TestCase):
    def setUp(self):
        self.layout = json.loads(Path(__file__).with_name('layout.proposed.json').read_bytes())
        self.lease = {'gpu': [{'index': i, 'uuid': 'gpu' + str(i)} for i in range(4, 8)]}
        self.workers = [{'role': 'primary', 'identity': identity()},
                        {'role': FLASH, 'identity': identity(21, 'python flash.py')}]
        self.actual = {row['identity']['pid']: row['identity'] for row in self.workers}
        self.compute = [{'uuid': 'gpu4', 'pid': 20}, {'uuid': 'gpu7', 'pid': 20},
                        {'uuid': 'gpu7', 'pid': 21}]

    def test_reviewed_asymmetric_budgets(self):
        self.assertEqual(validate_layout(self.layout), {0: '20GiB', 1: '20GiB', 2: '20GiB', 3: '8GiB'})

    def test_other_physical_gpu_refused(self):
        self.layout['physical_gpus'] = [0, 1, 2, 3]
        with self.assertRaises(ValueError): validate_layout(self.layout)

    def test_large_primary_on_flash_card_refused(self):
        self.layout['primary_max_memory_gib'][-1] = 20
        with self.assertRaises(ValueError): validate_layout(self.layout)

    def test_precision_and_fast_path_changes_refused(self):
        for key, value in [('primary_dtype', 'float16'), ('flash_fast', True), ('primary_attention', 'eager')]:
            row = copy.deepcopy(self.layout); row[key] = value
            with self.assertRaises(ValueError): validate_layout(row)

    def test_all64_layers_once_onfour_devices(self):
        mapping = primary_device_map()
        layers = [mapping['model.language_model.layers.' + str(i)] for i in range(64)]
        self.assertEqual([layers.count(i) for i in range(4)], [18, 20, 20, 6])
        self.assertEqual(mapping['lm_head'], 3)
        self.assertEqual(mapping['model.visual'], 0)

    def test_owned_coordinated_share_admitted(self):
        result = validate_resource_group(self.lease, self.workers, self.actual, self.compute)
        self.assertTrue(result['exclusive_task_group'])

    def test_foreign_on_task_gpu_refused(self):
        self.compute.append({'uuid': 'gpu5', 'pid': 99})
        with self.assertRaises(ValueError): validate_resource_group(self.lease, self.workers, self.actual, self.compute)

    def test_unrelated_same_user_is_not_allowed(self):
        self.actual[99] = identity(99)
        self.compute.append({'uuid': 'gpu5', 'pid': 99})
        with self.assertRaises(ValueError): validate_resource_group(self.lease, self.workers, self.actual, self.compute)

    def test_foreign_other_gpu_untouched(self):
        self.compute.append({'uuid': 'gpu0', 'pid': 99})
        self.assertTrue(validate_resource_group(self.lease, self.workers, self.actual, self.compute)['exclusive_task_group'])

    def test_pid_reuse_and_full_command_mismatch_refused(self):
        for change in [{'start_ticks': '101'}, {'command': 'python unrelated.py'}, {'uid': 1006}]:
            actual = copy.deepcopy(self.actual); actual[20].update(change)
            with self.assertRaises(ValueError): validate_resource_group(self.lease, self.workers, actual, self.compute)

    def test_dead_peer_or_missing_identity_not_running_flag(self):
        self.actual.pop(21)
        with self.assertRaises(ValueError): validate_resource_group(self.lease, self.workers, self.actual, self.compute)

    def test_flash_cannot_compute_on_primary_other_cards(self):
        self.compute.append({'uuid': 'gpu4', 'pid': 21})
        with self.assertRaises(ValueError): validate_resource_group(self.lease, self.workers, self.actual, self.compute)

    def test_duplicate_worker_role_refused(self):
        self.workers.append({'role': 'primary', 'identity': identity(22)})
        self.actual[22] = identity(22)
        with self.assertRaises(ValueError): validate_resource_group(self.lease, self.workers, self.actual, self.compute)

    def test_identity_requires_command_and_starttime(self):
        self.assertTrue(identity_matches(identity(), identity()))
        self.assertFalse(identity_matches(identity(), identity(start='101')))

    def admission(self, body):
        raw = canonical(body)
        plan = {'mode': 'preflight', 'max_new_calls': 1,
                'requests': [{'case_id': 'one', 'fingerprint': request_fingerprint(body),
                              'wire_sha256': digest(raw)}]}
        return raw, validate_admission(plan)

    def test_full_frozen_wire_accepted(self):
        body = {'request_id': 'one', 'state': 'unchanged', 'options': {'a': 'A', 'b': 'B'}}
        raw, allowed = self.admission(body)
        self.assertEqual(validate_frozen_wire(raw, json.loads(raw), allowed), request_fingerprint(body))

    def test_same_content_reordered_native_options_refused(self):
        body = {'request_id': 'one', 'options': {'a': 'A', 'b': 'B'}}
        raw, allowed = self.admission(body)
        changed = {'request_id': 'one', 'options': {'b': 'B', 'a': 'A'}}
        self.assertEqual(request_fingerprint(body), request_fingerprint(changed))
        with self.assertRaises(ValueError): validate_frozen_wire(json.dumps(changed).encode(), changed, allowed)

    def test_transport_id_change_cannot_create_new_call(self):
        body = {'request_id': 'one', 'state': 'frozen'}
        raw, allowed = self.admission(body)
        body['request_id'] = 'different'
        with self.assertRaises(ValueError): validate_frozen_wire(canonical(body), body, allowed)

    def test_wire_sha_is_required(self):
        with self.assertRaises(ValueError):
            validate_admission({'mode': 'preflight', 'max_new_calls': 1,
                                'requests': [{'fingerprint': '0' * 64}]})

    def test_gui_mode_is_refused(self):
        with self.assertRaises(ValueError): validate_admission({'mode': 'gui', 'max_new_calls': 1, 'requests': []})

    def test_resident_peer_admits_zero_requests(self):
        self.assertEqual(validate_admission({'mode': 'resident_only', 'max_new_calls': 0,
                                            'GUI_actions': 0, 'requests': []}), {})

    def test_resident_peer_cannot_reopen_completed_controls(self):
        for cap, rows in [(1, []), (0, [{'fingerprint': '0' * 64}]), (False, [])]:
            with self.assertRaises(ValueError): validate_admission({'mode': 'resident_only',
                'max_new_calls': cap, 'GUI_actions': 0, 'requests': rows})

    def test_actor2048_original_options_enforced(self):
        body = {'operation': 'actor', 'body': {'max_tokens': 2048, 'temperature': 0,
                'chat_template_kwargs': {'enable_thinking': False}, 'messages': []}}
        validate_actor(body)
        body['body']['max_tokens'] = 1024
        with self.assertRaises(ValueError): validate_actor(body)

    def test_unknown_is_only_an_option_not_an_automatic_decision(self):
        body = {'state': 'image only', 'question': 'Visible?',
                'options': {'visible': 'visible', 'unknown': 'unknown'}}
        validate_decision(body)
        validate_probabilities({'visible': .2, 'unknown': .8}, body['options'], 'unknown')

    def test_invalid_probabilities_rejected(self):
        for probabilities in [{'a': float('nan'), 'b': 0}, {'a': .7, 'b': .7}, {'a': True, 'b': 0}]:
            with self.assertRaises(ValueError): validate_probabilities(probabilities, {'a': None, 'b': None}, 'a')

    def test_false_nonmaximal_choice_rejected(self):
        with self.assertRaises(ValueError): validate_probabilities({'a': .1, 'b': .9}, {'a': None, 'b': None}, 'a')

    def observer(self):
        contract = {'state': 'Only describe this image.', 'questions': {
            key: {'type': 'choice', 'instructions': 'What is visible?',
                  'criteria': {'a': 'One appearance', 'unknown': 'Cannot determine'}}
            for key in ['appearance', 'layout', 'readability']}}
        body = {'request_id': 'frozen', 'image_base64': 'AA==', 'image_sha256': 'x',
                'state': contract['state'], 'questions': copy.deepcopy(contract['questions']),
                'provenance': {'observation_id': 'one', 'image_sha256': 'x'}}
        return body, contract

    def test_fixed_neutral_image_observer_is_admitted(self):
        body, contract = self.observer()
        validate_observation(body, contract)

    def test_task_history_candidate_cannot_be_observer_inputs(self):
        body, contract = self.observer()
        for key in ['task', 'history', 'candidate', 'injection_label', 'query_key']:
            changed = copy.deepcopy(body); changed[key] = 'extra context'
            with self.assertRaises(ValueError): validate_observation(changed, contract)

    def test_provenance_cannot_smuggle_task_text(self):
        body, contract = self.observer()
        body['provenance']['task'] = 'Find a suit'
        with self.assertRaises(ValueError): validate_observation(body, contract)

    def test_observer_state_or_question_cannot_change_per_task(self):
        body, contract = self.observer()
        body['state'] += ' Locate Keyword focus.'
        with self.assertRaises(ValueError): validate_observation(body, contract)
        body, contract = self.observer()
        body['questions']['appearance']['instructions'] = 'Find a suit.'
        with self.assertRaises(ValueError): validate_observation(body, contract)

    def test_joint_question_order_and_exact_three_are_bound(self):
        body, contract = self.observer()
        body['questions'] = dict(reversed(list(body['questions'].items())))
        with self.assertRaises(ValueError): validate_observation(body, contract)


class CheckpointIdentity(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.model = self.root / 'checkpoint'
        source = self.model / 'source/src/pplx_decider/model.py'
        source.parent.mkdir(parents=True)
        source.write_text('# pinned source\n', encoding='utf8')
        (self.model / 'model.safetensors').write_bytes(b'weight-fixture')
        self.files = []
        for path in self.model.rglob('*'):
            if path.is_file():
                stamp = path.stat()
                self.files.append({'file': path.relative_to(self.model).as_posix(),
                    'bytes': stamp.st_size, 'sha256': digest(path.read_bytes()),
                    'stat': {'dev': stamp.st_dev, 'ino': stamp.st_ino,
                             'size': stamp.st_size, 'mtime_ns': stamp.st_mtime_ns}})
        self.completion = self.root / 'complete.json'
        self.stable = self.root / 'identity.json'
        self.completion_value = {'status': 'complete', 'revision': FLASH_REVISION,
            'checkpoint': str(self.model),
            'files': [{k: v for k, v in row.items() if k != 'stat'} for row in self.files]}
        self.completion.write_bytes(canonical(self.completion_value))
        self.stable_value = {'status': 'identity_bound', 'revision': FLASH_REVISION,
            'checkpoint': str(self.model), 'completion_receipt': str(self.completion),
            'completion_receipt_sha256': digest(self.completion.read_bytes()), 'files': self.files}
        self.config = {'flash_model': str(self.model), 'flash_identity_receipt': str(self.completion),
            'flash_identity_receipt_sha256': digest(self.completion.read_bytes()),
            'flash_stable_identity_receipt': str(self.stable)}
        self.seal_stable()

    def seal_stable(self):
        self.stable.write_bytes(canonical(self.stable_value))
        self.config['flash_stable_identity_receipt_sha256'] = digest(self.stable.read_bytes())

    def test_actual_checkpoint_matches_pinned_completion_and_stable_stats(self):
        self.assertEqual(verify_flash_checkpoint(self.config)['file_count'], 2)

    def test_changed_actual_weight_after_complete_is_refused(self):
        (self.model / 'model.safetensors').write_bytes(b'changed-weight')
        with self.assertRaises(RuntimeError): verify_flash_checkpoint(self.config)

    def test_unlisted_native_source_is_refused(self):
        (self.model / 'source/src/pplx_decider/extra.py').write_text('# extra', encoding='utf8')
        with self.assertRaises(RuntimeError): verify_flash_checkpoint(self.config)

    def test_resealed_wrong_source_hash_is_refused(self):
        row = next(row for row in self.stable_value['files'] if row['file'].endswith('.py'))
        row['sha256'] = '0' * 64
        self.seal_stable()
        with self.assertRaises(RuntimeError): verify_flash_checkpoint(self.config)

    def test_receipt_chain_cannot_rebind_other_checkpoint(self):
        self.stable_value['completion_receipt_sha256'] = '0' * 64
        self.seal_stable()
        with self.assertRaises(RuntimeError): verify_flash_checkpoint(self.config)

    def test_revision_and_complete_state_are_required(self):
        self.stable_value['status'] = 'pending'
        self.seal_stable()
        with self.assertRaises(RuntimeError): verify_flash_checkpoint(self.config)


class NativeStateBinding(unittest.TestCase):
    def setUp(self):
        self.expected = [{'name': 'model.layer.weight', 'shape': [2, 3],
            'dtype': 'torch.bfloat16', 'device': 'meta', 'bytes': 12}]
        self.actual = [{**self.expected[0], 'device': 'cuda:0'}]

    def test_realized_cuda_layout_matches_meta_shapes_without_mtp(self):
        self.assertTrue(validate_native_state_records(self.actual, self.expected)['native_MTP_not_instantiated'])

    def test_unknown_or_mtp_runtime_tensor_is_never_ignored(self):
        for name in ['mtp.fc.weight', 'unknown.weight']:
            rows = [*self.actual, {**self.actual[0], 'name': name}]
            with self.assertRaises(RuntimeError): validate_native_state_records(rows, self.expected)

    def test_cpu_or_wrong_shape_or_precision_is_rejected(self):
        for change in [{'device': 'cpu'}, {'shape': [3, 2]}, {'dtype': 'torch.float32'}, {'bytes': 24}]:
            rows = [{**self.actual[0], **change}]
            with self.assertRaises(RuntimeError): validate_native_state_records(rows, self.expected)


class ControlledStop(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'primary/requests').mkdir(parents=True)
        process = Mock(pid=20); process.poll.return_value = None
        self.child = {'role': 'primary', 'process': process, 'identity': identity(),
                      'log': self.root / 'primary.log', 'stop_requested_at': 0}
        self.child['log'].write_text('sealed idle log', encoding='utf8')

    def ready(self): (self.root / 'primary/ready.json').write_text('{}', encoding='utf8')

    def test_normal_stop_only_writes_marker_without_worker_signal(self):
        self.child.pop('stop_requested_at')
        with patch.object(launcher, 'identity', return_value=identity()), patch.object(launcher.os, 'kill') as kill:
            launcher.stop_owned([self.child]); kill.assert_not_called()
        self.assertTrue((self.root / 'stop-requested.json').exists())
        self.assertIn('stop_requested_at', self.child)

    def test_loading_is_never_assumed_idle_and_forced(self):
        with patch.object(launcher.time, 'monotonic', return_value=100), patch.object(launcher.os, 'kill') as kill:
            launcher.progress_owned_stop([self.child]); kill.assert_not_called()

    def test_pending_native_request_is_never_forced(self):
        self.ready(); (self.root / 'primary/requests/pending').mkdir()
        with patch.object(launcher.time, 'monotonic', return_value=100), patch.object(launcher.os, 'kill') as kill:
            launcher.progress_owned_stop([self.child]); kill.assert_not_called()

    def test_reused_identity_is_never_signalled(self):
        self.ready()
        with patch.object(launcher.time, 'monotonic', return_value=100), \
                patch.object(launcher, 'identity', return_value=identity(start='999')), \
                patch.object(launcher.os, 'kill') as kill:
            with self.assertRaises(RuntimeError): launcher.progress_owned_stop([self.child])
            kill.assert_not_called()

    def test_exact_idle_peer_is_snapshotted_before_bounded_force(self):
        self.ready()
        with patch.object(launcher.time, 'monotonic', return_value=100), \
                patch.object(launcher, 'identity', return_value=identity()), \
                patch.object(launcher.signal, 'SIGKILL', 9, create=True), \
                patch.object(launcher.os, 'kill') as kill:
            launcher.progress_owned_stop([self.child]); kill.assert_called_once_with(20, 9)
        snapshot = Path(self.child['force_snapshot'])
        self.assertTrue((snapshot / 'snapshot-sha256.json').exists())
        self.assertTrue((self.root / 'controlled-idle-stop-primary-9.json').exists())


if __name__ == '__main__':
    unittest.main()
