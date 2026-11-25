"""Replay the frozen length filter on two actual replies; no model calls or edits."""
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

from orchestrate import HERE, PACKAGE, save, sha
from join_source_reviews import verify_seal


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    pointer = HERE / 'summary-boundary-diagnosis-created.json'
    assert not pointer.exists(), 'Completed actual-prefix diagnoses are immutable'
    manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
    filenames = ['unicode_length_guard.py', 'bounded_schema.py', 'bounded_auxiliary.py', 'native_format_bridge.py']
    for name in filenames:
        assert sha(PACKAGE / name) == manifest['files'][name]
    guard = load('frozen_summary_boundary_guard', PACKAGE / 'unicode_length_guard.py')
    schema = load('frozen_summary_boundary_schema', PACKAGE / 'bounded_schema.py')
    assert guard.field_limits(schema.SCHEMA)['summary'] == 180
    root = HERE / ('summary-boundary-diagnosis-' + str(time.time_ns()))
    root.mkdir()
    for name in filenames:
        (root / name).write_bytes((PACKAGE / name).read_bytes())
    reports, authorities = [], []
    sources = [
        ('0002', HERE / 'mixed-receipt-audit-1794252665988226300'),
        ('0008', HERE / 'mixed-receipt-audit-1794253325238705100'),
    ]
    for request, auditroot in sources:
        seal = verify_seal(auditroot)
        audit = json.loads((auditroot / 'receipt.json').read_bytes())
        assert audit['passed'] and audit['actual_enabled_mixed_branch_observed']
        data = json.loads((auditroot / '3090-native-bindings.json').read_bytes())
        report = next(row for row in data['reports'] if row['request'] == request)
        assert report['operation'] == 'evidence'
        proof = report['native_proof']
        assert proof['natural_EOS'] and proof['independent_native_tokenizer_decode_matches_original_raw_text']
        assert proof['independent_selected_native_ID_bytes_match_saved_token_bytes']
        response = data['bindings'][request]['response']['evidence_response']
        raw = response['raw_output']
        reading = json.loads(raw)
        summary = reading['frame']['summary']
        assert len(summary) == 180
        start = re.search(r'"summary"\s*:\s*', raw).end()
        decoded, consumed = json.JSONDecoder().raw_decode(raw[start:])
        assert decoded == summary
        closing_quote = start + consumed - 1
        assert raw[closing_quote] == '"'
        prefix = raw[:closing_quote].encode('utf8')
        state = guard.LengthState(guard.field_limits(schema.SCHEMA)).feed(prefix)
        assert state.in_string and not state.is_key and state.maximum == state.count == 180
        assert not state.pending_high and not state.escape and not state.utf8_remaining
        assert state.stack[-1]['key'] == 'summary'
        probes = []
        for extension in [b'a', b' ', b'.', b'\\n', b'\\u0041', '\u4e2d'.encode('utf8')]:
            rejected = False
            try:
                state.clone().feed(extension)
            except guard.InvalidLengthPrefix:
                rejected = True
            assert rejected
            probes.append(dict(extension_hex=extension.hex(), rejected=True))
        closed = state.clone().feed(b'"')
        assert not closed.in_string
        completed = state.clone().feed(raw[closing_quote:].encode('utf8'))
        assert completed.complete()
        rawname = request + '-actual-native-raw-output.txt'
        (root / rawname).write_bytes(raw.encode('utf8'))
        reports.append(dict(request=request, original_request_seal_sha256=report['request_seal_sha256'],
                            actual_image_sha256=response['image_sha256'],
                            raw_output_file=rawname, raw_output_sha256=sha(root / rawname),
                            summary=summary, decoded_character_length=len(summary), hard_character_cap=180,
                            complete_original_reply_natural_EOS=True, output_tokens=proof['output_tokens'],
                            actual_summary_prefix_byte_length=len(prefix), summary_prefix_at_original_length_cap=True,
                            original_length_filter_rejects_additional_scalar_character=True,
                            closing_quote_allowed_by_original_length_filter=True,
                            whole_original_JSON_length_replay_complete=True, extension_probes=probes,
                            full_actual_token_allowed_sets_independently_recomputed=False,
                            unmasked_model_preference_or_counterfactual_sentence_unknown=True,
                            screenshot_semantic_correctness_not_established=True))
        authorities.append(dict(audit=str(auditroot), audit_receipt_sha256=sha(auditroot / 'receipt.json'),
                                audit_seal_sha256=seal, native_report_file_sha256=sha(auditroot / '3090-native-bindings.json')))
    prompt = (PACKAGE / 'fixed-prompt.txt').read_text(encoding='utf8')
    needle = 'Use short values: summary <=180 characters,'
    assert prompt.count(needle) == 1
    draft = prompt.replace(needle,
        'Use short values: summary must be one complete literal sentence of <=100 characters; '
        'omit boilerplate and peripheral detail (the hard schema limit remains 180 characters).')
    (root / 'original-fixed-v6-prompt.txt').write_bytes(prompt.encode('utf8'))
    (root / 'UNSENT-short-sentence-prompt-proposal.txt').write_bytes(draft.encode('utf8'))
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    receipt = dict(time=time.time(), operation='actual-two-reply-length-boundary-diagnosis',
                   reports=reports, authorities=authorities,
                   original_fixed_prompt_sha256=sha(root / 'original-fixed-v6-prompt.txt'),
                   unsent_proposal_sha256=sha(root / 'UNSENT-short-sentence-prompt-proposal.txt'),
                   diagnosis='Both actual incomplete summary clauses end exactly at the frozen 180-codepoint cap. '
                             'At each actual prefix, the frozen length filter forbids another scalar character '
                             'but permits closing the string. This identifies a generation constraint contributing '
                             'to the incomplete field; it does not show what unmasked generation would have said '
                             'or repair unsupported footer/photo statements.',
                   proposed_condition='A future independently identified prompt would ask for one complete '
                                      'literal sentence within 100 characters while retaining the original strict '
                                      '180-character schema cap, full image, stateless input and all budgets.',
                   exact_tradeoff='Shorter summaries omit some visible detail; this does not make remaining '
                                  'facts true or guarantee complete sentences. Requires new source-bound controls '
                                  'and matched evaluation before use or benefit claims.',
                   proposal_unsent_and_not_deployed=True, current32_prompt_and_runtime_unchanged=True,
                   auxiliary_semantic_instability_repaired=False, main_validator_unchanged=True,
                   existing_replies_modified_or_reexecuted=False, new_model_GUI_scorer_paid_calls=0,
                   efficacy_established=False, goal='active')
    save(root / 'receipt.json', receipt)
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), receipt_sha256=sha(root / 'receipt.json'),
                  seal_sha256=sha(root / 'seal.json'), actual_replies_diagnosed=['0002', '0008'],
                  original_length_cap=180, new_model_GUI_scorer_calls=0, current_runtime_unchanged=True)
    save(pointer, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
