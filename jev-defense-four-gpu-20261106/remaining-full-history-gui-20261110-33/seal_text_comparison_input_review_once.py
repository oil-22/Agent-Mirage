"""Seal text-only comparison inputs,with optional exact prior-output bindings."""
import argparse
import copy
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def frozen_pointer(name):
    value = json.loads((HERE / name).read_bytes())
    root = Path(value['root'])
    assert root.parent == HERE and verify_seal(root) == value['seal_sha256']
    return value, root


def main(notes_path):
    assert notes_path.parent == HERE
    notes = json.loads(notes_path.read_bytes())
    key = notes['key']
    assert re.fullmatch(r'[a-z][a-z0-9-]+', key)
    pointer = HERE / (key + '-created.json')
    assert not pointer.exists()
    source_authority, source = frozen_pointer(notes['source_pointer'])
    payload = json.loads((source / 'payload.json').read_bytes())
    assert payload['operation'] == 'judge' and not payload['view']['images']
    assert len(payload['view']['messages']) == 1
    pair = json.loads(payload['candidate'])
    assert pair == json.loads(payload['view']['messages'][0]['content'])
    assert notes['all_actual_system_and_comparison_text_read'] is True
    assert notes['own_reply_not_read'] is True
    bindings = []
    if notes.get('verify_completion90_and_original_four_frozen_records'):
        previous, previous_root = frozen_pointer('source14-completion90-reply-created.json')
        raw = json.loads((previous_root / '0090-raw.txt').read_bytes())
        completed = copy.deepcopy(pair['original_completion_image_reading'])
        for citation in completed['evidence']:
            citation.pop('resolved_box_pixels', None)
        assert completed == raw
        relation, relation_root = frozen_pointer('source14-price-relation-0089-source-created.json')
        original_pair = json.loads(json.loads((relation_root / 'payload.json').read_bytes())['candidate'])
        records = original_pair['independent_original_frame_records']
        for row in pair['frozen_source_frame_records']:
            index = row['original_completion_image_index']
            assert index in {0,10,11,12}
            assert row['independent_single_frame'] == records[index]
            assert row['source_image_sha256'] == records[index]['original_source_frame']['sha256']
            bindings.append(dict(original_completion_image_index=index,
                image_sha256=row['source_image_sha256'],
                frozen_record_sha256=records[index]['frozen_sha256']))
        assert {v['original_completion_image_index'] for v in bindings} == {0,10,11,12}
    root = HERE / (key + '-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (root / 'reviewer-notes.json').write_bytes(notes_path.read_bytes())
    save(root / 'review.json', dict(schema='source-first-text-comparison-input-review-v1',
        time=time.time(), rows=[dict(request=notes['request'], source_input=str(source),
            source_input_seal_sha256=source_authority['seal_sha256'], actual_images=[],
            all_actual_system_and_comparison_text_read=True, raw_reply_not_read_before_this_seal=True,
            judgments_before_reply=notes['judgments_before_reply'])],
        optional_exact_prior_completion_and_frozen_record_bindings=bindings,
        raw_own_reply_not_read_before_this_seal=True,
        main_source_labels_and_original_outputs_unchanged=True,
        one_reviewer_nonblind_development_diagnosis=True,
        evaluation_only_never_checker_input=True,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    save(root / 'seal.json', {p.name:sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), review_sha256=sha(root / 'review.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--notes', type=Path, required=True)
    main(parser.parse_args().notes.resolve())
