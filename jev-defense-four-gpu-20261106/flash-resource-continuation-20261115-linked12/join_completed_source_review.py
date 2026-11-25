"""Bind an already complete source review to native and controller evidence.

This reads one completed trajectory. Labels are never inferred, changed, or
filled by execution/official results; it cannot invoke models or GUI actions.
"""
import argparse
import base64
import hashlib
import json
import time
from pathlib import Path
from control import HERE, R4090, remote, save, sha
from capture_live_evidence import COMMON
from controller_audit_reader import GUI_READER, check_controller, parse_original


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert root.resolve().is_relative_to(HERE.resolve())
    seal = load(root / 'seal.json')
    assert seal and all(sha(root / n) == h for n, h in seal.items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--Flash-CPU', dest='cpu', type=Path, required=True)
    parser.add_argument('--terminals', type=Path, required=True)
    args = parser.parse_args()
    reviewroot, native, cpu, terminals = (p.resolve() for p in
                                         (args.review, args.native, args.cpu, args.terminals))
    for root in (reviewroot, native, cpu):
        verify(root)
    assert terminals.is_relative_to(HERE.resolve())
    review = load(reviewroot / 'review.json')
    assert review['completed_trajectory_review'] is True and not review['partial_prefix_only']
    assert review['unreviewed_within_exported_prefix'] == 0
    packets = Path(review['source_packets'])
    verify(packets)
    assert sha(packets / 'seal.json') == review['source_packets_seal_sha256']
    entries = load(packets / 'review-index.json')['packets']
    mapping = load(packets / 'PRIVATE-source-index.json')
    run_ids = {v['run_id'] for v in mapping}
    assert len(run_ids) == 1
    run_id = run_ids.pop()
    terminal = next(v for v in load(terminals)['result']['terminals'] if v['run']['run_id'] == run_id)
    assert len(entries) == len(review['rows']) == review['candidate_coverage'] == terminal['actor_calls']
    assert [v['candidate'] for v in review['rows']] == list(range(1, len(entries) + 1))
    assert all(v['full_legal_history_and_original_image_reviewed'] for v in review['rows'])
    actual = load(native / '3090.json')
    mains = {v['request_id']: v for v in actual['sealed_main_requests']}
    flashes = {v['request_id']: v for v in actual['sealed_Flash_requests']}
    independent = {v['request_id']: v for v in load(cpu / 'cumulative-report.json')['result']['requests']}
    selected = {v['decision']: v for v in mains.values() if v['run_id'] == run_id}
    assert len(selected) == len(entries)

    dest = HERE / ('completed-source-native-join-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'pre-join-binding.json', {
        'time': time.time(), 'run_id': run_id, 'review': str(reviewroot),
        'review_sha256': sha(reviewroot / 'review.json'), 'review_seal_sha256': sha(reviewroot / 'seal.json'),
        'native_audit': str(native), 'native_audit_seal_sha256': sha(native / 'seal.json'),
        'Flash_CPU_audit': str(cpu), 'Flash_CPU_seal_sha256': sha(cpu / 'seal.json'),
        'terminal_audit': str(terminals), 'terminal_audit_sha256': sha(terminals),
        'source_labels_sealed_before_this_join': True, 'new_model_GUI_calls': 0})
    source = GUI_READER
    old = "for terminal_path in sorted((r/'batch/runs').glob('*/attempt-*/terminal.json')):"
    new = "for terminal_path in sorted((r/'batch/runs'/RUN_ID).glob('attempt-*/terminal.json')):"
    boundary = "assert len(controllers)==29 and {v['terminal']['run']['run_id']for v in controllers}=={v['run_id']for v in plan['queue']}"
    assert source.count(old) == source.count(boundary) == 1
    source = source.replace(old, new).replace(boundary,
        "assert len(controllers)==1 and controllers[0]['terminal']['run']['run_id']==RUN_ID")
    code = 'ROOT=' + repr(R4090) + '\nRUN_ID=' + repr(run_id) + '\n' + COMMON + source
    compile(code, '<single-completed-controller-reader>', 'exec')
    raw, operation = remote('4090', code, 'completed-source-review-controller-binding', timeout=55)
    collection = json.loads(raw)
    save(dest / 'GUI-collection.json', {'result': collection, 'operation': str(operation)})
    controller = check_controller(collection['controllers'][0], mains, flashes, terminal, parse_original())

    def restore(value):
        if isinstance(value, list):
            return [restore(v) for v in value]
        if isinstance(value, dict):
            if value.get('type') == 'image_url':
                data = (packets / value['image_url']['url']).read_bytes()
                assert hashlib.sha256(data).hexdigest() == value['original_PNG_sha256']
                return {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(data).decode()}}
            return {k: restore(v) for k, v in value.items()}
        return value

    joined = []
    for number, (entry, label, bound) in enumerate(zip(entries, review['rows'], controller['rows']), 1):
        packet = load(packets / entry['file'])
        row = selected[number]
        assert label['packet_sha256'] == entry['sha256'] == sha(packets / entry['file'])
        assert label['source_full_legal_body_sha256'] == packet['source_body_sha256']
        assert label['source_response_sha256'] == packet['source_response_sha256']
        assert row['wire_sha256'] == packet['source_wire_sha256']
        assert row['seal_sha256'] == packet['source_request_seal_sha256']
        assert row['native_text'] == packet['candidate_exact_text']
        assert bound['request_id'] == row['request_id'] and bound['decision'] == number
        restored = json.dumps(restore(packet['legal_full_input_review_projection']),
                              sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
        assert hashlib.sha256(restored).hexdigest() == row['body_sha256']
        assert bound['image_sha256'] == label['current_image_sha256'] == row['current_image_sha256']
        flash_id = bound['gate_request_id']
        if flash_id is not None:
            online, independent_flash = flashes[flash_id], independent[flash_id]
            assert online['seal_sha256'] == independent_flash['seal_sha256']
            assert online['decision'] == independent_flash['decision'] == 'YES'
            assert online['image_sha256'] == independent_flash['image_sha256'] == bound['image_sha256']
        joined.append({'source_label_unchanged': label, 'native_and_controller_binding': bound,
                       'independent_Flash_CPU_verified': flash_id is not None,
                       'actual_native_action_not_automatically_wrong_from_narrative_error': True})
    save(dest / 'review-joined.json', {
        'time': time.time(), 'run_id': run_id, 'source_review': str(reviewroot),
        'source_review_seal_sha256': sha(reviewroot / 'seal.json'),
        'native_audit': str(native), 'native_audit_seal_sha256': sha(native / 'seal.json'),
        'Flash_CPU_audit': str(cpu), 'Flash_CPU_audit_seal_sha256': sha(cpu / 'seal.json'),
        'native_old_raw_checks_referenced_at_original_times': actual.get('cumulative_verification_is_linked_not_fresh_full_rehash', False),
        'fresh_full_postexit_rehash_still_required': True,
        'candidate_coverage': len(joined), 'definite_positive_candidates': review['definite_positive_candidates'],
        'unresolved_candidates': review['unresolved_candidates'],
        'trajectory_semantic_Mirage': review['trajectory_semantic_Mirage'],
        'labels_sealed_before_this_execution_join': True,
        'official_result_not_used_as_semantic_truth': True,
        'completed_controller_binding': controller, 'rows': joined,
        'reviewer_count': 1, 'fully_blind': False, 'effectiveness_proven': False,
        'Mirage_reduction': None, 'goal': 'active', 'new_model_GUI_calls': 0})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'join': str(dest), 'run_id': run_id, 'candidate_coverage': len(joined),
                      'trajectory_semantic_Mirage': review['trajectory_semantic_Mirage'],
                      'effectiveness_proven': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
