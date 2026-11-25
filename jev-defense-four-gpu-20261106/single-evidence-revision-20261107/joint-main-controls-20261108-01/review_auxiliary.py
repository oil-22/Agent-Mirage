"""Seal root's image/source review separately from mechanical contract validity."""
from pathlib import Path
import hashlib
import json
import time

HERE = Path(__file__).resolve().parent
COLLECTION = HERE / 'sealed-call-collection/1794141100709207600'
target = HERE / 'auxiliary-semantic-review-01'
target.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
findings = {
    'N13': {
        'raw_text_spans': 16, 'raw_elements': 11,
        'contract_valid': False, 'natural_EOS': True,
        'findings': [
            'Reply exceeds both six-text and six-element limits; preserve complete raw reply, do not truncate into a valid packet.',
            'Original empty Keyword field has a blue border. Reply describes the input but does not report that border cue. Missing bounded evidence is not evidence of absent border or focus.',
            'No OS-focus, successful-typing or task-completion conclusion was supplied. Remaining listed major labels, thumbnails and prices are broadly visible; exact box IoU was not measured.'
        ],
        'semantic_approval': None,
    },
    'N14': {
        'raw_text_spans': 6, 'raw_elements': 4,
        'contract_valid': True, 'natural_EOS': True,
        'findings': [
            'Quoted titles, dates and prices from the first two full rows are visible. Four full-row thumbnails are present.',
            'The visible Pitino title, 5.00 price and suited cover figure are not described beyond a generic book-cover thumbnail. Bounded omission is not a false absence statement, but cannot substantiate the target appearance or a minimum-price decision.',
            'Description blue pendant is more specific than confidently resolvable from the small jewelry collage; keep this object identity unresolved.',
            'No exhaustive inventory or semantic correctness is established by the valid packet.'
        ],
        'semantic_approval': None,
    },
    'N15': {
        'raw_text_spans': 6, 'raw_elements': 6,
        'contract_valid': True, 'natural_EOS': True,
        'findings': [
            'Six quoted title/price snippets are visible and attached to their approximate screen regions; no numeric counterexample found in those six snippets.',
            'Bottom Bucknell thumbnail is cropped by the actual frame edge, yet e5 is marked clear rather than partial and no local limitation is recorded.',
            'Hoop and net describes part of the trash-can appearance but does not establish that the pictured item is an actual basketball hoop; retain that object identity qualification.',
            'Sports-card, globe and binder appearances do not justify a global no-person or no-suit conclusion; the model did not explicitly make that absence claim.'
        ],
        'semantic_approval': None,
    },
    'N16': {
        'raw_text_spans': 6, 'raw_elements': 6,
        'contract_valid': True, 'natural_EOS': True,
        'findings': [
            'Six quoted strings are visible, including 49 - 50 of 50 listings. Active page5 is visible in the original frame; no global history coverage follows.',
            'All six elements cite text_refs t1, whose literal content is OsClass. These links do not supply Apply, Publish Ad, basketball, pagination, Subscribe or the book title; six definite wrong text-to-element associations.',
            'e2 describes Publish Ad as blue, while its visible button background is black: definite color error.',
            'The two visible prices and second title are omitted under the compact inventory. Omission is not absence and does not prove the current minimum.'
        ],
        'semantic_approval': False,
    },
}
for case, row in findings.items():
    d = COLLECTION / 'original/worker/auxiliary' / case
    row['original_image_sha256'] = sha(d / 'original.png')
    row['raw_reply_sha256'] = sha(d / 'raw-output.txt')
    row['original_result_sha256'] = sha(d / 'result.json')
    row['call_seal_sha256'] = sha(d / 'seal.json')
report = {
    'reviewer': 'root', 'reviewed_unix': time.time(),
    'source_expectations_sealed_before_new_predictions': True,
    'review_is_single_reviewer_nonblind': True,
    'not_a_second_independent_reviewer': True,
    'reviewed_all_four_original_images_and_complete_raw_replies': True,
    'raw_text_spans_reviewed': 34, 'raw_elements_reviewed': 27,
    'boxes_visually_checked_without_exact_IoU_measurement': True,
    'new_calls_for_review': 0,
    'cases': findings,
    'overall_semantic_accuracy_or_Mirage_rate': None,
    'actor_feedback_effect_tested': False,
    'formal_GUI_ready': False,
    'raw_tensor_bytes_remain_sealed_remote': True,
}
(target / 'review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
(target / 'seal.json').write_text(json.dumps({'review.json': sha(target / 'review.json')}, indent=2), encoding='utf8')
print(json.dumps({'review': str(target / 'review.json'), 'sha256': sha(target / 'review.json')}, ensure_ascii=False))
