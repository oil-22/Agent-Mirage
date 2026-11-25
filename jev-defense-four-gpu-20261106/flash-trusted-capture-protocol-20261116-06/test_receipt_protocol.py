"""New protocol controls, including races/restart and honest signed-bad boundary."""
import copy
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from receipt_protocol import PROTOCOL, ReceiptVerifier, canonical, digest


class ProtocolControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.binding = {'public_key': self.public.hex(), 'session_id': 'session', 'environment_id': 'live-environment',
                        'source_code_sha256': '1' * 64}
        self.path = Path(self.tmp.name) / 'ledger.sqlite3'
        self.guard = ReceiptVerifier(self.path, **self.binding)
        self.png = b'original image bytes; semantics are outside the receipt verifier'

    def signed(self, expected, png=None, **changes):
        body = {'protocol': PROTOCOL, 'session_id': 'session', 'environment_id': 'live-environment',
                'capture_id': 'capture', 'challenge': expected['challenge'], 'action_sequence': expected['action_sequence'],
                'capture_index': 1, 'acquired_at_ns': time.time_ns(), 'image_sha256': digest(self.png if png is None else png),
                'source_code_sha256': '1' * 64, 'key_id': digest(self.public), **changes}
        return {**body, 'signature': self.key.sign(canonical(body)).hex()}

    def check(self, mutate=None, png=None):
        expected = self.guard.issue(0)
        receipt = self.signed(expected)
        if mutate:
            receipt = mutate(receipt)
        return self.guard.check(self.png if png is None else png, receipt, expected=expected)

    def test_01_original_capture_accepted(self):
        self.assertEqual(self.check().value, 'YES')

    def test_02_replaced_bytes_rejected(self):
        self.assertEqual(self.check(png=b'old different image').reason, 'capture_bytes_replaced')

    def test_03_invalid_signature_rejected(self):
        self.assertEqual(self.check(lambda r: {**r, 'signature': '00' * 64}).reason, 'capture_signature_mismatch')

    def test_04_no_receipt(self):
        e = self.guard.issue(0)
        self.assertEqual(self.guard.check(self.png, None, expected=e).value, 'NO')

    def test_05_old_receipt_new_challenge(self):
        old = self.signed(self.guard.issue(0))
        self.assertEqual(self.guard.check(self.png, old, expected=self.guard.issue(0)).reason, 'old_or_other_capture_response')

    def test_06_receipt_cannot_be_reused(self):
        e = self.guard.issue(0)
        r = self.signed(e)
        self.assertEqual(self.guard.check(self.png, r, expected=e).value, 'YES')
        self.assertEqual(self.guard.check(self.png, r, expected=e).reason, 'capture_challenge_already_closed')

    def test_07_restart_preserves_consumption(self):
        e = self.guard.issue(0)
        r = self.signed(e)
        self.guard.check(self.png, r, expected=e)
        restarted = ReceiptVerifier(self.path, **self.binding)
        self.assertEqual(restarted.check(self.png, r, expected=e).value, 'NO')

    def test_08_new_capture_same_pixels_allowed(self):
        for _ in range(2):
            e = self.guard.issue(0)
            self.assertEqual(self.guard.check(self.png, self.signed(e), expected=e).value, 'YES')

    def test_09_atomic_race_allows_exactly_one(self):
        e = self.guard.issue(0)
        r = self.signed(e)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.guard.check(self.png, r, expected=e).value, range(8)))
        self.assertEqual(results.count('YES'), 1)

    def test_10_rejected_challenge_is_closed(self):
        e = self.guard.issue(0)
        r = self.signed(e)
        self.guard.check(b'replaced', r, expected=e)
        self.assertEqual(self.guard.check(self.png, r, expected=e).value, 'NO')

    def test_11_other_environment(self):
        e = self.guard.issue(0)
        self.assertEqual(self.guard.check(self.png, self.signed(e, environment_id='foreign'), expected=e).reason, 'other_capture_source_or_environment')

    def test_12_other_action_sequence(self):
        e = self.guard.issue(1)
        self.assertEqual(self.guard.check(self.png, self.signed(e, action_sequence=0), expected=e).reason, 'old_or_other_capture_response')

    def test_13_changed_key_cannot_open_ledger(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        with self.assertRaises(ValueError):
            ReceiptVerifier(self.path, **{**self.binding, 'public_key': other.hex()})

    def test_14_extra_fields_rejected(self):
        self.assertEqual(self.check(lambda r: {**r, 'task': 'hidden task'}).value, 'NO')

    def test_15_missing_image(self):
        e = self.guard.issue(0)
        self.assertEqual(self.guard.check(None, None, expected=e).reason, 'missing_image')

    def test_16_source_signed_bad_image_is_not_detected(self):
        e = self.guard.issue(0)
        bad = b'authentically captured blank or masked screenshot'
        self.assertEqual(self.guard.check(bad, self.signed(e, bad), expected=e).value, 'YES')

    def test_17_prechallenge_capture_rejected(self):
        e = self.guard.issue(0)
        self.assertEqual(self.guard.check(self.png, self.signed(e, acquired_at_ns=1), expected=e).reason, 'capture_predates_issued_challenge')

    def test_18_wrong_source_program(self):
        e = self.guard.issue(0)
        self.assertEqual(self.guard.check(self.png, self.signed(e, source_code_sha256='2' * 64), expected=e).value, 'NO')

    def test_19_bool_not_action_integer(self):
        self.assertEqual(self.check(lambda r: {**r, 'action_sequence': False}).reason, 'invalid_receipt_types')

    def test_20_duplicate_RPC_fields_rejected(self):
        from native_rpc import loads
        with self.assertRaises(ValueError):
            loads(b'{"op":"capture","op":"sign"}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
