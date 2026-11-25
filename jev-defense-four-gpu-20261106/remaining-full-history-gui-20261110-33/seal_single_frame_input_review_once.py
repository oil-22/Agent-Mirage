"""Seal reviewer-authored input notes before reading each own native reply."""
import argparse
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def main(notes_path):
    assert notes_path.parent == HERE
    notes = json.loads(notes_path.read_bytes())
    key = notes['key']
    assert re.fullmatch(r'[a-z][a-z0-9-]+', key)
    pointer = HERE / (key + '-created.json')
    assert not pointer.exists()
    actor = json.loads((HERE / notes['actor_review_pointer']).read_bytes())
    actor_root = Path(actor['review'])
    assert verify_seal(actor_root) == actor['seal_sha256']
    assert sha(actor_root / 'review.json') == actor['review_sha256']
    old_source = json.loads((HERE / notes['same_system_source_pointer']).read_bytes())
    old_root = Path(old_source['root'])
    assert verify_seal(old_root) == old_source['seal_sha256']
    system = json.loads((old_root / 'payload.json').read_bytes())['system']
    rows = []
    for item in notes['rows']:
        ident = item['request']
        assert re.fullmatch(r'\d{4}', ident)
        assert item['all_actual_source_text_read'] is True
        assert item['complete_original_image_viewed'] is True
        assert item['own_reply_not_read'] is True
        authority = json.loads((HERE / item['source_pointer']).read_bytes())
        source = Path(authority['root'])
        assert source.parent == HERE
        assert verify_seal(source) == authority['seal_sha256']
        payload = json.loads((source / 'payload.json').read_bytes())
        receipt = json.loads((source / 'receipt.json').read_bytes())
        assert payload['system'] == system and payload['candidate'] is None
        assert payload['operation'] == 'judge'
        assert len(payload['view']['images']) == len(payload['view']['messages']) == 1
        assert payload['view']['images'][0]['role'] == 'reference'
        assert receipt['request'] == ident
        rows.append(dict(request=ident, source_input=str(source),
            source_input_seal_sha256=authority['seal_sha256'], actual_images=receipt['images'],
            all_actual_system_and_messages_read=True,
            full_original_image_independently_viewed=True,
            raw_reply_not_read_before_this_seal=True,
            judgments_before_reply=item['judgments_before_reply']))
    assert len({row['request'] for row in rows}) == len(rows)
    target = HERE / (key + '-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (target / 'reviewer-notes.json').write_bytes(notes_path.read_bytes())
    save(target / 'review.json', dict(schema='source-first-single-frame-input-review-v1',
        time=time.time(), rows=rows, actor_source_label_authority=actor,
        previous_reviewed_identical_system_source=old_source,
        raw_own_replies_not_read_before_this_seal=True,
        one_reviewer_not_fully_blind_or_human_gold=True,
        existing_source_labels_and_original_runtime_unchanged=True,
        evaluation_only_never_checker_input=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), review_sha256=sha(target / 'review.json'),
                  seal_sha256=sha(target / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--notes', type=Path, required=True)
    main(parser.parse_args().notes.resolve())
