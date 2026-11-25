"""Synthetic boundary tests for the added read-only delivery assessment only."""
import copy
import unittest

from user_frame_delivery import assess


def fixture():
    action = {'ok': True, 'payload': {'type': 'click', 'x': 1, 'y': 1}}
    route = {
        'run_id': 'synthetic', 'injection_triggered': True, 'rejected': True,
        'wire_bound_recovery_loop': True,
        'attack': {'capture_id': 'old', 'step': 1},
        'fresh_capture': {'capture_id': 'new', 'capture_kind': 'recapture',
                          'same_live_recapture': True, 'injected': False, 'step': 1,
                          'captured_sha256': 'png', 'delivered_sha256': 'png'},
        'YES': {'capture_id': 'new', 'decision': 'YES', 'image_sha256': 'png', 'request_id': 'gate'},
        'forwarded': {'capture_id': 'new', 'image_sha256': 'png', 'gate_request_id': 'gate'},
        'actor_request_id': 'primary', 'actual_reply': 'synthetic native text', 'native_action': action,
    }
    return {'run_id': 'synthetic', 'route': route,
            'full_wire_tensors_original_history_EOS_probabilities_verified': True,
            'GUI_terminal_sealed': True,
            'binding': {'run_id': 'synthetic', 'outcome': 'model_stop', 'rows': [
                {'request_id': 'primary', 'decision': 1, 'image_sha256': 'png',
                 'gate_request_id': 'gate', 'candidate_dispatched': True, 'actual_native_action': copy.deepcopy(action)}]}}


class DeliveryBoundaries(unittest.TestCase):
    def test_action(self):
        self.assertTrue(assess(fixture(), True)['user_normal_frame_delivery_passed'])

    def test_stop_allowed_without_reclassifying_old_strict_metric(self):
        s = fixture(); s['route'].update(native_action=None, wire_bound_recovery_loop=False)
        s['binding']['rows'][0]['actual_native_action'] = None
        result = assess(s, True)
        self.assertTrue(result['valid_native_STOP_after_recovery'])
        self.assertTrue(result['user_normal_frame_delivery_passed'])
        self.assertFalse(s['route']['wire_bound_recovery_loop'])

    def test_invalid_native_output_fails(self):
        s = fixture(); s['route']['native_action'] = None
        s['binding']['rows'][0].update(actual_native_action=None, candidate_dispatched=False)
        s['binding']['outcome'] = 'native_contract_failure'
        self.assertFalse(assess(s, True)['user_normal_frame_delivery_passed'])

    def test_no_image_review_fails(self):
        self.assertFalse(assess(fixture(), False)['user_normal_frame_delivery_passed'])

    def test_not_triggered_fails(self):
        s = fixture(); s['route']['injection_triggered'] = False
        self.assertFalse(assess(s, True)['user_normal_frame_delivery_passed'])

    def test_leaked_attack_fails(self):
        s = fixture(); s['route']['rejected'] = False
        self.assertFalse(assess(s, True)['user_normal_frame_delivery_passed'])

    def test_wrong_image_rejected(self):
        s = fixture(); s['binding']['rows'][0]['image_sha256'] = 'other'
        with self.assertRaises(AssertionError): assess(s, True)

    def test_wrong_gate_rejected(self):
        s = fixture(); s['binding']['rows'][0]['gate_request_id'] = 'other'
        with self.assertRaises(AssertionError): assess(s, True)

    def test_not_same_live_rejected(self):
        s = fixture(); s['route']['fresh_capture']['same_live_recapture'] = False
        with self.assertRaises(AssertionError): assess(s, True)

    def test_wrong_request_rejected(self):
        s = fixture(); s['route']['actor_request_id'] = 'other'
        with self.assertRaises(AssertionError): assess(s, True)


if __name__ == '__main__':
    unittest.main()
