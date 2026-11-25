"""Exact canonical native grammar/tokenizer CPU check; never load model weights."""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(package, original):
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    sys.path.insert(0, str(package / 'proposed-release'))
    from defense.schema import judge_schema
    from source_quote_references import source_index, resolve_references, extraction_boundary
    from candidate_units import candidate_source_units
    reference = json.loads((package / 'primary-reference.json').read_bytes())
    proof_path = Path(reference['primary_dependency_receipt'])
    assert sha(proof_path) == reference['primary_dependency_receipt_sha256']
    proof = json.loads(proof_path.read_bytes())
    assert proof['status'] == 'passed' and proof['canonical_class_identical'] and proof['all_dependency_bytes_stable']
    deps = Path(proof['dependency_root'])
    actual = {str(f.relative_to(deps)): sha(f) for f in deps.rglob('*')
              if f.is_file() and '__pycache__' not in f.parts and f.suffix != '.pyc'}
    assert actual == proof['dependency_files']
    sys.path.insert(0, str(deps))
    from lmformatenforcer import JsonSchemaParser
    from lmformatenforcer.integrations.transformers import build_token_enforcer_tokenizer_data, build_transformers_prefix_allowed_tokens_fn
    from transformers import AutoTokenizer
    import torch
    assert not torch.cuda.is_initialized()
    originals = []
    for ident in ['0074', '0075']:
        folder = original / 'worker/requests' / ident
        seal = json.loads((folder / 'seal.json').read_bytes())
        for name in ['payload.json', 'native-call.json', 'effective-generation.json']:
            assert sha(folder / name) == seal[name]
        originals.append((ident, json.loads((folder / 'payload.json').read_bytes()),
                          json.loads((folder / 'native-call.json').read_bytes())))
    payload = originals[0][1]
    candidate, view_data = payload['candidate'], payload['view']
    view = SimpleNamespace(images=view_data['images'], messages=view_data['messages'], observation_id=view_data['observation_id'])
    schema = judge_schema(view, candidate, phase='exact_source_reference')
    old_schema = originals[0][2]['verifier_grammar']['schema']
    restored = copy.deepcopy(schema)
    claim = restored['properties']['claims']['items']
    source_ids = claim['properties'].pop('quote_id')['enum']
    claim['properties']['text'] = old_schema['properties']['claims']['items']['properties']['text']
    claim['required'] = ['text' if name == 'quote_id' else name for name in claim['required']]
    assert restored == old_schema
    rows = source_index(candidate)['rows']
    assert len(rows) == len(source_ids) and all(row['quote_id'] == ident for row, ident in zip(rows, source_ids))
    reports = []

    def characters(text, spec=schema):
        state = JsonSchemaParser(spec)
        for index, char in enumerate(text):
            if char not in state.get_allowed_characters():
                return dict(accepted=False, first_rejected_character=index, character=char)
            state = state.add_character(char)
        return dict(accepted=state.can_end(), characters=len(text))

    valid = dict(claims=[dict(id='c1', kind='gui_fact', quote_id=source_ids[0], status='uncertain',
        evidence=[], reason='Source ID is not truth proof.', dependent_decisions=['completion'])],
        action=dict(status='insufficient', target_kind='not_applicable', reason='No completion approval in this CPU control.', evidence=[]),
        acknowledges_visual_deficit=False, pure_wait=False)
    tokenizer = AutoTokenizer.from_pretrained(reference['primary_model'], local_files_only=True, trust_remote_code=True)
    token_data = build_token_enforcer_tokenizer_data(tokenizer)
    prompt_ids = originals[0][2]['input_ids']
    prompt_sha = hashlib.sha256(json.dumps(prompt_ids, separators=(',', ':')).encode()).hexdigest()

    def tokens(text, spec=schema):
        # A CPU representability witness, not the generated model path. The
        # preserved old and new schemas both reject some delimiter-spanning BPE
        # merges; use exact native character tokens without changing runtime.
        ids = [token for char in text for token in tokenizer.encode(char, add_special_tokens=False)]
        assert tokenizer.decode(ids, skip_special_tokens=True) == text
        constrain = build_transformers_prefix_allowed_tokens_fn(token_data, JsonSchemaParser(spec))
        prefix = list(prompt_ids)
        for index, ident in enumerate(ids):
            if ident not in constrain(0, torch.tensor(prefix, dtype=torch.long)):
                return dict(accepted=False, first_rejected_native_token=index, token_id=ident)
            prefix.append(ident)
        eos = tokenizer.eos_token_id
        assert isinstance(eos, int)
        terminal_allowed = constrain(0, torch.tensor(prefix, dtype=torch.long))
        return dict(accepted=eos in terminal_allowed, tokens=len(ids), native_EOS_allowed=eos in terminal_allowed)

    for row in rows:
        value = copy.deepcopy(valid)
        value['claims'][0]['quote_id'] = row['quote_id']
        text = json.dumps(value, separators=(',', ':'))
        char_result = characters(text)
        token_result = tokens(text)
        assert char_result['accepted'] and token_result['accepted'], (row['quote_id'], char_result, token_result)
        resolved, binding = resolve_references(value, candidate)
        assert resolved['claims'][0]['text'] == row['text']
        reports.append(dict(case='exact_source_id_' + row['quote_id'], source_text_sha256=row['text_utf8_sha256'],
            source_occurrences=row['sources'], character_result=char_result, native_token_result=token_result))
    for label, change in [
        ('unknown_source_id', lambda v: v['claims'][0].update(quote_id='q9999')),
        ('dual_free_text_representation', lambda v: v['claims'][0].update(text='Invented claim.')),
        ('old_free_text_field', lambda v: (v['claims'][0].pop('quote_id'), v['claims'][0].update(text=rows[0]['text'])))]:
        value = copy.deepcopy(valid); change(value)
        encoded = json.dumps(value, separators=(',', ':'))
        char_result, token_result = characters(encoded), tokens(encoded)
        assert not char_result['accepted'] and not token_result['accepted'], (label, char_result, token_result)
        reports.append(dict(case=label, character_result=char_result, native_token_result=token_result))
    for status in ['supported', 'contradicted', 'insufficient', 'uncertain']:
        value = copy.deepcopy(valid)
        value['claims'][0]['status'] = status
        value['action']['status'] = status
        if status in ['supported', 'contradicted']:
            value['claims'][0]['evidence'] = [dict(observation_id=view.observation_id, image_index=0,
                coordinate_space='normalized_1000', box_xyxy=[0,0,1000,1000], description='Synthetic source-shape control only.')]
        if status == 'supported':
            value['action']['evidence'] = copy.deepcopy(value['claims'][0]['evidence'])
        result = characters(json.dumps(value, separators=(',', ':')))
        assert result['accepted']
        reports.append(dict(case='all_status_domains_remain_available_' + status, character_result=result,
            synthetic_source_shape_not_visual_support=True))
    wait = dict(claims=[], action=dict(status='supported', target_kind='not_applicable',
        reason='Pure native WAIT source-shape control.', evidence=[dict(source='candidate', span_id='full')]),
        acknowledges_visual_deficit=False, pure_wait=True)
    wait_schema = judge_schema(view, '<action>{"type":"wait"}</action>', phase='exact_source_reference')
    encoded = json.dumps(wait, separators=(',', ':'))
    char_result, token_result = characters(encoded, wait_schema), tokens(encoded, wait_schema)
    assert char_result['accepted'] and token_result['accepted']
    reports.append(dict(case='native_WAIT_empty_claims', character_result=char_result, native_token_result=token_result,
        synthetic_protocol_control_not_model_semantic_pass=True))
    old_reply_domain = []
    for ident, _, raw in originals:
        result = characters(raw['text'])
        assert not result['accepted']
        old_reply_domain.append(dict(request=ident, raw_reply_utf8_sha256=hashlib.sha256(raw['text'].encode('utf8')).hexdigest(),
            changed_wire_field_rejects_unchanged_old_reply=result,
            not_a_specific_tail_repair_or_semantic_improvement=True, original_reply_not_repaired_or_regenerated=True))
    original_system = payload['system']
    addition = extraction_boundary(candidate_source_units(candidate))
    old_tokens = len(tokenizer.encode(original_system, add_special_tokens=False))
    new_tokens = len(tokenizer.encode(original_system + addition, add_special_tokens=False))
    assert not torch.cuda.is_initialized()
    try:
        version = importlib.metadata.version('lm-format-enforcer')
    except importlib.metadata.PackageNotFoundError:
        version = None
    return dict(time=time.time(), passed=True, controls=reports, controls_count=len(reports),
        exact_source_ids_tested=len(rows), all_source_ids_native_character_and_token_accepted=True,
        original_failed_wire_domain_controls=old_reply_domain,
        canonical_dependency_root=str(deps), canonical_dependency_files_SHA_bound=len(actual),
        dependency_receipt_sha256=reference['primary_dependency_receipt_sha256'], library_version=version,
        tokenizer_class=type(tokenizer).__name__, primary_model_path=reference['primary_model'],
        original_0074_complete_prompt_IDs_sha256=prompt_sha, original_0074_prompt_tokens=len(prompt_ids),
        proposed_source_table_system_only_token_measurement=dict(original=old_tokens, proposed=new_tokens,
            delta=new_tokens-old_tokens, full_multimodal_new_input_capacity_or_future_histories_not_proven=True),
        witness_native_token_encoding='per-character exact native tokenizer IDs; CPU only, not model replies',
        ordinary_BPE_path_failure_exists_in_both_original_and_proposed_grammar=True,
        unchanged_runtime_and_canonical_library=True,
        CPU_grammar_and_tokenizer_only=True, no_model_weights_loaded=True, no_CUDA_context_initialized=True,
        no_real_model_negative_WAIT_semantic_or_capacity_pass=True, new_model_GUI_capture_action_scorer_paid_calls=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True)
    args = parser.parse_args()
    root = args.package.resolve()
    try:
        result = main(root, args.original.resolve())
        with (root / 'receipt.json').open('x') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps(dict(passed=True, controls=result['controls_count'], source_ids=result['exact_source_ids_tested'])))
    except BaseException as error:
        with (root / 'failure.json').open('x') as stream:
            json.dump(dict(time=time.time(), type=type(error).__name__, message=str(error),
                traceback=traceback.format_exc(), new_model_GUI_scorer_calls=0), stream)
        traceback.print_exc()
        sys.exit(1)
