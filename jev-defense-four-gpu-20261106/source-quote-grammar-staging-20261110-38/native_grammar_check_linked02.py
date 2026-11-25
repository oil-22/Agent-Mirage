"""Native installed verifier-grammar/tokenizer CPU checks; no model loading."""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def main(package, original):
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    sys.path.insert(0, str(package / 'proposed-release'))
    from defense.schema import judge_schema
    from source_quote_options import quote_options
    reference = json.loads((package / 'primary-reference.json').read_bytes())
    proof_path = Path(reference['primary_dependency_receipt'])
    assert hashlib.sha256(proof_path.read_bytes()).hexdigest() == reference['primary_dependency_receipt_sha256']
    proof = json.loads(proof_path.read_bytes())
    assert proof['status'] == 'passed' and proof['canonical_class_identical'] and proof['all_dependency_bytes_stable']
    deps = Path(proof['dependency_root'])
    actual = {str(f.relative_to(deps)): hashlib.sha256(f.read_bytes()).hexdigest()
              for f in deps.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix != '.pyc'}
    assert actual == proof['dependency_files']
    sys.path.insert(0, str(deps))
    from lmformatenforcer import JsonSchemaParser
    from lmformatenforcer.integrations.transformers import (
        build_token_enforcer_tokenizer_data, build_transformers_prefix_allowed_tokens_fn)
    from transformers import AutoTokenizer
    import torch
    assert not torch.cuda.is_initialized()
    original_calls = []
    for ident in ['0074', '0075']:
        folder = original / 'worker/requests' / ident
        seal = json.loads((folder / 'seal.json').read_bytes())
        for name in ['payload.json', 'native-call.json', 'effective-generation.json']:
            assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == seal[name]
        original_calls.append((ident, json.loads((folder / 'payload.json').read_bytes()),
                               json.loads((folder / 'native-call.json').read_bytes())))
    payload = original_calls[0][1]
    candidate = payload['candidate']
    view_data = payload['view']
    view = SimpleNamespace(images=view_data['images'], messages=view_data['messages'],
                           observation_id=view_data['observation_id'])
    schema = judge_schema(view, candidate, phase='exact_source_quote')
    old_schema = original_calls[0][2]['verifier_grammar']['schema']
    # The source-domain restriction is the only change to the grammar.
    removed = copy.deepcopy(schema)
    quotes = removed['properties']['claims']['items']['properties']['text'].pop('enum')
    assert removed == old_schema
    reports = []

    def characters(text, spec):
        state = JsonSchemaParser(spec)
        for index, char in enumerate(text):
            if char not in state.get_allowed_characters():
                return dict(accepted=False, first_rejected_character=index, character=char)
            state = state.add_character(char)
        return dict(accepted=state.can_end(), characters=len(text))

    for ident, unchanged, raw in original_calls:
        assert unchanged['candidate'] == candidate and unchanged['view'] == view_data
        assert characters(raw['text'], old_schema)['accepted']
        result = characters(raw['text'], schema)
        assert not result['accepted']
        reports.append(dict(case='unchanged_failed_reply_' + ident,
            existing_reply_not_repaired_or_regenerated=True, old_grammar_accepts=True,
            exact_quote_grammar_rejects=True, result=result))
    quote = next(text for text in quotes if 'cheapest blue kayak' in text and not text.startswith('{'))
    valid = dict(claims=[dict(id='c1', kind='gui_fact', text=quote, status='uncertain',
        evidence=[], reason='Source quotation is not truth proof.', dependent_decisions=['completion'])],
        action=dict(status='insufficient', target_kind='not_applicable',
                    reason='No completion approval from this CPU check.', evidence=[]),
        acknowledges_visual_deficit=False, pure_wait=False)
    encoded = json.dumps(valid, ensure_ascii=False, separators=(',', ':'))
    assert characters(encoded, schema)['accepted']
    reports.append(dict(case='exact_original_source_with_uncertain_claim_and_insufficient_action',
                        native_character_grammar_accepts=True))
    invalid = copy.deepcopy(valid)
    invalid['claims'][0]['text'] = quote + ' invented extra premise'
    assert not characters(json.dumps(invalid, separators=(',', ':')), schema)['accepted']
    reports.append(dict(case='appended_unsourced_premise', native_character_grammar_rejects=True))
    wait = dict(claims=[], action=dict(status='supported', target_kind='not_applicable',
        reason='Pure native WAIT control.', evidence=[dict(source='candidate', span_id='full')]),
        acknowledges_visual_deficit=False, pure_wait=True)
    wait_schema = judge_schema(view, '<action>{"type":"wait"}</action>', phase='exact_source_quote')
    assert characters(json.dumps(wait, separators=(',', ':')), wait_schema)['accepted']
    reports.append(dict(case='native_WAIT_empty_claims', native_character_grammar_accepts=True,
                        synthetic_protocol_control_not_real_model_semantic_pass=True))

    reference = json.loads((package / 'primary-reference.json').read_bytes())
    tokenizer = AutoTokenizer.from_pretrained(reference['primary_model'], local_files_only=True,
                                              trust_remote_code=True)
    token_data = build_token_enforcer_tokenizer_data(tokenizer)

    def token_replay(text, selected_ids, prompt_ids):
        assert tokenizer.decode(selected_ids, skip_special_tokens=True).strip() == text.strip()
        constrain = build_transformers_prefix_allowed_tokens_fn(token_data, JsonSchemaParser(schema))
        prefix = list(prompt_ids)
        for index, token in enumerate(selected_ids):
            allowed = constrain(0, torch.tensor(prefix, dtype=torch.long))
            if token not in allowed:
                return dict(accepted=False, first_rejected_native_token=index,
                            token_id=token, accepted_prefix_tokens=index)
            prefix.append(token)
        return dict(accepted=True, tokens=len(selected_ids))

    original_prompt_ids = original_calls[0][2]['input_ids']
    ids = tokenizer.encode(encoded, add_special_tokens=False)
    assert token_replay(encoded, ids, original_prompt_ids)['accepted']
    reports.append(dict(case='exact_source_valid_JSON_native_token_replay',
        original_0074_full_prompt_IDs_sha256=hashlib.sha256(json.dumps(original_prompt_ids, separators=(',', ':')).encode()).hexdigest(),
        result=token_replay(encoded, ids, original_prompt_ids)))
    for ident, _, raw in original_calls:
        ids = raw['generated_ids']
        if ids and ids[-1] in [248044, 248046]:
            ids = ids[:-1]
        result = token_replay(raw['text'], ids, raw['input_ids'])
        assert not result['accepted']
        reports.append(dict(case='unchanged_' + ident + '_native_generated_IDs', result=result,
            excluded_by_new_source_domain_not_a_new_model_reply=True))
    assert not torch.cuda.is_initialized()
    try:
        library_version=importlib.metadata.version('lm-format-enforcer')
    except importlib.metadata.PackageNotFoundError:
        library_version=None
    return dict(time=time.time(), passed=True, library_version=library_version,
        actual_original_dependency_root=str(deps), dependency_files_SHA_bound=len(actual),
        dependency_identity_receipt_sha256=reference['primary_dependency_receipt_sha256'],
        tokenizer_class=type(tokenizer).__name__, tokenizer_model_path=reference['primary_model'],
        controls=reports, controls_count=len(reports), CPU_grammar_and_tokenizer_only=True,
        no_model_weights_loaded=True, no_CUDA_context_initialized=True,
        source_choice_counts=len(quotes), actual_original_candidate_characters=len(candidate),
        no_real_model_negative_WAIT_semantic_or_capacity_pass=True,
        new_model_GUI_capture_action_scorer_paid_calls=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(main(args.package.resolve(), args.original.resolve()), ensure_ascii=True))
