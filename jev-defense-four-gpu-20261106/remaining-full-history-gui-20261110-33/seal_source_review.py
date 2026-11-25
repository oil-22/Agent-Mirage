"""Seal explicitly supplied image/history/candidate judgments, not detector labels."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, save, sha


def main(source, sequence):
    assert source.parent == HERE and re.fullmatch(r'\d{2,3}', sequence)
    pointer = HERE / ('source-review-' + sequence + '-created.json')
    assert not pointer.exists(), 'Existing labels remain immutable'
    supplied = json.loads(source.read_bytes())
    collection = Path(supplied['collection'])
    assert collection.parent == HERE / 'source-first-packets'
    for name, expected in json.loads((collection / 'seal.json').read_bytes()).items():
        assert (collection / name).resolve().is_relative_to(collection.resolve())
        assert sha(collection / name) == expected, name
    previous = set()
    for path in HERE.glob('source-review-*-created.json'):
        if not re.fullmatch(r'source-review-\d+-created\.json', path.name):
            continue
        authority = json.loads(path.read_bytes());old = Path(authority['review'])
        assert sha(old / 'review.json') == authority['review_sha256']
        previous.update(row['candidate_event_sha256'] for row in json.loads((old / 'review.json').read_bytes())['rows'])
    rows = []
    for supplied_row in supplied['rows']:
        row = dict(supplied_row)
        packet = collection / row['id'] / 'packet.json'
        public = json.loads(packet.read_bytes())
        assert row['candidate_event_sha256'] == public['candidate_event_sha256']
        assert row['candidate_event_sha256'] not in previous
        assert public['checker_labels_current_acceptance_execution_scoring_private_delivery_excluded'] is True
        for field in ['candidate_semantic_mirage', 'native_action_error']:
            assert row[field] is None or type(row[field]) is bool
        assert type(row['pure_native_WAIT_excluded']) is bool
        expected_images = ['image-%02d.png' % n for n in range(len(public['actual_delivered_images']))]
        assert row['source_image_files_viewed'] == expected_images
        for index, filename in enumerate(expected_images):
            assert sha(collection / row['id'] / filename) == public['actual_delivered_images'][index]['sha256']
        assert hashlib.sha256(public['candidate'].encode()).hexdigest() == public['candidate_text_sha256']
        row.update(candidate_text_sha256=public['candidate_text_sha256'], actor_request_body_sha256=public['actor_request_body_sha256'],
            packet_sha256=sha(packet), complete_supplied_images=len(expected_images), public_source_packet=str(packet))
        rows.append(row);previous.add(row['candidate_event_sha256'])
    root = HERE / ('source-review-' + str(time.time_ns()));root.mkdir()
    (root / 'supplied-source-review.json').write_bytes(source.read_bytes())
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(root / 'review.json', dict(time=time.time(), rows=rows, independent_current_checker_execution_score_join_not_performed=True,
        legal_prior_feedback_and_auxiliary_history_retained=True, source_reviewer_count=1,
        not_fully_blind_or_human_gold=True, whole_trajectory_Mirage_or_efficacy_not_established=True,
        new_model_GUI_scorer_calls=0))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    authority = dict(review=str(root), review_sha256=sha(root / 'review.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, authority)
    print(json.dumps(authority))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--sequence', required=True)
    args = parser.parse_args()
    main(args.input.resolve(), args.sequence)
