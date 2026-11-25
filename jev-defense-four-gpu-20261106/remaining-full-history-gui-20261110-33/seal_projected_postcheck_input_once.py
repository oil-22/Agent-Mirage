"""Freeze a source-reviewed postcheck's exact original public-history projection."""
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
        assert (folder / name).resolve().is_relative_to(folder.resolve())
        assert orchestrate.sha(folder / name) == expected
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
    expected[-1]['content'] = [v for v in expected[-1]['content'] if not (
        v.get('type') == 'text' and v['text'].startswith('IMAGE-ONLY EVIDENCE PACKET'))]
    assert payload['operation'] == 'judge' and payload['candidate'] == packet['candidate']
    assert payload['view']['messages'] == expected
    assert len(payload['view']['images']) == len(receipt['images']) == 1
    image = payload['view']['images'][0]
    raw = base64.b64decode(image['raw_base64'], validate=True)
    assert raw == (source / 'image-00.png').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == packet['actual_delivered_images'][-1]['sha256']
    assert notes['all_actual_system_dynamic_records_and_messages_read'] is True
    assert notes['complete_raw_own_reply_not_read'] is True
    target = root / (notes['key'] + '-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (target / 'reviewer-notes.json').write_bytes(notes_path.read_bytes())
    orchestrate.save(target / 'review.json', dict(
        schema='source-first-exact-postcheck-history-projection-review-v1', time=time.time(),
        rows=[dict(request=receipt['request'], source_input=str(source),
            source_input_seal_sha256=source_authority['seal_sha256'], actual_images=receipt['images'],
            actor_source_review=label_authority, complete_actor_messages=len(expected),
            only_current_auxiliary_packet_removed_from_checker_projection=True,
            main_actor_history_and_images_unchanged=True,
            actual_system_utf8_sha256=hashlib.sha256(payload['system'].encode()).hexdigest(),
            complete_raw_own_reply_not_read_before_seal=True,
            prior_legal_feedback_visibility=notes['prior_legal_feedback_visibility'],
            judgments_before_reply=notes['judgments_before_reply'])],
        one_reviewer_nonblind_development_diagnosis=True,
        evaluation_only_never_checker_input=True, source_labels_unchanged=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    orchestrate.save(target / 'seal.json', {p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=orchestrate.sha(target / 'review.json'),
                  seal_sha256=orchestrate.sha(target / 'seal.json'))
    orchestrate.save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))
