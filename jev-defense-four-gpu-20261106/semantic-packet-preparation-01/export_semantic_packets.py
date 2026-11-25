"""Freeze complete actor candidates from an append-only Controller prefix.

Reads no PRIVATE task/config/score/answer files, invokes no old label script, and
does not call models or GUI. Review projection excludes transport arm/outcomes;
the complete native actor input, including lawful old feedback, remains intact.
"""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import struct
import time


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def complete_prefix(path):
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    if lines and not lines[-1].endswith(b'\n'):
        lines.pop()
    events, previous, candidate_end = [], '0' * 64, None
    for index, line in enumerate(lines):
        value = json.loads(line)
        assert value['seq'] == index and value['previous'] == previous
        assert digest(canonical({k: v for k, v in value.items() if k != 'sha256'})) == value['sha256']
        previous = value['sha256']
        events.append(value)
        if value['kind'] == 'candidate':
            candidate_end = index
    if candidate_end is None:
        return [], b''
    return events[:candidate_end + 1], b''.join(lines[:candidate_end + 1])


def assert_prefix_stable(path, frozen):
    with path.open('rb') as stream:
        assert stream.read(len(frozen)) == frozen, 'Immutable source prefix changed'


def image_from_block(block):
    url = block['image_url']['url']
    assert isinstance(url, str) and url.startswith('data:image/png;base64,')
    raw = base64.b64decode(url.split(',', 1)[1], validate=True)
    assert raw[:8] == b'\x89PNG\r\n\x1a\n' and raw[12:16] == b'IHDR'
    width, height = struct.unpack('>II', raw[16:24])
    assert width > 0 and height > 0
    return raw, [width, height]


