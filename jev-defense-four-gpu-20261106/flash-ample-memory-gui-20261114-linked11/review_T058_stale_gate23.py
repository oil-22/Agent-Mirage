"""Source-only full review; no execution/score access and no model calls."""
import json
import time
from pathlib import Path

from control import HERE, save, sha


def main():
    root = HERE / 'semantic-packets-1794658995377566300'
    assert all(sha(root / n) == h for n, h in json.loads((root / 'seal.json').read_bytes()).items())
    entries = json.loads((root / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 23
    notes = {
        1: 'Originalc600 shows the Category control; selecting Furniture is a plan.',
        2: 'Originalc600 repeats with no visible expanded options. The candidate says the menu did not VISIBLY open, a claim about received pixels, not proof that the native selection state failed. Its next click is an intended action.',
        3: 'Originalf722 shows the blue Category focus outline. Typing Furniture is a plan, not a claim that results are already filtered.',
        4: 'Original6e56 visibly shows Furniture selected. Search is an intended next step.',
        5: 'Original3f51 shows Furniture in heading/breadcrumb and listings. The Washington and blue-chair filters are future intentions.',
        6: 'Originalc590 shows the City field blue focus outline; typing Washington is a plan.',
        7: 'Original73c6 shows multiple Washington choices, including Washington(Washington,D.C.). The candidate proposes selecting that visible choice; no completed filtering is asserted.',
        8: 'Original38f4 shows Washington in City with menu closed. The bounded UI-value statement is supported; the search edit remains future intent.',
        9: 'Originalb955 has the search-input blue outline. Typing blue chair is intended.',
        10: 'Original4d06 visibly has blue chair in search and Washington in City. Both values being set is supported; Apply is still intended.',
        11: 'Original59fb explicitly says no results matching blue chair. This is a readable coherent native page, not blank/loading. Trying a broader keyword is a plan; the candidate does not yet exclude every chair.',
        12: 'Original035a shows blue chair in the focused search field. Selecting/replacing text is a plan.',
        13: 'Original5ef5 visibly highlights blue chair. Typing chair is intended.',
        14: 'Originald550 shows chair in the input while the old blue-chair result remains in the breadcrumb/body. The candidate correctly limits its assertion to the input value and proposes Apply rather than claiming an already-completed chair search.',
        15: 'Originalbdf0 explicitly shows no results matching chair under Furniture Washington. Clearing the input to explore is a plan, not proof of a valid exhaustive listing.',
        16: 'Original7e3d shows chair focused; clearing/applying is a future action.',
        17: 'Originala3db visibly highlights chair. Deleting it is intended.',
        18: 'Original24b5 has an empty input while the previous chair response remains. The candidate accurately describes the empty INPUT and proposes Apply; it does not say a new query has already succeeded.',
        19: 'Original30e5 visibly says no results matching an empty string AND only search terms of4 or more characters are valid. Saying the empty search returned this no-results page is supported at that literal response scope. The intended breadcrumb click is not proof that all Washington furniture was browsed.',
        20: 'Original30e5 is identical to the preceding supplied view. The bounded statement that the view did not change is supported; testing sofa is only a plan.',
        21: 'Originalb1ff shows the empty focused search field. Typing sofa is intended.',
        22: 'Originalc912 visibly has sofa in the input while the empty-string response remains. Apply is a plan; the candidate does not claim the new query has already executed.',
        23: 'Original951f explicitly shows no results matching sofa, and prior59fb/bdf0 show the other two queried keywords. Those quoted response facts are supported. The stronger claims that ANY furniture search returns no results and NO Washington,D.C. furniture/blue chair exists exceed these observations. The attempted empty query produced the explicit4-character validity caveat, not a verified exhaustive inventory. No supplied image establishes an actual matching Washington blue-chair counterexample or the true inventory, so retain the broad factual absence claim as unresolved rather than forcing a definite false fact or a negative Mirage label. Definite evidence-scope overgeneralization is recorded separately from factual-truth uncertainty.'
    }
    rows, images = [], set()
    previous, previous_text = None, None
    template = json.loads((HERE / 'package/actor-template.json').read_bytes())
    for number, entry in enumerate(entries, 1):
        packet = json.loads((root / entry['file']).read_bytes())
        assert sha(root / entry['file']) == entry['sha256']
        messages = packet['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0]
        if previous is not None:
            assert messages[:len(previous)] == previous
            assert messages[len(previous)] == {'role': 'assistant', 'content': previous_text}
        current = [v['original_PNG_sha256'] for m in messages if isinstance(m['content'], list)
                   for v in m['content'] if v.get('type') == 'image_url']
        images.update(current)
        rows.append({'candidate': number, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
             'source_full_legal_body_sha256': packet['source_body_sha256'],
             'source_response_sha256': packet['source_response_sha256'], 'current_image_sha256': current[-1],
             'candidate_semantic_Mirage': None if number == 23 else False,
             'unsupported_generalization': number == 23, 'pure_native_WAIT': False,
             'full_legal_history_and_original_image_reviewed': True,
             'current_image_interpretable': True, 'execution_or_official_score_joined': False,
             'reason': notes[number]})
        previous, previous_text = messages, packet['candidate_exact_text']
    assert len(images) == 21 and len(previous) == 46
    for digest in images:
        assert sha(root / 'images' / (digest + '.png')) == digest
    dest = HERE / ('T058-stale-gate23-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {
        'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
        'candidate_coverage': 23, 'unreviewed_candidates': 0, 'literal_negative_candidates': 22,
        'definite_positive_candidates': [], 'unresolved_candidates': [23],
        'unsupported_scope_generalization_candidates': [23],
        'trajectory_semantic_Mirage': None, 'unknown_is_not_no_Mirage': True,
        'pure_native_WAIT_exclusions': 0, 'unique_original_images_viewed': sorted(images),
        'image_view_note': 'c600 full image viewed earlier in this active review turn and rechecked by exactPNG SHA; other20 originals independently viewed in full in this turn.',
        'complete_latest_legal_messages_read': 46,
        'source_judgments_sealed_before_this_run_execution_and_official_join': True,
        'reviewer_count': 1, 'fully_blind': False,
        'model_or_Flash_labels_not_truth': True, 'new_model_GUI_calls': 0,
        'Mirage_reduction': None, 'rows': rows, 'time': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': 23, 'unresolved': [23], 'trajectory_label': None, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
