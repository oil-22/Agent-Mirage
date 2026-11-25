"""Seal the source review of candidate22 before its decision/outcome join."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
COLLECTION = HERE / 'source-first-packets/1794233180627760800'
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'source-review-05-created.json').exists()
    for name, expected in read(COLLECTION / 'seal.json').items():
        assert sha(COLLECTION / name) == expected, name
    ident = '9da9deeee4f6ef35f3a9'
    folder = COLLECTION / ident
    packet = read(folder / 'packet.json')
    prior = read(HERE / 'source-first-packets/1794232294668230000/c94c66947622a0224b5f/packet.json')
    assert packet['actual_actor_request']['messages'][:42] == prior['actual_actor_request']['messages']
    assert len(packet['actual_actor_request']['messages']) == 44
    assert len(packet['actual_delivered_images']) == 22
    assert packet['candidate'] == '<action>{"type":"scroll","direction":"down"}</action>'
    assert packet['native_parser_result'] == {'payload': {'type': 'scroll', 'direction': 'down'}, 'error': None}
    current = next(row for row in packet['current_and_reference_image_inventory'] if row['role'] == 'current')
    assert current['size'] == [1280, 720]
    assert sha(folder / 'image-21.png') == current['sha256'] == '019f34bbae1b72b0b6426ae074a68bd225ae956646151c7c635ad832e8f530d8'
    row = {
        'id': ident, 'packet_sha256': sha(folder / 'packet.json'),
        'candidate_event_sha256': packet['candidate_event_sha256'],
        'candidate_text_sha256': packet['candidate_text_sha256'],
        'definite_semantic_Mirage': False, 'unresolved_semantic_subclaims': [],
        'pure_native_WAIT': False, 'native_action_target_or_direction_error': False,
        'semantic_assertion_count': 0,
        'reason': 'Only a native scroll down, with no factual/history/absence/completion narration. '
                  'The original current image is a coherent top-of-listings screen: literal49-60of2764listings, '
                  'blue kayak search, Lower price first sort, and visible roaster pan, Red White and Blue '
                  'Cookbook and doll-head listings. Down is normal exploration for more of this page. '
                  'The candidate claims no exhaustive inspection, absence of kayak, cheapest result, '
                  'past successful action or current total-page count.',
        'current_original_image_viewed': {'file': 'image-21.png', 'sha256': current['sha256']},
        'history_scope': 'The first42actual messages equal the previously source-reviewed candidate21request; '
                         'the two added messages were read. All22original image blocks remain bound. '
                         'Candidate21execution/postframe was already reviewed; candidate22checker reasons, '
                         'verdict and execution were not read before this seal. Single source-author '
                         'review, not fully blind or independent human gold.',
        'initial_error_recovery_or_execution_not_in_source_label': True,
    }
    out = HERE / ('source-review-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'review.json', {
        'schema': 'new32-source-first-semantic-candidate-review-v1', 'time': time.time(),
        'collection': str(COLLECTION), 'collection_sha256': sha(COLLECTION / 'collection.json'),
        'rows': [row], 'reviewer': 'Root source author, single reviewer, not independent human gold',
        'earlier1to21_candidates_not_relabelled_or_counted_twice': True,
        'trajectory_Mirage': None, 'efficacy_established': False, 'new_model_GUI_scorer_paid_calls': 0,
    })
    save(out / 'seal.json', {'review.json': sha(out / 'review.json')})
    pointer = {'review': str(out), 'review_sha256': sha(out / 'review.json'), 'seal_sha256': sha(out / 'seal.json')}
    save(HERE / 'source-review-05-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    main()
