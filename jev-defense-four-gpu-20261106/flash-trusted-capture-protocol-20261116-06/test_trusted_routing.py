"""Controller wiring tests with synthetic bytes and stub model, zero inference."""
import ast
import json
import re
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from gate_core import Frame, ImageGate, GateController, Journal, Decision, NativeHistoryActor
from receipt_protocol import PROTOCOL, ReceiptVerifier, canonical, digest

P = Path(__file__).resolve().parent
ROOT = Path(json.loads((P / 'preparation-current.json').read_bytes())['package'])


class Checker:
    def __init__(self, decisions=('YES',)):
        self.inputs = []
        self.decisions = iter(decisions)

    def decide(self, png):
        self.inputs.append(png)
        return Decision(next(self.decisions), digest(png), uuid.uuid4().hex, 'pinned', 'contract')


class RoutingControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = Ed25519PrivateKey.generate()
        pub = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.pub = pub
        self.guard = ReceiptVerifier(self.root / 'ledger.sqlite3', public_key=pub.hex(), session_id='s', environment_id='e', source_code_sha256='1' * 64)
        self.log = Journal(self.root / 'journal')

    def frame(self, raw=b'normal', delivered=None):
        expected = self.guard.issue(0)
        body = {'protocol': PROTOCOL, 'session_id': 's', 'environment_id': 'e', 'capture_id': uuid.uuid4().hex,
                'challenge': expected['challenge'], 'action_sequence': 0, 'capture_index': 1, 'acquired_at_ns': time.time_ns(),
                'image_sha256': digest(raw), 'source_code_sha256': '1' * 64, 'key_id': digest(self.pub)}
        receipt = {**body, 'signature': self.key.sign(canonical(body)).hex()}
        return Frame(raw if delivered is None else delivered, body['capture_id'], time.time(), receipt, expected)

    def gate(self, checker):
        return ImageGate(checker, receipt_guard=self.guard, revision='pinned', contract_sha256='contract', journal=self.log, recapture_seconds=0)

    def test_01_source_NO_skips_Flash_and_recaptures(self):
        checker = Checker()
        gate = self.gate(checker)
        bad = self.frame(b'current', b'old')
        result = gate.acquire(bad, lambda: self.frame(b'current'), cancelled=lambda: False)
        self.assertEqual(checker.inputs, [b'current'])
        self.assertEqual((gate.receipt_no, gate.recaptures, result['status']), (1, 1, 'accepted'))

    def test_02_signed_bad_frame_still_requires_Flash(self):
        checker = Checker(('NO', 'YES'))
        gate = self.gate(checker)
        gate.acquire(self.frame(b'authentic blank'), lambda: self.frame(), cancelled=lambda: False)
        self.assertEqual(checker.inputs, [b'authentic blank', b'normal'])
        self.assertEqual((gate.receipt_no, gate.calls, gate.recaptures), (0, 2, 1))

    def test_03_missing_precheck_skips_receipt_and_Flash(self):
        checker = Checker()
        gate = self.gate(checker)
        gate.acquire(Frame.captured(None), lambda: self.frame(), cancelled=lambda: False)
        self.assertEqual((gate.precheck_no, gate.receipt_no, gate.calls, gate.recaptures), (1, 0, 1, 1))

    def test_04_pure_WAIT_original_history_without_receipt_metadata(self):
        bodies = []
        checker = Checker()
        gate = self.gate(checker)
        template = json.loads((ROOT / 'actor-template.json').read_bytes())
        prior = [{'role': 'user', 'content': 'Full legal earlier history'}, {'role': 'assistant', 'content': 'Earlier reply'}]
        def call(body):
            bodies.append(body)
            return '<action>{"type":"wait"}</action>'
        actor = NativeHistoryActor(template, call, past_messages=prior)
        source = (ROOT / 'native-parser-source.py').read_text('utf-8')
        parse = next(n for n in ast.parse(source).body if getattr(n, 'name', '') == 'parse')
        space = {'re': re, 'json': json}
        exec(compile(ast.Module(body=[parse], type_ignores=[]), '<original-native-parser>', 'exec'), space)
        controller = GateController(gate, max_steps=50, max_actor_calls=70)
        result = controller.step(self.frame(b'now', b'old'), lambda: self.frame(), actor, space['parse'],
                                 lambda payload: {'environment_action': True, 'ok': True, 'payload': payload}, cancelled=lambda: False)
        actor.commit(result)
        self.assertEqual(result['proposal'], {'type': 'wait'})
        self.assertEqual(bodies[0]['messages'][1:3], prior)
        self.assertEqual(bodies[0]['messages'][0], template['messages'][0])
        serialized = json.dumps(bodies[0])
        self.assertNotIn('signature', serialized)
        self.assertNotIn('challenge', serialized)
        self.assertEqual(checker.inputs, [b'normal'])

    def test_05_manual_stop_before_models(self):
        checker = Checker()
        gate = self.gate(checker)
        result = gate.acquire(self.frame(), lambda: self.frame(), cancelled=lambda: True)
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(checker.inputs, [])

    def test_06_identical_new_acquisition_not_false_replay(self):
        for _ in range(2):
            checker = Checker()
            self.assertEqual(self.gate(checker).acquire(self.frame(), lambda: self.frame(), cancelled=lambda: False)['status'], 'accepted')

    def test_07_original_gate_semantic_failure_stays_technical(self):
        checker = Checker(())
        result = self.gate(checker).acquire(self.frame(), lambda: self.frame(), cancelled=lambda: False)
        self.assertEqual((result['status'], result['reason']), ('technical_failure', 'checker_failure'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
