"""Seal bounded reviewer notes against source-first inputs and exact replies."""
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
    source = json.loads((HERE / notes['source_review_pointer']).read_bytes())
    replies = json.loads((HERE / notes['reply_export_pointer']).read_bytes())
    for authority in [source, replies]:
        folder = Path(authority['root'])
        assert folder.parent == HERE and verify_seal(folder) == authority['seal_sha256']
    source_ids = {row['request'] for row in json.loads((Path(source['root']) / 'review.json').read_bytes())['rows']}
    actual_ids = {row['request'] for row in json.loads((Path(replies['root']) / 'receipt.json').read_bytes())['records']}
    rows = []
    for item in notes['rows']:
        ident = item['request']
        assert ident in source_ids & actual_ids
        raw_path = Path(replies['root']) / (ident + '-raw.txt')
        decoded = json.loads(raw_path.read_bytes())
        rows.append(dict(item, raw_reply_file=str(raw_path), raw_reply_sha256=sha(raw_path),
            raw_status=decoded.get('status'), raw_loading=decoded.get('loading'),
            raw_output_modified=False))
    assert len({row['request'] for row in rows}) == len(rows)
    root = HERE / (key + '-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (root / 'reviewer-notes.json').write_bytes(notes_path.read_bytes())
    save(root / 'review.json', dict(schema='source-first-native-reply-bounded-semantic-review-v1',
        time=time.time(), source_input_review=source, actual_reply_export=replies, rows=rows,
        source_labels_and_original_outcomes_unchanged=True,
        one_reviewer_nonblind_development_diagnosis=True,
        no_new_main_candidate_or_trajectory_label=True,
        evaluation_only_never_checker_input=True,
        efficacy_or_general_semantic_accuracy_established=False,
        runtime_input_prompt_validator_or_budget_modified=False,
        new_model_GUI_capture_action_scorer_paid_calls=0))
    (root / 'report.md').write_text(notes['report_markdown'], encoding='utf8')
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), review_sha256=sha(root / 'review.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--notes', type=Path, required=True)
    main(parser.parse_args().notes.resolve())
