"""Mechanical candidate extraction provenance, not a semantic truth detector."""
from __future__ import annotations
import copy
import hashlib

EXACT_CLAIM_INSTRUCTIONS = '''
Candidate extraction provenance (additional development contract): each claims[].text must be one nonempty exact, contiguous quote copied from the ACTUAL candidate, preserving its negation, uncertainty and scope. Use several entries if needed; do not concatenate disjoint fragments or insert paraphrased premises. A quote can be part of the prose or native action JSON answer. Do not write synthetic JSON fields or an assertion the candidate did not make. claims:[] remains valid when no concrete assertion is present; do not invent claims to fill it. Exact quotation is not evidence that the statement is true and does not permit relabeling a factual assertion as intent. Original evidence and action checks remain mandatory.
'''


def check_claim_origins(verdict: dict, candidate: str) -> dict:
    if not isinstance(candidate, str):
        raise TypeError('Only an actual string actor candidate can be quote-bound')
    if not isinstance(verdict, dict) or not isinstance(verdict.get('claims'), list):
        raise TypeError('Call the unchanged native verdict validator first')
    rows, errors = [], []
    for index, claim in enumerate(verdict['claims']):
        text = claim.get('text') if isinstance(claim, dict) else None
        if not isinstance(text, str) or not text:
            errors.append({'claim_index': index, 'reason': 'missing_exact_candidate_quote'})
            continue
        starts, offset = [], 0
        while True:
            found = candidate.find(text, offset)
            if found < 0:
                break
            starts.append(found); offset = found + 1
        if not starts:
            errors.append({'claim_index': index, 'claim_id': claim.get('id'),
                           'reason': 'claim_text_not_an_exact_candidate_span'})
            continue
        rows.append({'claim_index': index, 'claim_id': claim.get('id'),
            'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'candidate_spans': [[start, start + len(text)] for start in starts],
            'span_unit': 'Python Unicode code points in the unchanged candidate',
            'unique_occurrence': len(starts) == 1})
    return {'policy': 'exact-candidate-claim-origin-v1-development',
        'source_candidate_sha256': hashlib.sha256(candidate.encode('utf-8')).hexdigest(),
        'reject': bool(errors), 'errors': errors, 'bindings': rows,
        'verdict_modified': False, 'original_verdict': copy.deepcopy(verdict),
        'semantic_truth_or_claim_completeness_established': False,
        'duplicate_occurrences_are_listed_not_arbitrarily_resolved': True}
