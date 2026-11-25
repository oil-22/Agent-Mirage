"""Seal a manually authored source review; never infer labels from detector output."""
import argparse
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main(input_path, pointer_name):
    assert Path(pointer_name).name == pointer_name and pointer_name.endswith('-created.json')
    assert not (HERE / pointer_name).exists()
    manual = read(input_path)
    collection = HERE / manual['collection']
    for name, expected in read(collection / 'seal.json').items():
        assert sha(collection / name) == expected, name
    folder = collection / manual['id']
    packet = read(folder / 'packet.json')
    previous = read(HERE / manual['previous_packet'])
    prefix = manual['previous_message_count']
    assert len(previous['actual_actor_request']['messages']) == prefix
    assert packet['actual_actor_request']['messages'][:prefix] == previous['actual_actor_request']['messages']
    assert len(packet['actual_actor_request']['messages']) == manual['message_count']
    assert len(packet['actual_delivered_images']) == manual['image_count']
    assert packet['candidate'] == manual['candidate']
    assert packet['native_parser_result'] == manual['native_parser_result']
    current = next(row for row in packet['current_and_reference_image_inventory'] if row['role'] == 'current')
    assert sha(folder / manual['current_image_file']) == current['sha256'] == manual['current_image_sha256']
    assert manual['original_current_image_actually_viewed'] is True
    assert manual['new_history_messages_actually_read'] is True
    assert manual['current_checker_reasons_outcomes_not_read_before_seal'] is True
    labels = manual['source_labels']
    assert labels['definite_semantic_Mirage'] in [True, False, None]
    row = dict(labels, id=manual['id'], packet_sha256=sha(folder / 'packet.json'),
        candidate_event_sha256=packet['candidate_event_sha256'], candidate_text_sha256=packet['candidate_text_sha256'],
        reason=manual['reason'], history_scope=manual['history_scope'],
        current_original_image_viewed={'file': manual['current_image_file'], 'sha256': current['sha256']},
        initial_error_recovery_or_execution_not_in_source_label=True)
    out = HERE / ('source-review-' + str(time.time_ns()))
    out.mkdir()
    (out / 'manual-review-input.json').write_bytes(Path(input_path).read_bytes())
    save(out / 'review.json', {
        'schema': 'new32-source-first-semantic-candidate-review-v1', 'time': time.time(),
        'collection': str(collection), 'collection_sha256': sha(collection / 'collection.json'),
        'rows': [row], 'reviewer': 'Root source author, single reviewer, not independent human gold',
        'manual_labels_never_checker_input': True,
        'earlier_candidates_not_relabelled_or_counted_twice': True,
        'trajectory_Mirage': None, 'efficacy_established': False, 'new_model_GUI_scorer_paid_calls': 0,
    })
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    pointer = {'review': str(out), 'review_sha256': sha(out / 'review.json'), 'seal_sha256': sha(out / 'seal.json')}
    save(HERE / pointer_name, pointer)
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--pointer', required=True)
    args = parser.parse_args()
    main(args.input.resolve(), args.pointer)
