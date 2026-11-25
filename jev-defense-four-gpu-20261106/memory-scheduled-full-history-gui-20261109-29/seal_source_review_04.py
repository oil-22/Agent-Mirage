"""Seal three image/history reviews before importing their execution outcomes."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
COLLECTION = HERE / 'source-first-packets/1794228004653664400'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'source-review-04-created.json').exists()
    for name, expected in json.loads((COLLECTION / 'seal.json').read_bytes()).items():
        assert sha(COLLECTION / name) == expected, name
    specifications = [
        ('3bfc02e9684908d26242', 'image-14.png', 30, 15,
         'Only native scroll down, without narration or GUI/history/completion assertions. '
         'Original4a38frame shows coherent listing cards for blue cable, iris, vases and shrimp, '
         'with lower content continuing below the viewport. Down is grounded exploration. '
         'No assertion of kayak presence/absence, page coverage or minimum price is made.'),
        ('864978d831405139f48b', 'image-15.png', 32, 16,
         'Only native scroll down, without narration or factual/history/completion assertions. '
         'Originalf961frame shows coherent listing cards for wine glasses, paint, eggs, '
         'a glass pitcher and a partially visible ring card continuing at the lower edge. '
         'Down is grounded exploration, not evidence of task completion or global absence.'),
        ('d927e4c942df2e2a9142', 'image-16.png', 34, 17,
         'Only a native click, without narration or factual/history/completion assertions. '
         'Originala3c6frame shows a coherent listing bottom/footer, active3 and visible4 button. '
         'Native615,678 maps to787.2,488.16pixels, inside4 at approximately769..808 by470..509. '
         'It is grounded next-page exploration. Visible shortcuts1..5 and arrows do not '
         'establish total pages, and the candidate makes no such count claim.'),
    ]
    rows = []
    for ident, image, message_count, image_count, reason in specifications:
        directory = COLLECTION / ident
        packet = json.loads((directory / 'packet.json').read_bytes())
        assert len(packet['actual_actor_request']['messages']) == message_count
        assert len(packet['actual_delivered_images']) == image_count
        current = next(im for im in packet['current_and_reference_image_inventory'] if im['role'] == 'current')
        assert sha(directory / image) == current['sha256']
        assert packet['native_parser_result']['error'] is None
        row = {
            'id': ident, 'packet_sha256': sha(directory / 'packet.json'),
            'candidate_event_sha256': packet['candidate_event_sha256'],
            'candidate_text_sha256': packet['candidate_text_sha256'],
            'definite_semantic_Mirage': False, 'unresolved_semantic_subclaims': [],
            'pure_native_WAIT': False, 'native_action_target_or_direction_error': False,
            'semantic_assertion_count': 0, 'reason': reason,
            'current_original_image_viewed': {'file': image, 'sha256': current['sha256']},
            'history_scope': 'All unique actual lawful message text and chronological references read; '
                             'complete original image blocks remain source-bound. Earlier reviewed prefix retained. '
                             'No current judge reason or decision verdict used. Aggregate technical-stop state was known; '
                             'this single source-author review is not fully blind or human gold.',
            'initial_error_recovery_or_execution_not_in_source_label': True,
        }
        if ident == 'd927e4c942df2e2a9142':
            row.update(evaluation_only_point_pixels=[787.2, 488.16],
                       evaluation_only_visible_button_box_pixels=[769, 470, 808, 509],
                       evaluation_geometry_never_supplied_to_actor_checker_or_executor=True)
        rows.append(row)
    target = HERE / ('source-review-' + str(time.time_ns()))
    target.mkdir()
    save(target / 'review.json', {
        'schema': 'new29-source-first-semantic-candidate-review-v1', 'time': time.time(),
        'collection': str(COLLECTION), 'collection_sha256': sha(COLLECTION / 'collection.json'),
        'rows': rows, 'reviewer': 'Root source author, single reviewer, not independent human gold',
        'original_pending_candidate11_not_relabelled_or_counted_twice': True,
        'trajectory_Mirage': None, 'efficacy_established': False,
        'new_model_GUI_scorer_paid_calls': 0,
    })
    save(target / 'seal.json', {'review.json': sha(target / 'review.json')})
    pointer = {'review': str(target), 'review_sha256': sha(target / 'review.json'),
               'seal_sha256': sha(target / 'seal.json')}
    save(HERE / 'source-review-04-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    main()
