"""Seal an actual current-only visual probe before its own native reply.

Read-only evaluation observer, not a runtime validator or new inference path.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import time

import orchestrate


def main(notes_path):
    root = orchestrate.HERE
    assert notes_path.parent == root
    notes = json.loads(notes_path.read_bytes())
    assert re.fullmatch(r'[a-z][a-z0-9-]+', notes['key'])
    pointer = root / (notes['key'] + '-created.json')
    assert not pointer.exists()
    authority = json.loads((root / notes['source_pointer']).read_bytes())
    source = Path(authority['root'])
    assert source.parent == root
    for name, expected in json.loads((source / 'seal.json').read_bytes()).items():
        item = source / name
        assert item.resolve().is_relative_to(source.resolve()) and orchestrate.sha(item) == expected
    assert orchestrate.sha(source / 'seal.json') == authority['seal_sha256']
    assert orchestrate.sha(source / 'receipt.json') == authority['receipt_sha256']
    payload = json.loads((source / 'payload.json').read_bytes())
    receipt = json.loads((source / 'receipt.json').read_bytes())
    assert payload['operation'] == 'judge' and payload['candidate'] is None
    view = payload['view']
    assert view['recent_action'] == view['execution_feedback'] == ''
    assert len(view['messages']) == len(view['images']) == 1
    assert view['messages'][0]['role'] == 'user' and isinstance(view['messages'][0]['content'], str)
    assert view['images'][0]['role'] == 'current'
    raw = base64.b64decode(view['images'][0]['raw_base64'], validate=True)
    assert raw == (source / 'image-00.png').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == notes['reviewed_original_image_sha256']
    assert notes['all_actual_system_and_question_read'] is True
    assert notes['complete_original_image_viewed'] is True
    assert notes['own_reply_not_read'] is True
    target = root / (notes['key'] + '-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (target / 'reviewer-notes.json').write_bytes(notes_path.read_bytes())
    orchestrate.save(target / 'review.json', dict(
        schema='source-first-current-only-visual-probe-input-review-v1', time=time.time(),
        rows=[dict(request=receipt['request'], source_input=str(source),
            source_input_seal_sha256=authority['seal_sha256'], actual_images=receipt['images'],
            actual_system_utf8_sha256=hashlib.sha256(payload['system'].encode()).hexdigest(),
            actual_single_question_utf8_sha256=hashlib.sha256(view['messages'][0]['content'].encode()).hexdigest(),
            all_actual_system_and_question_read=True, complete_original_image_independently_viewed=True,
            raw_reply_not_read_before_this_seal=True,
            judgments_before_reply=notes['judgments_before_reply'])],
        one_reviewer_nonblind_development_diagnosis=True,
        evaluation_only_never_checker_input=True, existing_source_labels_unchanged=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    orchestrate.save(target / 'seal.json', {p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=orchestrate.sha(target / 'review.json'),
                  seal_sha256=orchestrate.sha(target / 'seal.json'))
    orchestrate.save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))