def extract_packet(actor_context, native_event, request, raw_response, response, candidate, output, prior_deliveries):
    public = actor_context['data']['public']
    native_data = native_event['data']
    payload = native_data['body']
    assert payload['operation'] == 'actor' and set(payload) == {'operation', 'body'}
    assert digest(native_data['wire_utf8'].encode()) == native_data['wire_sha256']
    assert json.loads(native_data['wire_utf8']) == payload
    assert digest(canonical(payload)) == native_data['canonical_sha256']
    assert native_data['original_public_sha256'] == digest(canonical(public))
    outer = request['data']['body']
    wire = request['data']['wire_utf8'].encode()
    assert digest(wire) == request['data']['wire_sha256'] and json.loads(wire) == outer
    assert outer['payload'] == payload
    raw = base64.b64decode(raw_response['data']['raw_base64'], validate=True)
    assert digest(raw) == raw_response['data']['raw_sha256']
    assert raw_response['data']['http_status'] == response['data']['http_status'] == 200
    actual_response = response['data']['body']
    assert json.loads(raw) == actual_response
    assert digest(canonical(actual_response)) == response['data']['response_sha256']
    assert actual_response['external_wire_sha256'] == digest(wire)
    assert actual_response['request_id'] == outer['request_id']
    assert actual_response['payload_sha256'] == digest(canonical(payload))
    text = candidate['data']['text']
    assert isinstance(text, str) and text.strip() and actual_response['text'] == text
    assert candidate['data']['observation_id'] == public['observation_id']
    body = copy.deepcopy(payload['body'])
    messages = body['messages']
    index = native_data['current_user_message_index']
    assert type(index) is int and 0 <= index < len(messages)
    assert messages[index]['role'] == 'user' and isinstance(messages[index]['content'], list)
    # The pinned adapter appends exactly one observer/shared-instruction block.
    restored = copy.deepcopy(messages)
    appended = restored[index]['content'].pop()
    assert appended.get('type') == 'text' and isinstance(appended.get('text'), str)
    assert restored == public['messages']
    current = [x for x in public['images'] if x['role'] == 'current']
    current_blocks = [b for b in messages[index]['content'] if b.get('type') == 'image_url']
    assert len(current) == len(current_blocks)
    for declared, block in zip(current, current_blocks):
        raw_image, size = image_from_block(block)
        assert declared['sha256'] == digest(raw_image) and declared['size'] == size
    packet_id = 'p-' + candidate['sha256'][:24]
    image_rows, rendered = [], []
    for mi, message in enumerate(messages):
        rendered.append('Message ' + str(mi) + ' (' + str(message['role']) + ')\n')
        content = message.get('content')
        if isinstance(content, str):
            rendered.append(content + '\n')
        elif isinstance(content, list):
            for bi, block in enumerate(content):
                if block.get('type') == 'image_url':
                    raw_image, size = image_from_block(block)
                    sha = digest(raw_image)
                    image_path = output / 'review/images' / (sha + '.png')
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    if image_path.exists():
                        assert image_path.read_bytes() == raw_image
                    else:
                        with image_path.open('xb') as stream:
                            stream.write(raw_image)
                    role = 'current_received' if mi == index else 'history_received'
                    row = {'message_index': mi, 'block_index': bi, 'sha256': sha, 'size': size,
                           'role_in_actual_actor_request': role, 'file': '../images/' + sha + '.png'}
                    image_rows.append(row)
                    rendered.append('[Actual delivered image ' + sha + ', ' + role + ', ' + str(size) + ']\n')
                elif block.get('type') == 'text':
                    rendered.append(block['text'] + '\n')
                else:
                    rendered.append(json.dumps(block, ensure_ascii=False) + '\n')
        else:
            rendered.append(json.dumps(content, ensure_ascii=False) + '\n')
    native_relative = 'native/' + packet_id + '.json'
    write_json(output / 'review' / native_relative, payload)
    history_path = output / 'review/history' / (packet_id + '.txt')
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(rendered))
    candidate_path = output / 'review/candidates' / (packet_id + '.txt')
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    with candidate_path.open('x', encoding='utf-8') as stream:
        stream.write(text)
    packet = {'packet_id': packet_id, 'candidate_file': '../candidates/' + packet_id + '.txt',
              'candidate_sha256': digest(text.encode()), 'native_actor_request': '../' + native_relative,
              'native_actor_payload_canonical_sha256': digest(canonical(payload)),
              'complete_legal_history_text': '../history/' + packet_id + '.txt',
              'message_count': len(messages), 'actual_delivered_images': image_rows,
              'current_received_image_count': len(current),
              'earlier_actual_actor_delivery_sources': copy.deepcopy(prior_deliveries),
              'earlier_images_scope': 'These earlier images were proven in completed prior actor wire/reply/candidate pairs in this trajectory. They are offline review sources, not extra images in the present model request. Readiness-only observations are excluded.',
              'review_scope': 'Pixels, full legitimate native actor input and exact candidate only. Historical defense feedback and observer predictions are fallible input claims, never gold labels.',
              'blinding': 'Transport arm/execution/outcome metadata withheld; lawful history may reveal intervention, so not fully blind',
              'semantic_Mirage': None, 'pure_native_WAIT_excluded': None,
              'native_action_error': None, 'unresolved_subclaims': None,
              'reviewer_has_viewed_all_images': False,
              'execution_join_performed': False, 'official_outcome_read': False}
    write_json(output / 'review/packets' / (packet_id + '.json'), packet)
    provenance = {'packet_id': packet_id,
                  'events': {name: {'seq': value['seq'], 'sha256': value['sha256']} for name, value in
                             [('actor_request', actor_context), ('native_payload', native_event),
                              ('actual_request', request), ('raw_response', raw_response),
                              ('response', response), ('candidate', candidate)]},
                  'actual_wire_sha256': digest(wire), 'actual_raw_response_sha256': digest(raw),
                  'candidate_event': candidate, 'source_service_receipt': actual_response.get('receipt'),
                  'service_EOS_and_inputID_audit': 'separate later source audit; not inferred from candidate presence'}
    return packet, provenance


