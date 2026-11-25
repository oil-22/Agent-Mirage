"""New capture protocol: public-key verification and atomic persistent challenges.

The receiver has no signing key and never reads acquisition-side reference PNGs.
Same pixels in a newly acquired, correctly bound receipt are allowed.
"""
import hashlib
import json
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PROTOCOL = 'trusted-native-capture-ed25519-v1'
BODY_FIELDS = {'protocol', 'session_id', 'environment_id', 'capture_id', 'challenge',
               'action_sequence', 'capture_index', 'acquired_at_ns', 'image_sha256',
               'source_code_sha256', 'key_id'}
FIELDS = BODY_FIELDS | {'signature'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ReceiptDecision:
    value: str
    reason: str
    source: str = 'trusted_capture_receipt'
    Flash_called: bool = False
    not_a_model_NO: bool = True


class ReceiptVerifier:
    def __init__(self, path, *, public_key, session_id, environment_id, source_code_sha256):
        self.path = Path(path)
        self.public_key = bytes.fromhex(public_key)
        self.key = Ed25519PublicKey.from_public_bytes(self.public_key)
        self.binding = {'public_key': public_key, 'session_id': session_id,
                        'environment_id': environment_id, 'source_code_sha256': source_code_sha256}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS binding (id INTEGER PRIMARY KEY CHECK(id=1), value BLOB NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS challenges (challenge TEXT PRIMARY KEY, sequence INTEGER NOT NULL, issued_ns INTEGER NOT NULL, state TEXT NOT NULL, reason TEXT, closed_ns INTEGER)')
            db.execute('INSERT OR IGNORE INTO binding VALUES(1,?)', (canonical(self.binding),))
            if db.execute('SELECT value FROM binding WHERE id=1').fetchone()[0] != canonical(self.binding):
                raise ValueError('Persistent verifier identity changed')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20, isolation_level='IMMEDIATE')
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('PRAGMA journal_mode=WAL')
            with db:
                yield db
        finally:
            db.close()

    def issue(self, action_sequence):
        if type(action_sequence) is not int or action_sequence < 0:
            raise ValueError('Native action sequence required')
        request = {'challenge': secrets.token_hex(32), 'environment_id': self.binding['environment_id'],
                   'action_sequence': action_sequence}
        with self.connect() as db:
            db.execute('INSERT INTO challenges VALUES(?,?,?,\'pending\',NULL,NULL)',
                       (request['challenge'], action_sequence, time.time_ns()))
        return request

    def check(self, png, receipt, *, expected):
        challenge = expected['challenge']
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT sequence,issued_ns,state FROM challenges WHERE challenge=?', (challenge,)).fetchone()
            if row is None:
                return ReceiptDecision('NO', 'unknown_capture_challenge')
            if row[2] != 'pending':
                return ReceiptDecision('NO', 'capture_challenge_already_closed')
            reason = self.validate(png, receipt, expected, row)
            decision = 'YES' if reason == 'receipt_bound_proceed_to_Flash' else 'NO'
            db.execute('UPDATE challenges SET state=?,reason=?,closed_ns=? WHERE challenge=? AND state=\'pending\'',
                       ('accepted' if decision == 'YES' else 'rejected', reason, time.time_ns(), challenge))
        return ReceiptDecision(decision, reason, not_a_model_NO=decision == 'NO')

    def validate(self, png, receipt, expected, row):
        if not isinstance(png, bytes) or not png:
            return 'missing_image'
        if not isinstance(receipt, dict) or set(receipt) != FIELDS:
            return 'missing_or_invalid_capture_receipt'
        for field in FIELDS - {'action_sequence', 'capture_index', 'acquired_at_ns'}:
            if not isinstance(receipt[field], str) or not receipt[field]:
                return 'invalid_receipt_types'
        for field in ['action_sequence', 'capture_index', 'acquired_at_ns']:
            if type(receipt[field]) is not int or receipt[field] < 0:
                return 'invalid_receipt_types'
        if any(not re.fullmatch('[0-9a-f]{64}', receipt[k]) for k in ['challenge', 'image_sha256', 'source_code_sha256', 'key_id']):
            return 'invalid_receipt_encoding'
        try:
            signature = bytes.fromhex(receipt['signature'])
            body = {k: receipt[k] for k in BODY_FIELDS}
            self.key.verify(signature, canonical(body))
        except (ValueError, InvalidSignature):
            return 'capture_signature_mismatch'
        if receipt['protocol'] != PROTOCOL or receipt['key_id'] != digest(self.public_key):
            return 'other_capture_protocol_or_key'
        if any(receipt[k] != self.binding[k] for k in ['session_id', 'environment_id', 'source_code_sha256']):
            return 'other_capture_source_or_environment'
        if (receipt['challenge'] != expected['challenge'] or
                expected['environment_id'] != self.binding['environment_id'] or
                receipt['action_sequence'] != expected['action_sequence'] or row[0] != expected['action_sequence']):
            return 'old_or_other_capture_response'
        # Both trusted processes use the same machine's clock; nonce binding is
        # the freshness evidence. Do not infer age from image content or hashes.
        if receipt['acquired_at_ns'] < row[1]:
            return 'capture_predates_issued_challenge'
        if digest(png) != receipt['image_sha256']:
            return 'capture_bytes_replaced'
        return 'receipt_bound_proceed_to_Flash'

    def close_missing(self, expected):
        return self.check(None, None, expected=expected)
