"""Seal explicit source judgments for a fresh prefix; never infer a label."""
import argparse
import json
import time
from pathlib import Path
from control import HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--annotations', type=Path, required=True)
    args = parser.parse_args()
    annotations = args.annotations.resolve()
    assert annotations.is_relative_to(HERE.resolve())
    supplied = load(annotations)
    packets = Path(supplied['source_packets']).resolve()
    assert packets.parent == HERE
    assert all(sha(packets / n) == h for n, h in load(packets / 'seal.json').items())
    entries = load(packets / 'review-index.json')['packets']
    supplied_rows = supplied['rows']
    assert entries and [v['candidate'] for v in supplied_rows] == list(range(1, len(entries) + 1))
    assert supplied['full_system_all_legal_messages_and_candidates_read'] is True
    assert supplied['full_original_PNGs_viewed_at_original_resolution'] is True
    assert supplied['PRIVATE_execution_index_used_for_labeling'] is False
    template = load(HERE / 'package/actor-template.json')
    rows, images = [], set()
    last_messages, last_text = None, None
    for number, (entry, row) in enumerate(zip(entries, supplied_rows), 1):
        assert sha(packets / entry['file']) == entry['sha256']
        packet = load(packets / entry['file'])
        assert packet['natural_EOS']
        messages = packet['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0] and len(messages) == number * 2
        if last_messages is not None:
            assert messages[:-2] == last_messages
            assert messages[-2] == {'role': 'assistant', 'content': last_text}
        for message in messages:
            if not isinstance(message['content'], list):
                continue
            for block in message['content']:
                if block.get('type') == 'image_url':
                    h = block['original_PNG_sha256']
                    assert sha(packets / block['image_url']['url']) == h
                    images.add(h)
        assert row['current_image_sha256'] == messages[-1]['content'][-1]['original_PNG_sha256']
        assert row['full_legal_history_and_original_image_reviewed'] is True and row['reason']
        assert row['candidate_semantic_Mirage'] is None or type(row['candidate_semantic_Mirage']) is bool
        assert type(row['pure_native_WAIT']) is bool
        rows.append({**row, 'packet_sha256': entry['sha256'],
            'source_full_legal_body_sha256': packet['source_body_sha256'],
            'source_response_sha256': packet['source_response_sha256'],
            'execution_or_official_score_joined': False})
        last_messages, last_text = messages, packet['candidate_exact_text']
    assert images == set(supplied['original_image_sha256s_independently_viewed'])
    completed = supplied['completed_trajectory_review']
    assert type(completed) is bool
    positive = [v['candidate'] for v in rows if v['candidate_semantic_Mirage'] is True and not v['pure_native_WAIT']]
    unresolved = [v['candidate'] for v in rows if v['candidate_semantic_Mirage'] is None and not v['pure_native_WAIT']]
    negatives = [v['candidate'] for v in rows if v['candidate_semantic_Mirage'] is False and not v['pure_native_WAIT']]
    name = supplied['output_name']
    assert name and '/' not in name and '\\' not in name
    dest = HERE / (name + '-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'human-annotations.json').write_bytes(annotations.read_bytes())
    save(dest / 'review.json', {'time': time.time(), 'source_packets': str(packets),
        'source_packets_seal_sha256': sha(packets / 'seal.json'), 'candidate_coverage': len(rows),
        'unreviewed_within_exported_prefix': 0, 'completed_trajectory_review': completed,
        'partial_prefix_only': not completed, 'whole_final_trajectory_not_fully_reviewed': not completed,
        'definite_positive_candidates': positive, 'unresolved_candidates': unresolved,
        'literal_negative_candidates': len(negatives), 'pure_native_WAIT_exclusions': sum(v['pure_native_WAIT'] for v in rows),
        'trajectory_semantic_Mirage': True if positive else None if unresolved or not completed else False,
        'true_first_trigger_established': False, 'unique_original_images_viewed': sorted(images),
        'full_original_PNGs_independently_viewed_at_original_resolution': True,
        'all_full_legal_messages_candidates_and_exact_prefixes_read': True,
        'legal_user_plus_candidate_messages_reviewed': len(rows) * 2,
        'reviewer_count': 1, 'fully_blind': False, 'new_independent_reviewer_count': 0,
        'source_disclosures': supplied.get('source_disclosures', {}),
        'PRIVATE_execution_index_used_for_labeling': False,
        'source_judgments_sealed_before_detailed_controller_native_join': True,
        'same_existing_source_review_reused': False, 'unknown_not_converted_to_no_Mirage': True,
        'rows': rows, 'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'goal': 'active'})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': len(rows), 'positives': positive,
        'unresolved': unresolved, 'completed_trajectory_review': completed, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
