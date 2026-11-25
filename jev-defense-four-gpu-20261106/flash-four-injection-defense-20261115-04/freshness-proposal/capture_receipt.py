"""CPU-only proposal. Not imported by any current experiment or launcher.

Requires a trusted acquisition boundary that signs the original capture before
an untrusted delivery path. It cannot detect a bad image signed by that boundary.
No task/history, previous-image comparison or PRIVATE injection label is used.
"""
import hashlib
import hmac
import json
from dataclasses import dataclass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sign_capture(key, png, *, challenge, environment_id, capture_id):
    if len(key) < 32 or not isinstance(png, bytes) or not png:
        raise ValueError('Trusted key and complete captured bytes required')
    body = {'challenge': challenge, 'environment_id': environment_id,
            'capture_id': capture_id, 'image_sha256': hashlib.sha256(png).hexdigest()}
    return {**body, 'signature': hmac.new(key, canonical(body), hashlib.sha256).hexdigest()}


@dataclass(frozen=True)
class Result:
    decision: str
    reason: str
    source: str = 'capture_receipt_proposal'
    Flash_called: bool = False
    not_a_model_NO: bool = True


class ReceiptGuard:
    def __init__(self, key):
        if len(key) < 32:
            raise ValueError('Trusted verification key required')
        self.key = key
        self.claimed = set()  # Production needs atomic persistent claims, not this CPU set.

    def check(self, png, receipt, *, challenge, environment_id):
        if png is None or png == b'':
            return Result('NO', 'missing_image')
        fields = {'challenge', 'environment_id', 'capture_id', 'image_sha256', 'signature'}
        if not isinstance(receipt, dict) or set(receipt) != fields:
            return Result('NO', 'missing_or_invalid_capture_receipt')
        body = {k: v for k, v in receipt.items() if k != 'signature'}
        if any(not isinstance(v, str) or not v for v in receipt.values()):
            return Result('NO', 'invalid_receipt_types')
        expected = hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(receipt['signature'], expected):
            return Result('NO', 'capture_signature_mismatch')
        if receipt['challenge'] != challenge or receipt['environment_id'] != environment_id:
            return Result('NO', 'old_or_other_capture_response')
        if challenge in self.claimed:
            return Result('NO', 'capture_challenge_already_used')
        if not isinstance(png, bytes) or hashlib.sha256(png).hexdigest() != receipt['image_sha256']:
            return Result('NO', 'capture_bytes_replaced')
        self.claimed.add(challenge)
        return Result('YES', 'capture_receipt_bound_proceed_to_Flash')
