"""Synthetic CPU boundary tests; no original task/score/model/GUI access."""
import base64
import binascii
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

import export_semantic_packets as e


def png(rgb):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', binascii.crc32(tag + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\0' + bytes(rgb))) + chunk(b'IEND', b'')


def block(raw):
    return {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(raw).decode()}}


def make_source(root, candidates=2, missing_current=False):
    root.mkdir()
    events = []
    def add(kind, data):
        event = {'seq': len(events), 'previous': events[-1]['sha256'] if events else '0' * 64,
                 'time': 100 + len(events), 'kind': kind, 'data': data}
        event['sha256'] = e.digest(e.canonical(event)); events.append(event)
    code = {'defense/core.py': 'a' * 64}
    add('implementation', {'code_sha256': code})
    # Readiness-only image must not become a past actor delivery.
    add('observation', {'audience': 'actor', 'public': {'images': [{'sha256': e.digest(png((255, 0, 0)))}]},
                        'detector_label': 'HIDDEN_DETECTOR_SENTINEL'})
    for number in range(candidates):
        image = png((0, number * 100, 255))
        content = [{'type': 'text', 'text': 'Legitimate task only'}]
        if not missing_current: content.append(block(image))
        public = {'observation_id': 'obs' + str(number), 'messages': [
            {'role': 'system', 'content': 'native system'},
            {'role': 'user', 'content': 'Past defensefeedback may be mistaken; preserve this exact lawful history.'},
            {'role': 'user', 'content': content}],
            'images': [] if missing_current else [{'role': 'current', 'sha256': e.digest(image), 'size': [1, 1]}],
            'recent_action': '', 'execution_feedback': '', 'observed_at': 99}
        add('actor_request', {'public': public})
        body = {'messages': copy.deepcopy(public['messages']), 'max_tokens': 2048, 'temperature': 0}
        body['messages'][2]['content'].append({'type': 'text', 'text': 'Actually delivered fallible auxiliary observations'})
        payload = {'operation': 'actor', 'body': body}
        native = {'body': payload, 'wire_utf8': json.dumps(payload), 'wire_sha256': e.digest(json.dumps(payload).encode()),
                  'canonical_sha256': e.digest(e.canonical(payload)), 'original_public_sha256': e.digest(e.canonical(public)),
                  'current_user_message_index': 2}
        add('actor_observer_native_payload', native)
        outer = {'trajectory_id': 'HIDDEN_MODEL_ARM', 'request_id': 'id' + str(number), 'payload': payload,
                 'decision_index': number + 1, 'attempt_index': number + 1}
        wire = e.canonical(outer)
        add('actual_primary_wire_request', {'body': outer, 'wire_utf8': wire.decode(), 'wire_sha256': e.digest(wire)})
        candidate = 'Exact candidate ' + str(number) + '\n{"type":"wait"}'
        response = {'request_id': outer['request_id'], 'external_wire_sha256': e.digest(wire),
                    'payload_sha256': e.digest(e.canonical(payload)), 'text': candidate}
        raw = json.dumps(response).encode()
        add('actual_primary_wire_raw_response', {'http_status': 200, 'raw_base64': base64.b64encode(raw).decode(), 'raw_sha256': e.digest(raw)})
        add('actual_primary_wire_response', {'http_status': 200, 'body': response, 'response_sha256': e.digest(e.canonical(response))})
        add('candidate', {'observation_id': public['observation_id'], 'text': candidate})
        add('decision_accepted', {'detector_label': 'HIDDEN_DETECTOR_SENTINEL', 'official_score': 'HIDDEN_SCORE_SENTINEL'})
    path = root / 'events.jsonl'
    path.write_bytes(b''.join(json.dumps(x).encode() + b'\n' for x in events) + b'{"pending_half_line":')
    return code, events


class Tests(unittest.TestCase):
    def test_full_actual_inputs_and_only_completed_candidates_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); code, events = make_source(root / 'source')
            result = e.export_attempt(root / 'source', root / 'out', code)
            self.assertEqual(result['complete_candidates'], 2)
            self.assertEqual(result['frozen_prefix_seq'], events[-2]['seq'])
            index = json.loads((root / 'out/review/index.json').read_bytes())
            first, second = [json.loads((root / 'out/review' / x['file']).read_bytes()) for x in index['packets']]
            self.assertEqual(first['earlier_actual_actor_delivery_sources'], [])
            self.assertEqual(len(second['earlier_actual_actor_delivery_sources']), 1)
            self.assertEqual(second['earlier_actual_actor_delivery_sources'][0]['prior_packet_id'], first['packet_id'])
            self.assertEqual(len(list((root / 'out/review/images').glob('*.png'))), 2)
            text = (root / 'out/review/history' / (first['packet_id'] + '.txt')).read_text()
            self.assertIn('Past defensefeedback may be mistaken', text)
            self.assertIn('Actually delivered fallible auxiliary observations', text)
            combined = b''.join(p.read_bytes() for p in (root / 'out/review').rglob('*') if p.is_file())
            for hidden in (b'HIDDEN_MODEL_ARM', b'HIDDEN_DETECTOR_SENTINEL', b'HIDDEN_SCORE_SENTINEL', b'pending_half_line'):
                self.assertNotIn(hidden, combined)
            self.assertIsNone(first['semantic_Mirage'])

    def test_prefix_allows_append_but_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); _, _ = make_source(root / 'source', candidates=1)
            path = root / 'source/events.jsonl'; _, frozen = e.complete_prefix(path)
            path.write_bytes(frozen + b'{"new_pending":')
            e.assert_prefix_stable(path, frozen)
            path.write_bytes(b'X' + frozen[1:])
            with self.assertRaises(AssertionError): e.assert_prefix_stable(path, frozen)

    def test_none_received_frame_not_replaced_by_readiness_image(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); code, _ = make_source(root / 'source', candidates=1, missing_current=True)
            e.export_attempt(root / 'source', root / 'out', code)
            index = json.loads((root / 'out/review/index.json').read_bytes())
            packet = json.loads((root / 'out/review' / index['packets'][0]['file']).read_bytes())
            self.assertEqual(packet['current_received_image_count'], 0)
            self.assertEqual(packet['actual_delivered_images'], [])
            self.assertFalse((root / 'out/review/images').exists())

    def test_chain_or_candidate_reply_or_image_binding_corruption_rejected(self):
        for mode in ('chain', 'candidate', 'release'):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder); code, events = make_source(root / 'source', candidates=1)
                if mode == 'chain':
                    events[1]['data']['extra'] = 'tamper'
                elif mode == 'candidate':
                    events[-2]['data']['text'] = 'does not equal actual reply'
                    previous = '0' * 64
                    for value in events:
                        value['previous'] = previous
                        value['sha256'] = e.digest(e.canonical({k: v for k, v in value.items() if k != 'sha256'})); previous = value['sha256']
                else: code = {'different': 'b' * 64}
                (root / 'source/events.jsonl').write_bytes(b''.join(json.dumps(x).encode() + b'\n' for x in events))
                with self.assertRaises(AssertionError): e.export_attempt(root / 'source', root / 'out', code)

    def test_no_candidate_does_not_export_fake_zero_or_reply(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); code, _ = make_source(root / 'source', candidates=0)
            with self.assertRaises(AssertionError): e.export_attempt(root / 'source', root / 'out', code)
            self.assertFalse((root / 'out').exists())


if __name__ == '__main__': unittest.main(verbosity=2)
