"""Bind an immutable partial source review to already audited actual inputs/actions.

This reader cannot call a model, execute an action, or change a source label.
Completed trajectories use join_completed_source_review.py instead.
"""
import argparse
import base64
import hashlib
import json
import time
from pathlib import Path

from control import HERE, save, sha
from native_parser_reader import parse_original


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert root.resolve().parent == HERE
    seal = load(root / 'seal.json')
    assert seal and all(sha(root / name) == h for name, h in seal.items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--Flash-CPU', dest='cpu', type=Path)
    args = parser.parse_args()
    reviewroot, native = args.review.resolve(), args.native.resolve()
    for root in (reviewroot, native):
        verify(root)
    review = load(reviewroot / 'review.json')
    assert review['partial_prefix_only'] and not review['completed_trajectory_review']
    assert review['unreviewed_within_exported_prefix'] == 0
    source_occurrence = bool(review['definite_positive_candidates'])
    if 'at_least_one_boundary_occurrence_despite_unfinished_trajectory' in review:
        assert review['at_least_one_boundary_occurrence_despite_unfinished_trajectory'] is source_occurrence
    packets = Path(review['source_packets'])
    verify(packets)
    assert sha(packets / 'seal.json') == review['source_packets_seal_sha256']
    entries = load(packets / 'review-index.json')['packets']
    mapping = load(packets / 'PRIVATE-source-index.json')
    run_ids = {row['run_id'] for row in mapping}
    assert len(run_ids) == 1
    run = run_ids.pop()
    actual = load(native / '3090.json')
    mains = {row['decision']: row for row in actual['sealed_main_requests'] if row['run_id'] == run}
    flashes = {row['request_id']: row for row in actual['sealed_Flash_requests']}
    controller = next(row for row in load(native / '4090.json')['controllers'] if '/' + run + '/' in row['path'])
    assert len(controller['actor_requests']) == len(controller['forwarded_images'])
    requests = {req['request_id']: (req, frame) for req, frame in
                zip(controller['actor_requests'], controller['forwarded_images'])}
    replies = {row['request_id']: row for row in controller['actor_replies']}
    actions = {row['step']: row for row in controller['environment_actions']}
    independent = {}
    if args.cpu:
        verify(args.cpu.resolve())
        independent = {row['request_id']: row for row in load(args.cpu / 'cumulative-report.json')['result']['requests']}
    original_parser_file = HERE / 'package/native-parser-source.py'
    assert sha(original_parser_file) == load(HERE / 'package/manifest.json')['files']['native-parser-source.py']
    parse = parse_original()

    def restore(value):
        if isinstance(value, list):
            return [restore(v) for v in value]
        if isinstance(value, dict):
            if value.get('type') == 'image_url':
                data = (packets / value['image_url']['url']).read_bytes()
                assert hashlib.sha256(data).hexdigest() == value['original_PNG_sha256']
                return {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(data).decode()}}
            return {key: restore(v) for key, v in value.items()}
        return value

    count = review['candidate_coverage']
    assert count == len(entries) == len(review['rows'])
    rows = []
    for number, (entry, label) in enumerate(zip(entries, review['rows']), 1):
        packet = load(packets / entry['file'])
        a = mains[number]
        req, frame = requests[a['request_id']]
        reply = replies[a['request_id']]
        assert label['candidate'] == number
        assert label['packet_sha256'] == entry['sha256'] == sha(packets / entry['file'])
        assert label['source_full_legal_body_sha256'] == packet['source_body_sha256']
        assert label['source_response_sha256'] == packet['source_response_sha256']
        assert label['full_legal_history_and_original_image_reviewed']
        assert a['actual_tensor_files_verified'] and a['natural_EOS']
        assert a['wire_sha256'] == packet['source_wire_sha256'] and a['seal_sha256'] == packet['source_request_seal_sha256']
        assert a['native_text'] == packet['candidate_exact_text']
        assert a['current_image_sha256'] == label['current_image_sha256'] == frame['image_sha256']
        body = json.dumps(restore(packet['legal_full_input_review_projection']), sort_keys=True,
                          ensure_ascii=False, separators=(',', ':')).encode()
        assert hashlib.sha256(body).hexdigest() == a['body_sha256'] == req['body_sha256']
        assert reply['text_sha256'] == hashlib.sha256(a['native_text'].encode()).hexdigest()
        assert not frame['extra_auxiliary_text_in_main_prompt']
        gate = frame['gate_request_id']
        if gate is not None:
            online, cpu = flashes[gate], independent[gate]
            assert online['seal_sha256'] == cpu['seal_sha256']
            assert online['decision'] == cpu['decision'] == 'YES'
            assert online['image_sha256'] == cpu['image_sha256'] == a['current_image_sha256']
        payload = parse(a['native_text'])
        action = actions.get(number)
        if payload['type'] == 'stop':
            assert action is None
        else:
            assert action is not None and action['ok'] is True and action['payload'] == payload
        rows.append({'source_label_unchanged': label, 'request_id': a['request_id'],
                     'request_seal_sha256': a['seal_sha256'], 'body_canonical_sha256': a['body_sha256'],
                     'source_body_file_sha256': packet['source_body_sha256'],
                     'image_sha256': a['current_image_sha256'], 'gate_request_id': gate,
                     'original_parser_payload': payload, 'actual_environment_action': action,
                     'action_not_labeled_wrong_from_narrative_or_plan_error': True})
    dest = HERE / ('source-native-prefix-binding-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'binding.json', {'time': time.time(), 'run_id': run, 'source_review': str(reviewroot),
        'source_review_seal_sha256': sha(reviewroot / 'seal.json'), 'source_labels_sealed_before_this_join': True,
        'native_audit': str(native), 'native_audit_seal_sha256': sha(native / 'seal.json'),
        'old_native_raw_verification_times_retained': True, 'fresh_full_postexit_rehash_still_required': True,
        'original_parser_source_sha256': sha(original_parser_file),
        'controller_path': controller['path'], 'controller_verified_prefix_chain': controller['chain'],
        'partial_prefix_only': True, 'candidate_coverage': count, 'rows': rows,
        'whole_final_trajectory_review_not_complete': True, 'official_outcome_joined': False,
        'source_positive_boundary_occurrence': source_occurrence,
        'no_execution_or_score_used_to_replace_labels': True, 'new_model_GUI_calls': 0,
        'Mirage_reduction': None, 'goal': 'active'})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'binding': str(dest), 'prefix_native_input_parser_action_bindings': count,
                      'completed_trajectory': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
