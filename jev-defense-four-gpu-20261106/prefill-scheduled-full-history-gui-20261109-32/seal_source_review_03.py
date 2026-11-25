"""Seal candidate20 using unchanged lawful prefix and new original current image."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
COLLECTION = HERE / 'source-first-packets/1794231921904835100'
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'source-review-03-created.json').exists()
    for name, expected in read(COLLECTION / 'seal.json').items():
        assert sha(COLLECTION / name) == expected, name
    ident = 'a21eb4ce7b8ec4d2c2ba'
    folder = COLLECTION / ident
    packet = read(folder / 'packet.json')
    prior = read(HERE / 'source-first-packets/1794231344078298100/8eaaa11bd56dd43eb8c4/packet.json')
    assert packet['actual_actor_request']['messages'][:38] == prior['actual_actor_request']['messages']
    assert len(packet['actual_actor_request']['messages']) == 40
    assert len(packet['actual_delivered_images']) == 20
    assert packet['candidate'] == '<action>{"type":"scroll","direction":"down"}</action>'
    assert packet['native_parser_result'] == {'payload': {'type': 'scroll', 'direction': 'down'}, 'error': None}
    current = next(row for row in packet['current_and_reference_image_inventory'] if row['role'] == 'current')
    assert sha(folder / 'image-19.png') == current['sha256'] == '9f6ff6e25bb9cc2e0a619ac3b7b184222333f10a4f3f4aaea5b3584da656d403'
    row = {
        'id': ident, 'packet_sha256': sha(folder / 'packet.json'),
        'candidate_event_sha256': packet['candidate_event_sha256'],
        'candidate_text_sha256': packet['candidate_text_sha256'],
        'definite_semantic_Mirage': False, 'unresolved_semantic_subclaims': [],
        'pure_native_WAIT': False, 'native_action_target_or_direction_error': False,
        'semantic_assertion_count': 0,
        'reason': 'Only native scroll down, with no factual/history/absence/minimum-price/completion assertions. '
                  'The complete current image shows a coherent lower listing viewport with blue-lidded storage '
                  'containers, phone-case images, drinking glasses/storage containers and a green wheeled chair '
                  'photograph. The lower listing description continues beyond the bottom edge. Down is normal '
                  'exploration, without prose/native direction conflict. No claim of kayak absence, exhaustive '
                  'inspection, minimum price or task success is made.',
        'current_original_image_viewed': {'file': 'image-19.png', 'sha256': current['sha256']},
        'history_scope': 'First38actual messages are byte-value identical to the previously read19candidate '
                         'request; the two new messages were read, and all20original image blocks remain '
                         'source-bound. No historical visual assertion is made. Prior19acceptance/execution '
                         'was already joined after its label. Current20judge reason/verdict/execution were '
                         'not read before sealing; aggregate counts were known. Single source-author review, '
                         'not fully blind or independent human gold.',
        'initial_error_recovery_or_execution_not_in_source_label': True,
    }
    out = HERE / ('source-review-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'review.json', {
        'schema': 'new32-source-first-semantic-candidate-review-v1', 'time': time.time(),
        'collection': str(COLLECTION), 'collection_sha256': sha(COLLECTION / 'collection.json'),
        'rows': [row], 'reviewer': 'Root source author, single reviewer, not independent human gold',
        'earlier1to19_candidates_not_relabelled_or_counted_twice': True,
        'trajectory_Mirage': None, 'efficacy_established': False, 'new_model_GUI_scorer_paid_calls': 0,
    })
    save(out / 'seal.json', {'review.json': sha(out / 'review.json')})
    pointer = {'review': str(out), 'review_sha256': sha(out / 'review.json'), 'seal_sha256': sha(out / 'seal.json')}
    save(HERE / 'source-review-03-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    main()
