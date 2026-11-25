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

    def test_08_clean_control_never_calls_private_fault_bridge(self):
        from injection import Episode
        from types import SimpleNamespace
        def fail(*_):
            raise AssertionError('A normal control cannot render a fault')
        env = SimpleNamespace(page=SimpleNamespace(url='http://192.0.2.10:29980/index.php?page=item&id=1'), native_fault_probe=fail)
        ep = Episode('clean_control')
        raw, event = ep.apply(b'normal', step=2, previous_png=b'old', previous_action={'type':'click'}, recapture=False, env=env)
        self.assertEqual(raw, b'normal')
        self.assertFalse(event['injected'])

    def test_09_original_buttons_bridge_once_and_recapture_not_injected(self):
        from injection import Episode
        from types import SimpleNamespace
        calls = []
        def probe(name):
            calls.append(name)
            return b'actual native mask'
        env = SimpleNamespace(page=SimpleNamespace(url='http://192.0.2.10:29980/index.php?page=item&id=9'), native_fault_probe=probe)
        ep = Episode('buttons_only')
        for recapture in [False, True, False]:
            raw, event = ep.apply(b'normal', step=3, previous_png=b'previous', previous_action={'type':'click'}, recapture=recapture, env=env)
            self.assertEqual(raw, b'actual native mask' if len(calls)==1 and event['injected'] else b'normal')
        self.assertEqual(calls, ['buttons_only'])
        self.assertEqual(ep.used, 1)

    def test_10_native_blank_bridge_and_silent_drop_remain_distinct(self):
        from injection import Episode
        from types import SimpleNamespace
        calls=[]
        env=SimpleNamespace(native_fault_probe=lambda name:(calls.append(name) or b'native blank'))
        blank, event=Episode('blank_replace').apply(b'current', step=2, previous_png=b'old', previous_action={'type':'click'}, recapture=False, env=env)
        self.assertEqual(blank,b'native blank')
        self.assertEqual(calls,['blank_replace'])
        missing, event=Episode('silent_drop').apply(b'current', step=2, previous_png=b'old', previous_action={'type':'click'}, recapture=False, env=env)
        self.assertIsNone(missing)

    def test_11_missing_signed_capture_does_not_bypass_actual_loop(self):
        checker=Checker()
        gate=self.gate(checker)
        frame=self.frame();frame=Frame(None,frame.capture_id,frame.captured_at,frame.receipt,frame.expected)
        result=gate.acquire(frame,lambda:self.frame(),cancelled=lambda:False)
        self.assertEqual((gate.precheck_no,gate.receipt_no,gate.calls,gate.recaptures),(1,0,1,1))
        self.assertEqual(result['status'],'accepted')


if __name__ == '__main__':
    unittest.main(verbosity=2)
