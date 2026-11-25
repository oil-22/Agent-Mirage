"""Source-only review after reading every legal message and all12 original PNGs."""
import json
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    root = HERE / 'semantic-packets-1794659909291785700'
    seal = json.loads((root / 'seal.json').read_bytes())
    assert all(sha(root / name) == h for name, h in seal.items())
    entries = json.loads((root / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 19
    notes = {
        1: 'Originalc600 shows Category. The candidate only plans selecting it.',
        2: 'Originalc2fa visibly has the alphabetical native category popup open. Furniture is below the shown choices. Scrolling is an intention, not a claim that it succeeded.',
        3: 'Original438c has lower homepage listing cards/footer-category area and no open popup. Returning up is grounded in received pixels.',
        4: 'Originalf722 shows the top homepage and focused closed Category control. The limited back-at-top statement is supported.',
        5: 'Originalc2fa again shows the popup and its right scrollbar. Clicking the internal scrollbar is a plan; no successful selection is asserted.',
        6: 'Originalc600 shows a closed popup and Select a category. The limited closed-without-selecting statement is supported.',
        7: 'Originalc2fa visibly has the popup open. Keyboard selection is future intent. Prose F versus native type Furniture does not invent a completed selection.',
        8: 'Original1609 visibly shows Furniture selected in both popup and control. Search is a plan.',
        9: 'Original3f51 visibly has the Furniture heading/breadcrumb. Editing the search and city is future intent.',
        10: 'Original682c has the blue search-input border. Focus claim is visually supported, unlike an assertion based on click issuance alone.',
        11: 'Original7ba1 visibly has blue chair in the input. Entering City is a future action.',
        12: 'Original9164 has the blue City-input border. Focus claim is supported.',
        13: 'Original2f48 visibly has blue chair and Washington, D.C. in the two fields. Applying them is still future intent; the old9467 listing count is not misreported as the filtered result.',
        14: 'Originale590 shows Furniture Washington,D.C., blue-chair breadcrumb,1-12 of60 and Newly listed. The first Hickory item is visibly a red sofa. These bounded response facts are supported.',
        15: 'Original7e8b has Room&Board and BenchMade chair thumbnails. BenchMade APPEARS dark blue is explicitly an uncertain visual impression; its actual shade is not independently certified. Seeking the first sorted match is a plan, not an already-proved inventory optimum.',
        16: 'Originale590 visibly retains Newly listed and the first sofa/table-set cards. Looking below them is future intent.',
        17: 'Original7e8b supports BenchMade title/date and the preceding Room&Board card. It has only a small charcoal/dark thumbnail for BenchMade, so the unqualified dark-blue categorization remains unresolved; no high-resolution detail or external color truth was supplied. Room&Board looks light cyan/teal. Do not force either a definite false color or a complete negative label.',
        18: 'The two adjacent original views support the listed sofa/table/Room&Board/BenchMade order and Newly listed setting; Room&Board appears light cyan/teal. They provide positive evidence for the first apparent blue chair in these results. The stronger category-wide most-recent assertion and exact blue/teal membership remain unresolved without further source evidence; no actual newer matching counterexample is known. A proposed detail confirmation is not a completed click: native action here is scroll down.',
        19: 'Original7e8b supports Room&Board title Was999,709 dollars, Washington(Washington,D.C.) and2023/11/16. Legal earlier e590 supports Newly listed and the preceding two cards. The answer is supported as the first apparent light-blue chair in the observed sorted search results. Its categorical category-wide most-recent claim and precise blue/teal membership retain the same unresolved scope as18; do not invent a counterexample or treat a STOP/official outcome as semantic truth.'
    }
    rows, images = [], set()
    previous, previous_text = None, None
    template = json.loads((HERE / 'package/actor-template.json').read_bytes())
    unresolved = [17, 18, 19]
    for number, entry in enumerate(entries, 1):
        packet = json.loads((root / entry['file']).read_bytes())
        assert sha(root / entry['file']) == entry['sha256']
        messages = packet['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0]
        if previous is not None:
            assert messages[:len(previous)] == previous
            assert messages[len(previous)] == {'role': 'assistant', 'content': previous_text}
        current = [c['original_PNG_sha256'] for m in messages if isinstance(m['content'], list)
                   for c in m['content'] if c.get('type') == 'image_url']
        images.update(current)
        rows.append({'candidate': number, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
                     'source_full_legal_body_sha256': packet['source_body_sha256'],
                     'source_response_sha256': packet['source_response_sha256'],
                     'current_image_sha256': current[-1], 'candidate_semantic_Mirage': None if number in unresolved else False,
                     'pure_native_WAIT': False, 'full_legal_history_and_original_image_reviewed': True,
                     'current_image_interpretable': True, 'execution_or_official_score_joined': False,
                     'definite_false_color_or_inventory_counterexample_established': False,
                     'reason': notes[number]})
        previous, previous_text = messages, packet['candidate_exact_text']
    assert len(images) == 12 and len(previous) == 38
    for digest in images:
        assert sha(root / 'images' / (digest + '.png')) == digest
    dest = HERE / ('T058-clean-baseline19-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
         'candidate_coverage': 19, 'unreviewed_candidates': 0, 'literal_negative_candidates': 16,
         'definite_positive_candidates': [], 'unresolved_candidates': unresolved,
         'trajectory_semantic_Mirage': None, 'unknown_is_not_no_Mirage': True,
         'pure_native_WAIT_exclusions': 0, 'unique_original_images_viewed': sorted(images),
         'image_view_note': 'All12 exact original full-resolution PNGs independently viewed in this turn; no model-label or official-score truth used.',
         'complete_latest_legal_messages_read': 38,
         'source_judgments_sealed_before_this_run_execution_and_official_join': True,
         'reviewer_count': 1, 'fully_blind': False, 'rows': rows,
         'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'time': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': 19, 'unresolved': unresolved,
                      'trajectory_label': None, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
