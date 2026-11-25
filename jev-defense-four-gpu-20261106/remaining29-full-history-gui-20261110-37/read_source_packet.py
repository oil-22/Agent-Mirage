"""Display only lawful source text and image identities, never image base64.

An optional unchanged prefix may only refer to an already source-sealed packet.
No checker/execution/scorer/private index is read, and no labels are generated.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

from orchestrate import HERE, sha
from join_source_reviews import verify_seal


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')


def load_public(packet):
    packet = packet.resolve()
    assert packet.name == 'packet.json' and packet.parent.parent.parent == HERE / 'source-first-packets'
    verify_seal(packet.parent.parent)
    value = json.loads(packet.read_bytes())
    assert value['checker_labels_current_acceptance_execution_scoring_private_delivery_excluded'] is True
    assert sha(packet) and hashlib.sha256(value['candidate'].encode()).hexdigest() == value['candidate_text_sha256']
    return packet, value


def sealed_previous(packet):
    for pointer in HERE.glob('source-review-*-created.json'):
        if not re.fullmatch(r'source-review-\d+-created\.json', pointer.name):
            continue
        authority = json.loads(pointer.read_bytes())
        folder = Path(authority['review'])
        assert folder.parent == HERE and verify_seal(folder) == authority['seal_sha256']
        assert sha(folder / 'review.json') == authority['review_sha256']
        for row in json.loads((folder / 'review.json').read_bytes())['rows']:
            if Path(row['public_source_packet']).resolve() == packet:
                assert row['packet_sha256'] == sha(packet)
                return dict(review=str(folder), review_sha256=authority['review_sha256'])
    raise ValueError('Previous complete prefix has no immutable source-review authority')


def main(packet_path, previous_path=None):
    packet, value = load_public(packet_path)
    request = value['actual_actor_request']
    messages = request['messages']
    images = []
    by_position = {}
    for i, original in enumerate(value['actual_delivered_images']):
        path = packet.parent / ('image-%02d.png' % i)
        assert sha(path) == original['sha256']
        row = dict(message_index=original['message_index'], block_index=original['block_index'],
            sha256=original['sha256'], original_image_file=str(path))
        by_position[(row['message_index'], row['block_index'])] = row
        images.append(row)
    safe_messages = []
    for i, message in enumerate(messages):
        content = message['content']
        if isinstance(content, str):
            safe = content
        else:
            assert isinstance(content, list)
            safe = []
            for j, block in enumerate(content):
                if block['type'] == 'text':
                    safe.append(dict(type='text', text=block['text']))
                else:
                    assert block['type'] == 'image_url'
                    identity = by_position[(i, j)]
                    url = block['image_url']['url']
                    header, encoded = url.split(',', 1)
                    assert header.startswith('data:image/') and header.endswith(';base64')
                    assert hashlib.sha256(base64.b64decode(encoded, validate=True)).hexdigest() == identity['sha256']
                    safe.append(dict(type='original_image', **identity))
        safe_messages.append(dict(message_index=i, role=message['role'], content=safe))
    start, prefix = 0, None
    if previous_path:
        previous, earlier = load_public(previous_path)
        authority = sealed_previous(previous)
        earlier_messages = earlier['actual_actor_request']['messages']
        assert len(earlier_messages) < len(messages)
        same = canonical(messages[:len(earlier_messages)]) == canonical(earlier_messages)
        prefix = dict(previous_packet=str(previous), source_review_authority=authority,
            unchanged_complete_prefix_verified=same, messages=len(earlier_messages),
            canonical_prefix_sha256=hashlib.sha256(canonical(earlier_messages)).hexdigest())
        if same:
            start = len(earlier_messages)
    parameters = {key: request[key] for key in ['model', 'temperature', 'max_tokens', 'chat_template_kwargs'] if key in request}
    result = dict(packet=str(packet), packet_sha256=sha(packet), id=value['id'],
        candidate_event_sha256=value['candidate_event_sha256'], candidate=value['candidate'],
        native_parser_result=value['native_parser_result'], original_actor_body_sha256=value['actor_request_body_sha256'],
        complete_message_count=len(messages), complete_image_count=len(images), original_images=images,
        complete_request_parameters=parameters, additional_parameter_names=sorted(set(request) - set(parameters) - {'messages'}),
        already_reviewed_unchanged_prefix=prefix, messages_for_source_reading=safe_messages[start:],
        checker_execution_score_or_private_index_read=False, semantic_labels_created=False,
        new_model_GUI_scorer_calls=0)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet', required=True, type=Path)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    main(args.packet, args.previous)
