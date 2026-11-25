"""Freeze source-reviewed postcheck inputs with full recovery history and references.

Evaluation only; original single-current-image observer and runtime stay unchanged.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import time

import orchestrate


def verify(folder):
    for name, expected in json.loads((folder / 'seal.json').read_bytes()).items():
        item = folder / name
        assert item.resolve().is_relative_to(folder.resolve()) and orchestrate.sha(item) == expected
    return orchestrate.sha(folder / 'seal.json')


def main(notes_path):
    root = orchestrate.HERE
    assert notes_path.parent == root
    notes = json.loads(notes_path.read_bytes())
    assert re.fullmatch(r'[a-z][a-z0-9-]+', notes['key'])
    pointer = root / (notes['key'] + '-created.json')
    assert not pointer.exists()
    source_authority = json.loads((root / notes['source_pointer']).read_bytes())
    source = Path(source_authority['root'])
    assert source.parent == root and verify(source) == source_authority['seal_sha256']
    assert orchestrate.sha(source / 'receipt.json') == source_authority['receipt_sha256']
    payload = json.loads((source / 'payload.json').read_bytes())
    receipt = json.loads((source / 'receipt.json').read_bytes())
    label_authority = json.loads((root / notes['actor_review_pointer']).read_bytes())
    reviewed = Path(label_authority['review'])
    assert reviewed.parent == root and verify(reviewed) == label_authority['seal_sha256']
    label = next(v for v in json.loads((reviewed / 'review.json').read_bytes())['rows'] if v['id'] == notes['actor_source_id'])
    packet_path = Path(label['public_source_packet'])
    assert orchestrate.sha(packet_path) == label['packet_sha256']
    packet = json.loads(packet_path.read_bytes())
    expected = copy.deepcopy(packet['actual_actor_request']['messages'])
    image_messages = [i for i, msg in enumerate(expected) if isinstance(msg['content'], list)
        and any(v.get('type') == 'image_url' for v in msg['content'])]
    current_index = image_messages[-1]
    current_blocks = expected[current_index]['content']
    expected[current_index]['content'] = [v for v in current_blocks if not (
        v.get('type') == 'text' and v['text'].startswith('IMAGE-ONLY EVIDENCE PACKET'))]
    assert len(current_blocks) - len(expected[current_index]['content']) == 1
    assert payload['operation'] == 'judge' and payload['candidate'] == packet['candidate']
    assert payload['view']['messages'] == expected
    inventory = payload['view']['images']
    assert len(inventory) == len(receipt['images']) and inventory
    assert inventory[0]['role'] == 'current'
    supplied_hashes = {v['sha256'] for v in packet['actual_delivered_images']}
    for image, frozen in zip(inventory, receipt['images']):
        raw = base64.b64decode(image['raw_base64'], validate=True)
        assert raw == (source / frozen['file']).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == frozen['sha256'] and digest in supplied_hashes
    assert receipt['images'][0]['sha256'] == packet['actual_delivered_images'][-1]['sha256']
    assert notes['all_actual_system_dynamic_records_and_messages_read'] is True
    assert notes['complete_raw_own_reply_not_read'] is True
    target = root / (notes['key'] + '-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (target / 'reviewer-notes.json').write_bytes(notes_path.read_bytes())
    orchestrate.save(target / 'review.json', dict(
        schema='source-first-full-recovery-and-reference-postcheck-input-review-v1', time=time.time(),
        rows=[dict(request=receipt['request'], source_input=str(source),
            source_input_seal_sha256=source_authority['seal_sha256'], actual_images=receipt['images'],
            actor_source_review=label_authority, complete_actor_messages=len(expected),
            current_auxiliary_packet_message_index=current_index,
            only_current_auxiliary_packet_removed_from_checker_projection=True,
            main_actor_history_and_images_unchanged=True,
            actual_system_utf8_sha256=hashlib.sha256(payload['system'].encode()).hexdigest(),
            complete_raw_own_reply_not_read_before_seal=True,
            judgments_before_reply=notes['judgments_before_reply'])],
        one_reviewer_nonblind_development_diagnosis=True,
        evaluation_only_never_checker_input=True, source_labels_unchanged=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    orchestrate.save(target / 'seal.json', {p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=orchestrate.sha(target / 'review.json'),
                  seal_sha256=orchestrate.sha(target / 'seal.json'))
    orchestrate.save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))
