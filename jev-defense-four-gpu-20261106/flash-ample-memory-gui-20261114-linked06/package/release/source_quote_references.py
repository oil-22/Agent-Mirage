"""Proposed ASCII wire references to exact, immutable candidate source units.

This module does not extract facts, supply answers, choose a semantic status,
validate visual truth, recommend an action or enlarge any model/GUI budget.
"""
import copy
import hashlib
import json

from source_quote_options import quote_options


POLICY = 'STAGED-exact-candidate-quote-reference-wire-v1'


class QuoteReferenceError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def source_index(candidate):
    table = quote_options(candidate)
    rows = [dict(quote_id='q' + str(index).zfill(4), **row)
            for index, row in enumerate(table['options'])]
    assert rows and len({row['quote_id'] for row in rows}) == len(rows)
    return dict(policy=POLICY, source_candidate_utf8_sha256=table['source_candidate_utf8_sha256'],
        source_options_policy=table['policy'], rows=rows,
        semantic_truth_or_extraction_completeness_established=False,
        automatic_allow_or_block=False)


def bind_reference_schema(schema, candidate):
    """Change one wire field only; keep all semantic/action/source enums intact."""
    result = copy.deepcopy(schema)
    claim = result['properties']['claims']['items']
    properties = claim['properties']
    assert properties['text'] == dict(type='string', maxLength=max(1, len(candidate)))
    assert 'quote_id' not in properties and claim['required'].count('text') == 1
    options = [row['quote_id'] for row in source_index(candidate)['rows']]
    claim['properties'] = {('quote_id' if key == 'text' else key):
        (dict(type='string', enum=options) if key == 'text' else value)
        for key, value in properties.items()}
    claim['required'] = [('quote_id' if key == 'text' else key) for key in claim['required']]
    return result


def resolve_references(verdict, candidate):
    """Decode a lossless source representation BEFORE the unchanged validator.

    Raw model output is retained separately and never edited. Resolved claim
    text is fetched by an exact source ID; there is no fallback, repair,
    paraphrase, whitespace/Unicode normalization or semantic label change.
    """
    if not isinstance(verdict, dict) or not isinstance(verdict.get('claims'), list):
        raise QuoteReferenceError('Quote-reference wire verdict requires claims[]')
    index = source_index(candidate)
    by_id = {row['quote_id']: row for row in index['rows']}
    resolved = copy.deepcopy(verdict)
    bindings = []
    for position, claim in enumerate(verdict['claims']):
        if not isinstance(claim, dict) or 'text' in claim or 'quote_id' not in claim:
            raise QuoteReferenceError('Each wire claim requires quote_id instead of free text')
        ident = claim['quote_id']
        if not isinstance(ident, str) or ident not in by_id:
            raise QuoteReferenceError('Unknown exact candidate quote reference')
        row = by_id[ident]
        assert digest(row['text'].encode('utf8')) == row['text_utf8_sha256']
        decoded = resolved['claims'][position]
        del decoded['quote_id']
        decoded['text'] = row['text']
        assert {k: v for k, v in decoded.items() if k != 'text'} == {
            k: v for k, v in claim.items() if k != 'quote_id'}
        bindings.append(dict(claim_index=position, claim_id=claim.get('id'), quote_id=ident,
            text_utf8_sha256=row['text_utf8_sha256'], exact_source_occurrences=copy.deepcopy(row['sources'])))
    report = dict(policy=POLICY, wire_verdict_sha256=digest(canonical(verdict)),
        resolved_verdict_sha256=digest(canonical(resolved)),
        source_candidate_utf8_sha256=index['source_candidate_utf8_sha256'],
        complete_source_index_sha256=digest(canonical(index)), bindings=bindings,
        raw_model_verdict_preserved=True, statuses_reasons_evidence_dependencies_and_action_unchanged=True,
        original_native_schema_and_provenance_validator_still_required=True,
        semantic_truth_or_extraction_completeness_established=False,
        automatic_allow_or_block=False, staged_only=True)
    return resolved, report


def extraction_boundary(units):
    candidate = ''.join(row['exact_text'] for row in units['source_units'])
    assert digest(candidate.encode('utf8')) == units['candidate_utf8_sha256']
    index = source_index(candidate)
    return '''
STAGED SOURCE REPRESENTATION FOR VERIFY OUTPUT ONLY. The original semantic and
evidence rules above remain mandatory. In the JSON wire schema, claims[].quote_id
REPLACES claims[].text. Select one exact quote_id from the source table below;
do not output a text field. The Controller reads that ID's complete original
text without editing it, then runs the original claim/source/evidence checks.
Use separate claim entries for different source units. Preserve every actual
assertion's negation, qualifications and scope when assessing it; do not omit
facts or relabel them as plans to pass. A source unit may contain several clauses
and may still be false, unclear or irrelevant. The table also includes plans and
literal native JSON, with no factual labels. claims:[] remains valid for a pure
plan, never as a way to conceal real assertions. Check both prose and native STOP
answer, and all action prerequisites, as before. These source IDs supply no GUI
fact, status, evidence citation, answer, correction or action approval.
EXACT_QUOTE_SOURCE_DATA:
''' + json.dumps([dict(quote_id=row['quote_id'], text=row['text']) for row in index['rows']],
                 ensure_ascii=False, separators=(',', ':'))
