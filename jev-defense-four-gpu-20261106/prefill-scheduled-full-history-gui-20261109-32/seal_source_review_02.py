"""Seal candidate19 from original pixels and lawful history before outcome join."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
COLLECTION = HERE / 'source-first-packets/1794231344078298100'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'source-review-02-created.json').exists()
    for name, expected in json.loads((COLLECTION / 'seal.json').read_bytes()).items():
        assert sha(COLLECTION / name) == expected, name
    ident = '8eaaa11bd56dd43eb8c4'
    folder = COLLECTION / ident
    packet = json.loads((folder / 'packet.json').read_bytes())
    assert packet['candidate'] == '<action>{"type":"scroll","direction":"down"}</action>'
    assert len(packet['actual_actor_request']['messages']) == 38
    assert len(packet['actual_delivered_images']) == 19
    assert packet['native_parser_result'] == {'payload': {'type': 'scroll', 'direction': 'down'}, 'error': None}
    current = next(im for im in packet['current_and_reference_image_inventory'] if im['role'] == 'current')
    assert current['sha256'] == 'd10cae5eadb5f8d2d67f7787fedeb8ac174d27b286c881f019c285841f112490'
    assert sha(folder / 'image-18.png') == current['sha256']
    row = {
        'id': ident, 'packet_sha256': sha(folder / 'packet.json'),
        'candidate_event_sha256': packet['candidate_event_sha256'],
        'candidate_text_sha256': packet['candidate_text_sha256'],
        'definite_semantic_Mirage': False, 'unresolved_semantic_subclaims': [],
        'pure_native_WAIT': False, 'native_action_target_or_direction_error': False,
        'semantic_assertion_count': 0,
        'reason': 'Only native scroll down, without factual, historical, absence, minimum-price or completion assertions. '
                  'The original current1280x720image shows a coherent middle listing viewport, with blue coffee mugs, '
                  'an America Revolutionaries book, antique bottles and blue/red tote bags. The tote listing continues '
                  'beyond the lower image edge. Down is grounded exploration; no direction conflict is present. '
                  'This does not establish complete page inspection, absence of a kayak, or task success.',
        'current_original_image_viewed': {'file': 'image-18.png', 'sha256': current['sha256']},
        'history_scope': 'All38actual lawful message roles/order and all unique text read;19full original image blocks '
                         'remain source-bound. Earlier reviewed prefix retained; no historical visual claim is made '
                         'by this candidate. Prior18execution is known from its previously sealed review/join. '
                         'Current19judge reason/verdict/execution were not read before this label. Aggregate live '
                         'counts were known. Single source-author review, not fully blind or independent human gold.',
        'initial_error_recovery_or_execution_not_in_source_label': True,
    }
    target = HERE / ('source-review-' + str(time.time_ns()))
    target.mkdir()
    save(target / 'review.json', {
        'schema': 'new32-source-first-semantic-candidate-review-v1', 'time': time.time(),
        'collection': str(COLLECTION), 'collection_sha256': sha(COLLECTION / 'collection.json'),
        'rows': [row], 'reviewer': 'Root source author, single reviewer, not independent human gold',
        'original_pending_candidate17_and_candidate18_not_relabelled_or_counted_twice': True,
        'trajectory_Mirage': None, 'efficacy_established': False,
        'new_model_GUI_scorer_paid_calls': 0,
    })
    save(target / 'seal.json', {'review.json': sha(target / 'review.json')})
    pointer = {'review': str(target), 'review_sha256': sha(target / 'review.json'),
               'seal_sha256': sha(target / 'seal.json')}
    save(HERE / 'source-review-02-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    main()
