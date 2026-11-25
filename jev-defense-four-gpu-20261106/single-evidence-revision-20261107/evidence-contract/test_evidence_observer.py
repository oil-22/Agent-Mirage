import base64
import copy
import io
import json
import unittest
from dataclasses import dataclass
from PIL import Image
from evidence_observer import NeutralEvidenceObserver
from image_evidence import EvidenceContractError, canonical, digest
from test_image_evidence import example


@dataclass
class ImageData:
    raw: bytes
    role: str = 'current'


@dataclass
class View:
    messages: list
    images: tuple
    def data(self):
        return {'messages': self.messages, 'images': [{'sha256': digest(im.raw), 'role': im.role} for im in self.images]}


class Wiring(unittest.TestCase):
    def setUp(self):
        out = io.BytesIO(); Image.new('RGB', (1280, 720), 'white').save(out, format='PNG')
        self.raw = out.getvalue(); self.requests = []; self.events = []
        self.model = 'native-generative-model-to-be-frozen'; self.revision = 'a' * 40

    def backend(self, request):
        self.requests.append(copy.deepcopy(request))
        return {'request_sha256': digest(canonical(request)), 'image_sha256': request['image_sha256'],
            'model': self.model, 'revision': self.revision, 'raw_output': json.dumps(example()), 'natural_eos': True}

    def observer(self, backend=None, enabled=True, max_calls=60):
        return NeutralEvidenceObserver(self.backend if backend is None else backend,
            model=self.model, revision=self.revision, enabled=enabled, max_calls=max_calls,
            emit=lambda kind, value: self.events.append((kind, value)))

    def view(self, raw=True):
        content = [{'type': 'text', 'text': 'Task data remains only in actor input.'}]
        if raw:
            content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(self.raw).decode()}})
        return View([{'role': 'system', 'content': 'Original system.'},
            {'role': 'assistant', 'content': 'Entire prior response and native action.'},
            {'role': 'user', 'content': content},
            {'role': 'user', 'content': 'Trailing original regeneration correction.'}],
            (ImageData(self.raw),) if raw else ())

    def test_actual_actor_insertion_retains_full_history_and_correction(self):
        view = self.view(); body = {'messages': copy.deepcopy(view.messages), 'temperature': 0, 'max_tokens': 2048}
        original = copy.deepcopy(body)
        result = self.observer().augment(body, view)
        self.assertEqual(body, original)
        self.assertEqual(result['messages'][-1], original['messages'][-1])
        self.assertEqual(result['messages'][:-2], original['messages'][:-2])
        self.assertEqual(result['messages'][2]['content'][:-1], original['messages'][2]['content'])
        self.assertEqual(len(self.requests), 1)
        self.assertNotIn('Task data', json.dumps(self.requests[0]))
        self.assertNotIn('prior response', json.dumps(self.requests[0]))

    def test_baseline_has_same_static_boundary_and_no_auxiliary_call(self):
        view = self.view(); body = {'messages': copy.deepcopy(view.messages)}
        result = self.observer(enabled=False).augment(body, view)
        self.assertIn('IMAGE-ONLY EVIDENCE PACKET', result['messages'][2]['content'][-1]['text'])
        self.assertEqual(self.requests, [])

    def test_exact_received_image_cache_does_not_retry_failure(self):
        calls = []
        def broken(request):
            calls.append(request); raise RuntimeError('preserved failure')
        observer = self.observer(backend=broken)
        first, second = observer.packet(self.raw), observer.packet(self.raw)
        self.assertEqual(len(calls), 1)
        self.assertIn('failure', first['status'])
        self.assertTrue(second['exact_input_reuse'])

    def test_non_eos_or_wrong_binding_stays_unavailable(self):
        for field, replacement in [('natural_eos', False), ('image_sha256', '0' * 64), ('revision', 'b' * 40)]:
            def bad(request):
                response = self.backend(request); response[field] = replacement; return response
            packet = self.observer(backend=bad).packet(self.raw)
            self.assertIsNone(packet['reading'])
            self.assertFalse(packet['automatic_allow_or_block'])

    def test_failed_response_is_preserved_before_validation(self):
        def malformed(request):
            return {'raw_native_output': 'original malformed response', 'unexpected': 1}
        observer = self.observer(backend=malformed)
        result = observer.packet(self.raw)
        self.assertIn('failure', result['status'])
        raw = [value for kind, value in self.events if kind == 'neutral_evidence_raw_reply']
        self.assertEqual(raw[0]['response']['raw_native_output'], 'original malformed response')

    def test_missing_image_and_budget_never_infer_scene(self):
        self.assertIn('no_current_image', self.observer().packet(None)['status'])
        self.assertIn('budget_exhausted', self.observer(max_calls=0).packet(self.raw)['status'])
        self.assertEqual(self.requests, [])

    def test_mismatched_actual_actor_image_rejected_before_inference(self):
        view = self.view(); body = {'messages': copy.deepcopy(view.messages)}
        body['messages'][2]['content'][1]['image_url']['url'] += 'tampered'
        # Source view equality is necessary as well as explicit image binding.
        with self.assertRaises(EvidenceContractError):
            self.observer().augment(body, view)
        self.assertEqual(self.requests, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
