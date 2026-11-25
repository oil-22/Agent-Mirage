"""Seal an actual original-image/locator point-reader input before its reply.

Evaluation observer only. Never changes a model request, runtime or label.
"""
import argparse
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
    key = notes['key']
    assert re.fullmatch(r'[a-z][a-z0-9-]+', key)
    pointer = root / (key + '-created.json')
    assert not pointer.exists()
    authority = json.loads((root / notes['source_pointer']).read_bytes())
    source = Path(authority['root'])
    assert source.parent == root
    for name, expected in json.loads((source / 'seal.json').read_bytes()).items():
        item = source / name
        assert item.resolve().is_relative_to(source.resolve())
        assert orchestrate.sha(item) == expected
    assert orchestrate.sha(source / 'seal.json') == authority['seal_sha256']
    receipt = json.loads((source / 'receipt.json').read_bytes())
    assert orchestrate.sha(source / 'receipt.json') == authority['receipt_sha256']
    payload = json.loads((source / 'payload.json').read_bytes())
    wire = json.loads((source / 'external-wire.json').read_bytes())
    assert wire['payload'] == payload and payload['operation'] == 'judge'
    candidate, view = payload['candidate'], payload['view']
    assert candidate['mode'] == 'point_probe' and candidate['coordinate_space'] == 'pixels'
    assert set(candidate) == {'mode', 'coordinate_space', 'original_size', 'pixel_point'}
    assert view['recent_action'] == view['execution_feedback'] == ''
    assert len(view['images']) == len(receipt['images']) == 2
    assert [v['role'] for v in view['images']] == ['current', 'reference']
    assert len(view['messages']) == 1
    for index, image in enumerate(view['images']):
        raw = base64.b64decode(image['raw_base64'], validate=True)
        frozen = receipt['images'][index]
        assert raw == (source / frozen['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == frozen['sha256']
        assert frozen['size'] == candidate['original_size']
    assert receipt['images'][0]['sha256'] == notes['reviewed_original_image_sha256']
    assert notes['all_actual_system_and_messages_read'] is True
    assert notes['both_complete_images_independently_viewed'] is True
    assert notes['own_reply_not_read'] is True
    target = root / (key + '-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (target / 'reviewer-notes.json').write_bytes(notes_path.read_bytes())
    orchestrate.save(target / 'review.json', dict(
        schema='source-first-original-and-locator-point-input-review-v1',
        time=time.time(), rows=[dict(request=receipt['request'], source_input=str(source),
            source_input_seal_sha256=authority['seal_sha256'], actual_images=receipt['images'],
            candidate_geometry=candidate,
            actual_system_utf8_sha256=hashlib.sha256(payload['system'].encode()).hexdigest(),
            all_actual_system_and_messages_read=True,
            both_complete_images_independently_viewed=True,
            raw_reply_not_read_before_this_seal=True,
            judgments_before_reply=notes['judgments_before_reply'])],
        raw_own_reply_not_read_before_this_seal=True,
        one_reviewer_not_fully_blind_or_human_gold=True,
        source_labels_and_original_runtime_unchanged=True,
        evaluation_only_never_checker_input=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    orchestrate.save(target / 'seal.json', {p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=orchestrate.sha(target / 'review.json'),
                  seal_sha256=orchestrate.sha(target / 'seal.json'))
    orchestrate.save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--notes', type=Path, required=True)
    main(parser.parse_args().notes.resolve())
