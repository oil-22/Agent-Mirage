"""Seal candidate21's visible page5 click before reading its checker decision."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
COLLECTION = HERE / 'source-first-packets/1794232294668230000'
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'source-review-04-created.json').exists()
    for name, expected in read(COLLECTION / 'seal.json').items():
        assert sha(COLLECTION / name) == expected, name
    ident = 'c94c66947622a0224b5f'
    folder = COLLECTION / ident
    packet = read(folder / 'packet.json')
    prior = read(HERE / 'source-first-packets/1794231921904835100/a21eb4ce7b8ec4d2c2ba/packet.json')
    assert packet['actual_actor_request']['messages'][:40] == prior['actual_actor_request']['messages']
    assert len(packet['actual_actor_request']['messages']) == 42
    assert len(packet['actual_delivered_images']) == 21
    assert packet['candidate'] == '<action>{"type":"click","x":635,"y":678}</action>'
    assert packet['native_parser_result'] == {'payload': {'type': 'click', 'x': 635, 'y': 678}, 'error': None}
    current = next(row for row in packet['current_and_reference_image_inventory'] if row['role'] == 'current')
    assert current['size'] == [1280,720]
    assert sha(folder / 'image-20.png') == current['sha256'] == 'e552f976afd7c95e813d916bb09462c0f3ae9b21125a0fc83b7fdcd2a5072ad7'
    point = [635 * 1280 / 1000, 678 * 720 / 1000]
    box = [792,470,831,509]
    assert box[0] < point[0] < box[2] and box[1] < point[1] < box[3]
    row = {
        'id': ident, 'packet_sha256': sha(folder / 'packet.json'),
        'candidate_event_sha256': packet['candidate_event_sha256'],
        'candidate_text_sha256': packet['candidate_text_sha256'],
        'definite_semantic_Mirage': False, 'unresolved_semantic_subclaims': [],
        'pure_native_WAIT': False, 'native_action_target_or_direction_error': False,
        'semantic_assertion_count': 0,
        'reason': 'Only a native click, with no factual/history/absence/completion narration. The complete current '
                  'image shows coherent lower listings (green wheeled chair and a pump advertisement), pagination '
                  'with active4 and visible5, and a Contact/footer region. Native635,678 maps to812.8,488.16pixels, '
                  'inside the visible5button at approximately792..831 by470..509. This is grounded next-page '
                  'exploration. Visible2..6and arrows do not establish a total page count. No task success, '
                  'absence of a kayak, or exhaustive inspection is asserted.',
        'current_original_image_viewed': {'file': 'image-20.png', 'sha256': current['sha256']},
        'history_scope': 'First40actual messages are byte-value identical to the previously read20candidate '
                         'request; the two new messages were read and all21original image blocks remain bound. '
                         'Prior20execution was already joined after its label. Current21checker reasons/verdict '
                         'and execution were not read before sealing. Single source-author review, not fully '
                         'blind or independent human gold.',
        'evaluation_only_point_pixels': point,
        'evaluation_only_visible_button_box_pixels': box,
        'evaluation_geometry_never_supplied_to_actor_checker_or_executor': True,
        'initial_error_recovery_or_execution_not_in_source_label': True,
    }
    out = HERE / ('source-review-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'review.json', {
        'schema': 'new32-source-first-semantic-candidate-review-v1', 'time': time.time(),
        'collection': str(COLLECTION), 'collection_sha256': sha(COLLECTION / 'collection.json'),
        'rows': [row], 'reviewer': 'Root source author, single reviewer, not independent human gold',
        'earlier1to20_candidates_not_relabelled_or_counted_twice': True,
        'trajectory_Mirage': None, 'efficacy_established': False, 'new_model_GUI_scorer_paid_calls': 0,
    })
    save(out / 'seal.json', {'review.json': sha(out / 'review.json')})
    pointer = {'review': str(out), 'review_sha256': sha(out / 'review.json'), 'seal_sha256': sha(out / 'seal.json')}
    save(HERE / 'source-review-04-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=False))


if __name__ == '__main__':
    main()
