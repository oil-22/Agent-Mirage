"""Seal reviewer notes for one actual image-only readiness input, before reply."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import time

import orchestrate


def verify(folder):
    for name, expected in json.loads((folder / 'seal.json').read_bytes()).items():
        path = folder / name
        assert path.resolve().is_relative_to(folder.resolve())
        assert orchestrate.sha(path) == expected
    return orchestrate.sha(folder / 'seal.json')


def main(notes_path):
    root = orchestrate.HERE
    assert notes_path.parent == root
    notes = json.loads(notes_path.read_bytes())
    key = notes['key']
    assert re.fullmatch(r'[a-z][a-z0-9-]+', key)
    pointer = root / (key + '-created.json')
    assert not pointer.exists()
    authority = json.loads((root / notes['source_pointer']).read_bytes())
    source = Path(authority['root'])
    assert source.parent == root and verify(source) == authority['seal_sha256']
    assert orchestrate.sha(source / 'receipt.json') == authority['receipt_sha256']
    payload = json.loads((source / 'payload.json').read_bytes())
    receipt = json.loads((source / 'receipt.json').read_bytes())
    view = payload['view']
    assert payload['operation'] == 'judge' and payload['candidate'] is None
    assert view['recent_action'] == view['execution_feedback'] == ''
    assert len(view['images']) == len(view['messages']) == 1
    image = view['images'][0]
    assert image['role'] == 'current'
    raw = base64.b64decode(image['raw_base64'], validate=True)
    assert raw == (source / 'image-00.png').read_bytes()
    provenance = json.loads(view['messages'][0]['content'])
    assert set(provenance) == {'current_image_provenance_only'}
    assert provenance['current_image_provenance_only'][0]['sha256'] == hashlib.sha256(raw).hexdigest()
    assert notes['all_actual_system_and_messages_read'] is True
    assert notes['complete_original_image_viewed'] is True
    assert notes['own_reply_not_read'] is True
    target = root / (key + '-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (target / 'reviewer-notes.json').write_bytes(notes_path.read_bytes())
    orchestrate.save(target / 'review.json', dict(
        schema='actual-current-image-only-readiness-input-review-v1',
        time=time.time(),
        rows=[dict(request=receipt['request'], source_input=str(source),
                   source_input_seal_sha256=authority['seal_sha256'],
                   actual_images=receipt['images'],
                   actual_system_utf8_sha256=hashlib.sha256(payload['system'].encode()).hexdigest(),
                   all_actual_system_and_messages_read=True,
                   full_original_image_independently_viewed=True,
                   raw_reply_not_read_before_this_seal=True,
                   judgments_before_reply=notes['judgments_before_reply'])],
        raw_own_replies_not_read_before_this_seal=True,
        one_reviewer_not_fully_blind_or_human_gold=True,
        existing_source_labels_and_original_runtime_unchanged=True,
        evaluation_only_never_checker_input=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    orchestrate.save(target / 'seal.json', {
        p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=orchestrate.sha(target / 'review.json'),
                  seal_sha256=orchestrate.sha(target / 'seal.json'))
    orchestrate.save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--notes', type=Path, required=True)
    main(parser.parse_args().notes.resolve())
