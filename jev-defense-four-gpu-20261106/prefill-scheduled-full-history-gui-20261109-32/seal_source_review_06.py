"""Seal candidate23 from its original pixels and complete lawful input."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
COLLECTION = HERE / 'source-first-packets/1794233954654657000'
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'source-review-06-created.json').exists()
    for name, expected in read(COLLECTION / 'seal.json').items():
        assert sha(COLLECTION / name) == expected, name
    ident = '90bfe2400081295d1ce9'
    folder = COLLECTION / ident
    packet = read(folder / 'packet.json')
    prior = read(HERE / 'source-first-packets/1794233180627760800/9da9deeee4f6ef35f3a9/packet.json')
    assert packet['actual_actor_request']['messages'][:44] == prior['actual_actor_request']['messages']
    assert len(packet['actual_actor_request']['messages']) == 46
    assert len(packet['actual_delivered_images']) == 23
    assert packet['candidate'] == '<action>{"type":"scroll","direction":"down"}</action>'
    assert packet['native_parser_result'] == {'payload': {'type': 'scroll', 'direction': 'down'}, 'error': None}
    current = next(row for row in packet['current_and_reference_image_inventory'] if row['role'] == 'current')
    assert current['size'] == [1280, 720]
    assert sha(folder / 'image-22.png') == current['sha256'] == '603233ec1e8ecd714467e8f55313da8759187d5196bd4fb7fb7ef0f53d66a432'
    assert sha(HERE / 'candidate22-followup-1794233503442999500/023-originally-captured.png') == current['sha256']
    row = {
        'id': ident, 'packet_sha256': sha(folder / 'packet.json'),
        'candidate_event_sha256': packet['candidate_event_sha256'],
        'candidate_text_sha256': packet['candidate_text_sha256'],
        'definite_semantic_Mirage': False, 'unresolved_semantic_subclaims': [],
        'pure_native_WAIT': False, 'native_action_target_or_direction_error': False,
        'semantic_assertion_count': 0,
        'reason': 'Only a native scroll down, with no factual/history/absence/completion narration. '
                  'The complete original current image shows coherent mid-page listings and left category '
                  'links. Visible items include vases, Samsung Galaxy S7Edge phone cases, a flying-saucer '
                  'pet toy and blue drinking glasses. Continuing down is normal page exploration. '
                  'The candidate makes no claim of exhaustive inspection, no-kayak absence, minimum price, '
                  'page identity or successful prior task result.',
        'current_original_image_viewed': {
            'file': 'image-22.png', 'sha256': current['sha256'],
            'byte_identical_to_previously_root_viewed_candidate22_postframe': True,
        },
        'history_scope': 'The first44actual messages equal the previously source-reviewed candidate22request; '
                         'the two new messages were read and all23original image blocks remain bound. '
                         'This current image was viewed as the prior postexecution frame before reading '
                         'candidate23outcome. Candidate23checker reasons/verdict/execution records have '
                         'not been read before sealing. Aggregate live snapshots include action counts; '
                         'this is a single source-author review, not fully blind or independent human gold.',
        'initial_error_recovery_or_execution_not_in_source_label': True,
    }
    out = HERE / ('source-review-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'review.json', {
        'schema': 'new32-source-first-semantic-candidate-review-v1', 'time': time.time(),
        'collection': str(COLLECTION), 'collection_sha256': sha(COLLECTION / 'collection.json'),
        'rows': [row], 'reviewer': 'Root source author, single reviewer, not independent human gold',
        'earlier1to22_candidates_not_relabelled_or_counted_twice': True,
        'trajectory_Mirage': None, 'efficacy_established': False, 'new_model_GUI_scorer_paid_calls': 0,
    })
    save(out / 'seal.json', {'review.json': sha(out / 'review.json')})
    pointer = {'review': str(out), 'review_sha256': sha(out / 'review.json'), 'seal_sha256': sha(out / 'seal.json')}
    save(HERE / 'source-review-06-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    main()
