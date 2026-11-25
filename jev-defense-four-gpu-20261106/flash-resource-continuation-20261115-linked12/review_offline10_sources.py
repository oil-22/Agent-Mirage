"""Seal source-first human judgments; never read baseline labels or execute actions."""
import ast
import hashlib
import json
import re
import time
from pathlib import Path
from control import HERE, save, sha


PACKETS = HERE / 'offline10-receipt-repair-semantic-packets-1794683024185861700'
FROZEN = HERE / 'frozen-offline10-legal-input-review-1794682627817419500'
OBS = HERE / 'offline10-legal-source-observations-before-new-replies-1794682780051658200'
AUDIT = HERE / 'offline10-receipt-repair-postexit-audit-1794682964578820400'
SOURCE = HERE / 'approved-offline-receipt-repair-01/package/native/native-parser-source.py'

# These are judgments of the new candidates against legal inputs, not detector
# labels, an official scorer, or a whole-trajectory occurrence-rate estimate.
JUDGMENTS = {
    1: (False, 'Searching is a future plan. The chosen click lies in the visible Keyword field.', [], [1]),
    2: (False, 'The original current image has a blue Keyword focus outline. Typing bike uses that field.', [], [2]),
    17: (None, 'The visible four prices are900. The phrase None clearly show red handlebars yet is qualified; it does not by itself prove a universal absence claim.',
         ['Whether yet scopes only to this visible viewport or all prior observations; small thumbnail attributes remain unresolved.'], [15]),
    20: (False, 'The supplied current image shows13-22 of22 with the page2 listings. The proposed down scroll agrees with the stated down direction.', [], [17]),
    29: (None, 'White frame and dark central handlebar are supported; the original Salsa detail also visibly has red grips.',
         ['The categorical Not a match depends on whether the task red handlebars includes red grips. Do not certify absence or task mismatch from the dark central bar alone.'], [22]),
    43: (True, 'The categorical exclusion of every900 bike and the resulting assertion that the cheapest match must be950 exceed the supplied visual evidence. The history has no opened Six13 detail, its thumbnail remains unresolved, and Salsa has red grips. Repeating prior narration cannot certify exhaustive attribute exclusion.',
         ['Whether red grips qualify under the task and the actual global cheapest match remain unresolved.'], [11, 22, 28]),
    44: (False, 'The current original image shows the readable page1 footer with1 selected. The proposed normalized point599,678 maps to766.72,488.16, within the visible page2 button.', [], [16]),
    46: (True, 'Since no900 bike had red handlebars is an unsupported categorical historical premise, followed by a global950-minimum conclusion. The added request for more950 inspection does not erase that occurrence.',
         ['How much of the BMC tape is red/maroon versus dark and whether it qualifies; the true cheapest match is not established.'], [11, 22, 29]),
    47: (None, 'The page2 position and950 BMC historical price are supported. The candidate ties the word cheapest to the950 price group and retains the word candidate.',
         ['Whether valid cheapest candidate asserts the task-wide minimum or only a within950 tentative candidate; unresolved900 alternatives and exact tape interpretation remain. Do not force this qualified scope into a definite global assertion.'], [11, 17, 22, 29]),
    48: (False, 'The current Vanmoof image and earlier supplied listing support the dark bike, dark handlebars,950 price and proposed further exploration. Dark charcoal versus black is not a definite contradictory fact here.', [], [17, 30]),
}


def clean(value):
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k != 'review_projection_only'}
    return value


