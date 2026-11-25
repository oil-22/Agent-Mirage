"""Seal explicit visual judgments of original frames after source-first outcome joins."""
import argparse
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def read(path):
    return json.loads(Path(path).read_bytes())


def main(source, sequence):
    assert source.parent == HERE and re.fullmatch(r'\d{2,3}', sequence)
    pointer = HERE / ('postexecution-review-' + sequence + '-created.json')
    assert not pointer.exists()
    supplied = read(source)
    previous = set()
    initial_pointer = HERE / 'initial-two-postexecution-review-created.json'
    if initial_pointer.exists():
        authority = read(initial_pointer)
        folder = Path(authority['root'])
        assert verify_seal(folder) == authority['seal_sha256']
        previous.update(row['id'] for row in read(folder / 'review.json')['reports'])
    for path in HERE.glob('postexecution-review-*-created.json'):
        authority = read(path)
        folder = Path(authority['root'])
        assert verify_seal(folder) == authority['seal_sha256']
        previous.update(row['id'] for row in read(folder / 'review.json')['reports'])
    reports = []
    for supplied_row in supplied['reports']:
        row = dict(supplied_row)
        ident = row['id']
        assert re.fullmatch(r'[0-9a-f]{20}', ident) and ident not in previous
        authority = read(HERE / ('source-review-' + row['source_review_sequence'] + '-created.json'))
        folder = Path(authority['review'])
        assert verify_seal(folder) == authority['seal_sha256']
        assert sha(folder / 'review.json') == authority['review_sha256']
        label = next(label for label in read(folder / 'review.json')['rows'] if label['id'] == ident)
        joinpath = Path(row['execution_join']).resolve()
        assert joinpath.parent.parent == HERE and joinpath.name == 'join.json'
        verify_seal(joinpath.parent)
        joined = read(joinpath)
        assert joined['all_source_labels_sealed_before_this_join']
        outcome = next(item for item in joined['rows'] if item['id'] == ident)
        assert outcome['sealed_source_label'] == label and outcome['accepted'] and outcome['executed']
        assert len(outcome['accepted_events']) == len(outcome['executed_events']) == 1
        assert outcome['executed_events'][0]['data']['proposal']['payload'] == row['expected_payload']
        packet = read(label['public_source_packet'])
        assert packet['actual_delivered_images'][-1]['sha256'] == row['before_image_sha256']
        frame_authority = read(HERE / ('postexecution-frame-' + ident + '-created.json'))
        frame_folder = Path(frame_authority['root'])
        assert verify_seal(frame_folder) == frame_authority['seal_sha256']
        assert sha(frame_folder / 'receipt.json') == frame_authority['receipt_sha256']
        frame = read(frame_folder / 'receipt.json')
        assert frame['candidate_event_sha256'] == label['candidate_event_sha256']
        assert frame['executed_event_sha256'] == outcome['executed_events'][0]['sha256']
        image = frame_folder / 'original-postexecution.png'
        assert sha(image) == frame['next_observation_current_image']['sha256']
        assert row['original_frame_visually_viewed'] is True and len(row['visual_review']) > 20
        assert type(row['normal_action_target_outcome_locally_corroborated']) is bool
        row.update(source_label_authority=authority, original_source_label=label,
            source_label_unchanged=True, accepted=True, executed=True,
            execution_join_sha256=sha(joinpath),
            accepted_event_sha256=outcome['accepted_events'][0]['sha256'],
            executed_event_sha256=outcome['executed_events'][0]['sha256'],
            postexecution_frame_authority=frame_authority,
            original_postexecution_image=str(image), original_postexecution_image_sha256=sha(image))
        reports.append(row)
        previous.add(ident)
    folder = HERE / ('postexecution-review-' + str(time.time_ns()))
    folder.mkdir()
    (folder / 'supplied-review.json').write_bytes(source.read_bytes())
    (folder / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(folder / 'review.json', dict(time=time.time(), reports=reports,
        source_labels_sealed_before_current_outcome_join=True,
        original_source_labels_unchanged=True, source_reviewer_count=1,
        not_fully_blind_or_independent_human_gold=True,
        normal_actions_observed_in_this_review=sum(row['normal_action_target_outcome_locally_corroborated'] for row in reports),
        trajectory_Mirage=None, official_score=None, overall_false_rejection_rate=None,
        defense_efficacy_established=False, new_model_GUI_capture_action_scorer_calls=0, goal='active'))
    save(folder / 'seal.json', {p.name: sha(p) for p in folder.iterdir() if p.is_file()})
    result = dict(root=str(folder), review_sha256=sha(folder / 'review.json'), seal_sha256=sha(folder / 'seal.json'))
    save(pointer, result)
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--sequence', required=True)
    args = parser.parse_args()
    main(args.input.resolve(), args.sequence)