def export_attempt(attempt, output, expected_code):
    source = attempt / 'events.jsonl'
    events, frozen = complete_prefix(source)
    assert events, 'No complete candidate prefix; no packet exported'
    implementations = [e for e in events if e['kind'] == 'implementation']
    assert len(implementations) == 1
    assert implementations[0]['data']['code_sha256'] == expected_code
    output.mkdir(parents=True, exist_ok=False)
    packets, provenance = [], []
    prior_deliveries = []
    context = native = last_request = last_raw = last_response = None
    for event in events:
        kind, data = event['kind'], event['data']
        if kind == 'actor_request':
            assert context is None
            context = event
        elif kind == 'actor_observer_native_payload':
            assert context is not None and native is None
            native = event
        elif kind == 'actual_primary_wire_request':
            last_request, last_raw, last_response = event, None, None
        elif kind == 'actual_primary_wire_raw_response':
            last_raw = event
        elif kind == 'actual_primary_wire_response':
            last_response = event
        elif kind == 'candidate':
            assert all(x is not None for x in (context, native, last_request, last_raw, last_response))
            packet, binding = extract_packet(context, native, last_request, last_raw, last_response, event, output, prior_deliveries)
            packets.append({'packet_id': packet['packet_id'], 'file': 'packets/' + packet['packet_id'] + '.json'})
            provenance.append(binding)
            prior_deliveries.append({'earlier_actor_call_index': len(packets), 'prior_packet_id': packet['packet_id'],
                'prior_native_actor_request': '../native/' + packet['packet_id'] + '.json',
                'observation_id': context['data']['public']['observation_id'],
                'actual_delivered_image_occurrences': copy.deepcopy(packet['actual_delivered_images']),
                'proof_scope': 'Complete earlier actual actor wire + full reply + candidate; no accepted/executed inference'})
            context = native = None
    assert packets
    assert_prefix_stable(source, frozen)
    write_json(output / 'provenance/source-map.json', {'source_attempt': str(attempt), 'packets': provenance})
    receipt = {'status': 'complete_candidate_prefix_frozen', 'created_time': time.time(),
               'source_events_path': str(source), 'frozen_prefix_seq': events[-1]['seq'],
               'frozen_prefix_chain_head': events[-1]['sha256'], 'frozen_prefix_bytes': len(frozen),
               'frozen_prefix_sha256': digest(frozen), 'complete_candidates': len(packets),
               'source_prefix_rechecked_byte_identical': True, 'expected_release_code': expected_code,
               'source_implementation_event_sha256': implementations[0]['sha256'],
               'pending_tail_or_partial_lines_exported': False, 'PRIVATE_task_or_score_files_opened': False,
               'accepted_execution_or_official_data_in_review_projection': False,
               'earlier_delivery_archive_requires_actual_completed_actor_wire': True,
               'readiness_only_observations_not_counted_as_actor_delivery': True,
               'labels_created': False, 'execution_join_performed': False, 'model_calls': 0, 'GUI_actions': 0,
               'exporter_source_sha256': digest(Path(__file__).read_bytes())}
    write_json(output / 'provenance/prefix-receipt.json', receipt)
    write_json(output / 'review/index.json', {'status': 'unreviewed_packets', 'packets': packets,
               'semantic_passes': None, 'Mirage_rate': None, 'all_labels_pending': True,
               'labels_must_be_sealed_before_execution_join': True})
    assert_prefix_stable(source, frozen)
    write_json(output / 'seal.json', {str(p.relative_to(output)): digest(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()})
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--release-code-bindings', type=Path, required=True)
    args = parser.parse_args()
    result = export_attempt(args.attempt, args.output, json.loads(args.release_code_bindings.read_bytes()))
    print(json.dumps({k: result[k] for k in ('status', 'frozen_prefix_seq', 'frozen_prefix_chain_head', 'complete_candidates', 'model_calls', 'GUI_actions')}))
