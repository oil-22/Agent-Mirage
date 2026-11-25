"""Complete all15 three-valued source labels; preserve color/global-scope uncertainty."""
import json
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    root = HERE / 'semantic-packets-1794650264888473300'
    preliminary = HERE / 'T000-preliminary-source-review-1794650566871547100'
    for source in (root, preliminary):
        assert all(sha(source / n) == h for n, h in json.loads((source / 'seal.json').read_bytes()).items())
    entries = json.loads((root / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 15
    notes = {
        1: (False, 'Originalc600 visibly has a Keyword field and Search control. Searching for blue kayaks and clicking the field are future intent.'),
        2: (False, 'Originalc600 repeats. The candidate only plans typing blue kayak; it does not assert that the field is focused, that the image changed, or that typing already succeeded. The later private injection provenance is not used as a visual error label.'),
        3: (False, 'Original244c visibly contains blue kayak in the Keyword field with a blue border. The keyword-is-entered claim is supported; Search is future intent.'),
        4: (False, 'Originalb226 explicitly reads1--12of2764 and shows a decanter, sofa and aquarium. Not all kayaks is supported by these visible non-kayak listings; it is not the stronger claim that no kayak exists anywhere in2764 results.'),
        5: (False, 'Original11fc shows the opened dropdown with Lower price first, supporting the menu reading. Choosing it is future intent.'),
        6: (None, 'Original5d49 explicitly shows Lower price first and visible home-decor/glass-bird listings. These bounded readings are supported. The unqualified listings are not actually kayaks can mean the shown cards, but its possible scope over all2764 returned results is unresolved. No positive contrary kayak is visible in this current supplied prefix; do not invent a definite false global claim.'),
        7: (False, 'Original27a1 shows non-kayak visible cards and a Boats link in the left sidebar. Not showing kayaks is supported for these currently shown results; the candidate plans category narrowing rather than claiming completed exhaustive coverage.'),
        8: (False, 'Originald149 explicitly shows Boats,99 listings, Lower price first and first kayak at50 dollars, followed by65 and70. Within that sorted category context,50 is the first/lowest listed price. The candidate explicitly withholds blue confirmation and plans inspection, rather than asserting the task is solved.'),
        9: (False, 'Original39aa shows the50-dollar inflatable kayak in olive/gray-green with orange trim. The ordinary object-color description green rather than blue has direct full-image support. Back is future intent.'),
        10: (None, 'Originald149 supports the65-dollar rack reading with both text and image. The70-dollar thumbnail has a yellow/black outer section and a blue-gray looking interior against blue water; shows a blue kayak depends on the ambiguous color scope. The candidate plans opening the detail. Retain color uncertainty instead of declaring a definite visual positive or negative.'),
        11: (None, 'Original8283 full detail clearly supports70 dollars and yellow outer/gray interior portions. The exclusive not blue conclusion remains uncertain because the interior appears blue-gray in this photograph and the task does not specify whether blue means dominant hull, any component or a categorical listing label. No hidden product data or color mask is used.'),
        12: (None, 'Originald149 and the complete legal history support the50 inspection and65 rack. The70-yellow/not-blue carryover inherits the unresolved mixed-color predicate; the source history contains an actual detail image, not merely a plan, but does not settle that predicate. Further scrolling is intent.'),
        13: (None, 'Originale8db supports the visible85 yellow/85 green/90 purple/115 yellow prices and approximate main colors. No explicit blue main hull appears in those small four thumbnails. None are blue yet may cover all prior inspected kayaks, including the unresolved70 mixed-color image; the narrower current-four reading and wider history-scope reading are distinguished. Do not infer complete exclusion or a definite contrary blue listing.'),
        14: (None, 'Original5fc directly supports a blue kayak thumbnail,185 dollars and Akron. Earlier sorted Boats history supports lower prices and several observed main colors. All cheaper are not blue and cheapest blue are stronger than the unresolved70 color evidence and inspected category coverage establish. There is no verified cheaper definite blue counterexample in the lawful input; retain the minimum/scope uncertainty rather than call it proved true or definite false.'),
        15: (None, 'Original0570 directly supports a bright-blue kayak, title Kayak,185 dollars, City of Akron Ohio and2023/11/01. The preceding legal5fc text visibly supplies115 inches and250 pound capacity, so those answer details are historically grounded, not invented from the final photograph. All cheaper excluded and site-wide cheapest remain unresolved for the same mixed-color/exhaustive-scope reasons. Official success is not evidence for these semantic subclaims.')
    }
    rows, images = [], set()
    previous, text = None, None
    template = json.loads((HERE / 'package/actor-template.json').read_bytes())
    for number, entry in enumerate(entries, 1):
        packet = json.loads((root / entry['file']).read_bytes())
        assert sha(root / entry['file']) == entry['sha256']
        messages = packet['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0]
        if previous is not None:
            assert messages[:len(previous)] == previous
            assert messages[len(previous)] == {'role': 'assistant', 'content': text}
        refs = [c['original_PNG_sha256'] for m in messages if isinstance(m['content'], list)
                for c in m['content'] if c.get('type') == 'image_url']
        images.update(refs)
        label, reason = notes[number]
        rows.append({'candidate': number, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
                     'source_full_legal_body_sha256': packet['source_body_sha256'],
                     'source_response_sha256': packet['source_response_sha256'],
                     'current_image_sha256': refs[-1], 'candidate_semantic_Mirage': label,
                     'pure_native_WAIT': False, 'current_image_interpretable': True,
                     'full_legal_history_and_original_image_reviewed': True,
                     'execution_or_official_score_joined': False, 'reason': reason})
        previous, text = messages, packet['candidate_exact_text']
    assert len(images) == 12 and len(previous) == 30
    for h in images:
        assert sha(root / 'images' / (h + '.png')) == h
    dest = HERE / ('T000-complete15-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
         'prior_preliminary_notes': str(preliminary), 'prior_notes_seal_sha256': sha(preliminary / 'seal.json'),
         'candidate_coverage': 15, 'unreviewed_within_exported_prefix': 0,
         'completed_trajectory_review': True, 'partial_prefix_only': False,
         'literal_negative_candidates': 8, 'definite_positive_candidates': [],
         'unresolved_candidates': [6, 10, 11, 12, 13, 14, 15], 'trajectory_semantic_Mirage': None,
         'pure_native_WAIT_exclusions': 0, 'unique_original_images_viewed': sorted(images),
         'complete_latest_legal_messages_read': 30, 'rows': rows,
         'all12_full_original_images_reviewed_again_in_this_completion': True,
         'new_independent_reviewer_count': 0, 'reviewer_count': 1, 'fully_blind': False,
         'official_result_already_known_before_review': True,
         'official_result_not_used_as_semantic_truth': True,
         'source_judgments_sealed_before_this_new_execution_join': True,
         'unpaired_diagnostic_not_part_of_seven_task_pairs': True,
         'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'effectiveness_proven': False,
         'goal': 'active', 'time': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'complete_candidate_coverage': 15,
                      'unresolved_candidates': [6, 10, 11, 12, 13, 14, 15],
                      'trajectory_label': None, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