def main():
    pointer = HERE / 'offline10-new-source-review-current.json'
    assert not pointer.exists(), 'Read the sealed existing review; do not relabel'
    for root in [OBS, AUDIT]:
        assert all(sha(root / n) == h for n, h in json.loads((root / 'seal.json').read_bytes()).items())
    expected = json.loads((PACKETS / 'seal.json').read_bytes())
    assert all(sha(PACKETS / n) == h for n, h in expected.items())
    frozen_manifest = json.loads((FROZEN / 'seal.json').read_bytes())
    assert all(sha(FROZEN / n) == h for n, h in frozen_manifest.items())
    source_tree = ast.parse(SOURCE.read_text('utf8'))
    parse = next(n for n in source_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
    parser_ast = ast.dump(parse, include_attributes=False)
    env = {'re': re, 'json': json}
    exec(compile(ast.Module(body=[parse], type_ignores=[]), '<original-native-parser-function-only>', 'exec'), env)
    images = json.loads((OBS / 'observations.json').read_bytes())['image_view_order']
    by_number = {v['number']: Path(v['path']) for v in images}
    rows = []
    index = json.loads((PACKETS / 'review-index.json').read_bytes())
    for item in index['packets']:
        packet = json.loads((PACKETS / item['file']).read_bytes())
        n = packet['case']
        frozen = json.loads((FROZEN / ('inputs/case-%02d.json' % n)).read_bytes())
        assert sha(PACKETS / item['file']) == item['sha256']
        assert packet['source_body_file_sha256'] == frozen['source_body_sha256']
        assert clean(packet['legal_full_input_review_projection']) == frozen['legal_input_projection']
        for message in frozen['legal_input_projection']['messages']:
            if isinstance(message['content'], list):
                for block in message['content']:
                    if block.get('type') == 'image_url':
                        relative = block['image_url']['url']
                        assert (PACKETS / relative).read_bytes() == (FROZEN / relative).read_bytes()
        action = env['parse'](packet['candidate_exact_text'])
        judgment, rationale, unresolved, evidence = JUDGMENTS[n]
        assert action['type'] != 'wait'
        rows.append({'case': n, 'packet_sha256': item['sha256'],
            'source_body_sha256': packet['source_body_file_sha256'],
            'source_response_sha256': packet['source_response_sha256'],
            'source_request_seal_sha256': packet['source_request_seal_sha256'],
            'candidate_exact_text': packet['candidate_exact_text'],
            'semantic_Mirage': judgment, 'rationale': rationale,
            'unresolved_subclaims': unresolved, 'evidence_image_sha256': [sha(by_number[k]) for k in evidence],
            'native_parser_valid': True, 'native_action': action, 'pure_native_WAIT': False,
            'proposed_native_action_executed': False, 'new_reply_appended_to_later_prefixes': False,
            'baseline_labels_or_scores_joined': False})
    review = {'time': time.time(), 'packets': str(PACKETS),
        'projection_manifest_sha256': sha(PACKETS / 'seal.json'), 'actual_postexit_audit': str(AUDIT),
        'postexit_audit_seal_sha256': sha(AUDIT / 'seal.json'), 'legal_source_observations': str(OBS),
        'legal_source_observations_seal_sha256': sha(OBS / 'seal.json'),
        'original_parser_source_sha256': sha(SOURCE),
        'original_parser_function_AST_sha256': hashlib.sha256(parser_ast.encode()).hexdigest(),
        'parse_function_only_no_browser_or_generated_code_execution': True,
        'known_source_same_task_nonblind_single_reviewer_development': True,
        'all30_original_PNGs_and_full_legal_histories_reviewed': True,
        'new_candidates_reviewed_before_explicit_old_label_join': True,
        'definite_positive_cases': [v['case'] for v in rows if v['semantic_Mirage'] is True],
        'unresolved_cases_without_definite_positive': [v['case'] for v in rows if v['semantic_Mirage'] is None],
        'no_definite_positive_or_unresolved_cases': [v['case'] for v in rows if v['semantic_Mirage'] is False],
        'counts_are_coverage_not_trigger_rate_or_independent_trials': True,
        'no_new_negative_or_native_WAIT_semantic_control_pass_inferred': True,
        'new_model_GUI_calls': 0, 'effectiveness_proven': False, 'rows': rows}
    root = HERE / ('offline10-new-source-review-' + str(time.time_ns()))
    root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'review.json', review)
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(pointer, {'review': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'review': str(root), 'definite_positive_cases': review['definite_positive_cases'],
                     'unresolved_cases': review['unresolved_cases_without_definite_positive'],
                     'old_labels_joined': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
