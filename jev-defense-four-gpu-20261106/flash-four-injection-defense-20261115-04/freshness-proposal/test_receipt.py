"""Protocol fixtures, not visual/model/GUI success evidence."""
import copy
import unittest
from capture_receipt import ReceiptGuard, sign_capture

KEY = b'CPU-proposal-fixture-only-key-00000000'


class ReceiptTests(unittest.TestCase):
    def receipt(self, image=b'captured-PNG-fixture', challenge='new', environment='live-A'):
        return sign_capture(KEY, image, challenge=challenge, environment_id=environment, capture_id='capture-id')

    def test_valid_receipt_only_proceeds_to_Flash(self):
        result = ReceiptGuard(KEY).check(b'captured-PNG-fixture', self.receipt(), challenge='new', environment_id='live-A')
        self.assertEqual((result.decision, result.reason), ('YES', 'capture_receipt_bound_proceed_to_Flash'))
        self.assertFalse(result.Flash_called)

    def test_old_signed_frame_does_not_answer_new_challenge(self):
        result = ReceiptGuard(KEY).check(b'captured-PNG-fixture', self.receipt(challenge='old'), challenge='new', environment_id='live-A')
        self.assertEqual((result.decision, result.reason), ('NO', 'old_or_other_capture_response'))

    def test_replaced_bytes_rejected_without_PRIVATE_labels(self):
        result = ReceiptGuard(KEY).check(b'replayed-or-blank-or-masked-image', self.receipt(), challenge='new', environment_id='live-A')
        self.assertEqual((result.decision, result.reason), ('NO', 'capture_bytes_replaced'))

    def test_receipt_hash_edit_invalidates_signature(self):
        receipt = copy.deepcopy(self.receipt())
        receipt['image_sha256'] = '0' * 64
        result = ReceiptGuard(KEY).check(b'captured-PNG-fixture', receipt, challenge='new', environment_id='live-A')
        self.assertEqual(result.reason, 'capture_signature_mismatch')

    def test_identical_pixels_from_a_new_trusted_capture_are_allowed(self):
        guard = ReceiptGuard(KEY)
        for challenge in ['first', 'second']:
            self.assertEqual(guard.check(b'captured-PNG-fixture', self.receipt(challenge=challenge),
                                         challenge=challenge, environment_id='live-A').decision, 'YES')

    def test_reused_response_not_accepted_twice(self):
        guard = ReceiptGuard(KEY)
        self.assertEqual(guard.check(b'captured-PNG-fixture', self.receipt(), challenge='new', environment_id='live-A').decision, 'YES')
        self.assertEqual(guard.check(b'captured-PNG-fixture', self.receipt(), challenge='new', environment_id='live-A').decision, 'NO')

    def test_other_live_environment_is_rejected(self):
        self.assertEqual(ReceiptGuard(KEY).check(b'captured-PNG-fixture', self.receipt(environment='live-B'),
                                                challenge='new', environment_id='live-A').decision, 'NO')

    def test_missing_image_or_receipt_rejected(self):
        for image, receipt in [(None, self.receipt()), (b'', self.receipt()), (b'captured-PNG-fixture', None)]:
            self.assertEqual(ReceiptGuard(KEY).check(image, receipt, challenge='new', environment_id='live-A').decision, 'NO')

    def test_bad_frame_signed_as_new_by_trusted_source_is_not_detected(self):
        image = b'bad-but-authentically-new-capture'
        self.assertEqual(ReceiptGuard(KEY).check(image, self.receipt(image=image), challenge='new', environment_id='live-A').decision, 'YES')


if __name__ == '__main__':
    unittest.main(verbosity=2)
