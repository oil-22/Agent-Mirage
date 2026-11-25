"""CPU-only remote collector; imports no model weights or inference clients."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types


def collect(root, package, manifest_sha, expected, sources, auxiliary_expectation):
    import os
    def require(condition, reason):
        if not condition:
            raise ValueError(reason)
    def sha(path):
        h = hashlib.sha256()
        with Path(path).open('rb') as stream:
            for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest()
    read = lambda path: json.loads(Path(path).read_bytes())
    root, package = Path(root), Path(package)
    require(os.getuid() == 1033 and sha(package / 'manifest.json') == manifest_sha,
            'Unexpected owner or runtime manifest')
    manifest = read(package / 'manifest.json')
    for name, value in manifest['files'].items():
        require(sha(package / name) == value, 'Frozen runtime source differs: ' + name)
    for filename, source in sources.items():
        module = types.ModuleType(filename[:-3])
        sys.modules[filename[:-3]] = module
        exec(compile(source, filename, 'exec'), module.__dict__)
    mapper, selector = sys.modules['mixed_journal_map'], sys.modules['mixed_audit_selection']
    events, chain = mapper.verified_events((root / 'worker/journal/events.jsonl').read_bytes())
    plan = read(package / 'plan.json')
    predecessor = read(package / 'predecessor.json')
    require(manifest['tracks'] == 31 and manifest['total_original_tracks'] == 32, 'Wrong remaining queue')
    require(sha(package / 'predecessor.json') == manifest['predecessor_sha256'], 'Predecessor authority differs')
    require(sha(package / 'plan.json') == predecessor['unchanged_full_plan_sha256'], 'Original full32 plan differs')
    require(predecessor['excluded_run_ids'] == [plan['queue'][0]['run_id']] == ['fullhistory23-T000-clean-noaux'], 'Only sealed terminal may be excluded')
    require(sha(package / 'predecessor/original-technical-failure.json') == predecessor['original_terminal_sha256'], 'Original terminal bytes differ')
    mapping = mapper.map_requests(events, plan['queue'][1:], {'actor': 0, 'judge': 0, 'evidence': 0})
    selected = selector.select_completed_requests(mapping, list(expected))
    require(set(expected) <= {row['request'] for row in selected}, 'Missing selected request')
    reference = read(package / 'primary-reference.json')
    primary_model = Path(reference['primary_model'])
    runtime = read(reference['primary_expected_runtime'])
    for name, value in runtime['metadata_sha256'].items():
        require(sha(primary_model / name) == value, 'Primary native metadata differs: ' + name)
    from transformers import AutoTokenizer, GenerationConfig
    tokenizer = AutoTokenizer.from_pretrained(primary_model, local_files_only=True, trust_remote_code=True)
    device_map = {'model.visual': 3, 'model.language_model.embed_tokens': 3,
                  'model.language_model.norm': 2, 'model.language_model.rotary_emb': 2, 'lm_head': 2}
    for i in range(64):
        device_map['model.language_model.layers.' + str(i)] = 0 if i < 18 else 1 if i < 36 else 2 if i < 51 else 3
    require(device_map == read(root / 'worker/new-placement.json')['device_map'], 'Native device map differs')
    template = read(package / 'actor-template.json')
    parameters = {k: v for k, v in template.items() if k != 'messages'}
    schema, prompts = types.ModuleType('source_schema'), types.ModuleType('source_prompts')
    exec(compile((package / 'release/defense/schema.py').read_bytes(), 'source-schema', 'exec'), schema.__dict__)
    exec(compile((package / 'release/defense/prompts.py').read_bytes(), 'source-prompts', 'exec'), prompts.__dict__)
    transitions = [event for event in events if event['kind'] == 'GPU_weight_residency_transition']
    aux_ref = read(package / 'auxiliary-identity-reference.json')
    aux_tokenizer, expected_tensor_proofs, tensor_sources = None, None, None
    bindings, reports = {}, []
    for row in selected:
        ident, operation = row['request'], row['operation']
        path = root / 'worker/requests' / ident
        require(path.stat().st_uid == 1033, 'Native request owner differs')
        require(sha(path / 'seal.json') == row['seal_sha256'], 'Journal/request seal mismatch')
        if ident in expected:
            require(expected[ident] == row['seal_sha256'], 'Inspected request seal differs')
        files = read(path / 'seal.json')
        for name, value in files.items():
            require((path / name).resolve().is_relative_to(path.resolve()), 'Receipt path escapes request')
            require(sha(path / name) == value, 'Full original request SHA differs: ' + name)
        data = {name: read(path / name) for name in ['external-wire.json', 'payload.json', 'response.json',
                'prepared.json', 'first-forward.json', 'effective-generation.json', 'actual-generation.json',
                'sequence_ids.json', 'forward-count.json']}
        wire, response = data['external-wire.json'], data['response.json']
        require(mapper.canonical(wire) == (path / 'external-wire.json').read_bytes(), 'Noncanonical original HTTP wire')
        payload, actual = wire['payload'], data['actual-generation.json']
        require(payload == data['payload.json'], 'Payload file differs from original wire')
        binding = dict(wire_sha256=sha(path / 'external-wire.json'), payload_sha256=hashlib.sha256(mapper.canonical(payload)).hexdigest(),
                       request_id=wire['request_id'], request_seal_sha256=row['seal_sha256'],
                       response_raw_sha256=hashlib.sha256(mapper.canonical(response)).hexdigest(),
                       response=response, receipt=str(path), mapped_request=row,
                       frozen_run=next(item for item in read(package / 'plan.json')['queue'] if item['run_id'] == row['trajectory_id']))
        require(binding['payload_sha256'] == row['payload_sha256'], 'Actual payload differs from mapped request')
        if operation in ['actor', 'judge']:
            cfg = GenerationConfig.from_pretrained(primary_model, local_files_only=True)
            cfg.do_sample, cfg.max_new_tokens = False, 2048 if operation == 'actor' else 4096
            if operation == 'actor':
                cfg.temperature = 0.0
            else:
                cfg.temperature, cfg.top_p, cfg.top_k = 1.0, 1.0, 0
            grammar = None
            if operation == 'judge':
                view = types.SimpleNamespace(**payload['view'])
                grammar = schema.judge_schema(view, payload['candidate'],
                    phase='history_report' if payload['system'].startswith(prompts.HISTORY_REPORT) else None)
            session = row['primary_prefill_session']
            prefill_path = root / 'worker' / ('prefill-residency-%03d.json' % session)
            prefill_event = next(e for e in events if e['sha256'] == row['prefill_completion_event_sha256'])
            proof = sys.modules['primary_receipt_checks'].check_primary_receipts(
                external_request=wire, response=response, mapped_request=row,
                prepared=data['prepared.json'], first_forward=data['first-forward.json'],
                effective_generation=data['effective-generation.json'], expected_generation=cfg.to_dict(),
                native_call=read(path / 'native-call.json'), actual_generation=actual,
                sequence_ids=data['sequence_ids.json'], forward_count=data['forward-count.json'],
                independently_decoded_native_output=tokenizer.decode(actual['output_ids'], skip_special_tokens=True),
                verified_file_SHA256=files, prefill=read(prefill_path), prefill_completion_event=prefill_event,
                expected_device_map=device_map, expected_group_order=list(device_map),
                expected_actor_parameters=parameters, expected_verifier_schema=grammar)
            proof.update(prefill_file=str(prefill_path), prefill_file_sha256=sha(prefill_path))
        else:
            require(operation == 'evidence', 'Unknown native operation')
            aux_model = Path(aux_ref['base_model']['local_path'])
            for item in aux_ref['metadata_files']:
                require(sha(aux_model / item['filename']) == item['sha256'], 'Auxiliary native metadata differs')
            if aux_tokenizer is None:
                aux_tokenizer = AutoTokenizer.from_pretrained(aux_model, local_files_only=True, trust_remote_code=False)
            helper = sys.modules['auxiliary_receipt_checks']
            native_bytes = helper.selected_token_bytes(aux_tokenizer, actual['output_ids'], [248044, 248046])
            spec = importlib.util.spec_from_file_location('frozen_mixed_schema', package / 'bounded_schema.py')
            bounded_schema = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bounded_schema)
            proof = helper.check_auxiliary_receipts(request=payload, original_image=(path / 'original.png').read_bytes(),
                fixed_prompt=(package / 'fixed-prompt.txt').read_text(encoding='utf8'),
                expected_model=aux_ref['base_model']['repo'], expected_revision=aux_ref['base_model']['revision'],
                prepared=data['prepared.json'], first_forward=data['first-forward.json'],
                effective_generation=data['effective-generation.json'], expected_generation=auxiliary_expectation,
                actual_generation=actual, sequence_ids=data['sequence_ids.json'], raw_output=(path / 'raw-output.txt').read_bytes(),
                raw_native_token_bytes=(path / 'generated-raw-utf8.bin').read_bytes(),
                independently_decoded_native_output=aux_tokenizer.decode(actual['output_ids'], skip_special_tokens=True,
                                                                          clean_up_tokenization_spaces=False),
                independently_reconstructed_native_token_bytes=native_bytes,
                input_boundary=read(path / 'stateless-input-boundary.json'),
                discarded_context=read(path / 'stateless-context-discarded.json'),
                mask_steps=read(path / 'actual-mask-steps.json'), unicode_guard=read(path / 'unicode-length-guard.json'),
                utf8_validation=read(path / 'raw-UTF8-validation.json'),
                expected_schema_sha256=bounded_schema.schema_sha256(),
                expected_unicode_guard_sha256=sha(package / 'unicode_length_guard.py'), verified_file_SHA256=files)
            require(data['forward-count.json']['actual_forward_calls'] == actual['actual_forward_calls'],
                    'Auxiliary audit wrapper/native forward count differs')
            if expected_tensor_proofs is None:
                expected_tensor_proofs, tensor_sources = expected_tensors(package, root, reference, aux_model, device_map, sha)
            transition_events = [next(e for e in transitions if e['sha256'] == t['event_sha256'])
                                 for t in row['residency_transitions']]
            transition_files, transition_bindings = [], []
            for event in transition_events:
                index = next(i for i, value in enumerate(transitions, 1) if value['sha256'] == event['sha256'])
                transition_path = root / 'worker' / ('residency-transition-%02d.json' % index)
                transition_files.append(read(transition_path))
                transition_bindings.append(dict(path=str(transition_path), sha256=sha(transition_path), event_sha256=event['sha256']))
            cycle = sys.modules['mixed_exchange_checks'].check_gpu_cycle(mapped_request=row,
                transition_events=transition_events, transition_files=transition_files,
                expected_primary_groups=[name for name, device in device_map.items() if device == 3],
                expected_tensor_proofs=expected_tensor_proofs, auxiliary_native_forwards=actual['actual_forward_calls'])
            proof.update(GPU_cycle=cycle, transition_files=transition_bindings, tensor_metadata_sources=tensor_sources)
            binding['original_auxiliary_output_sha256'] = files['raw-output.txt']
        reports.append(dict(request=ident, operation=operation, request_seal_sha256=row['seal_sha256'],
                            verified_original_files=len(files), native_proof=proof))
        bindings[ident] = binding
    import torch
    require(not torch.cuda.is_initialized(), 'CPU-only read-only auditor initialized CUDA')
    return dict(passed=True, source_chain=chain, mapping_scope=mapping['scope'], bindings=bindings, reports=reports,
                CUDA_initialized=False, model_weights_loaded=False, runtime_modified=False,
                new_model_GUI_scorer_calls=0, semantic_correctness_or_efficacy_established=False)


def expected_tensors(package, root, reference, aux_model, device_map, sha):
    """Derive counts from sealed primary meta state and native auxiliary meta init."""
    import torch
    import inspect
    from transformers import AutoConfig, AutoModelForImageTextToText, Qwen3_5ForConditionalGeneration
    read = lambda path: json.loads(Path(path).read_bytes())
    bound_path = Path(reference['primary_native_layout_receipt'])
    assert sha(bound_path) == reference['primary_native_layout_receipt_sha256']
    bound = read(bound_path)
    meta_root = Path(bound['meta_root'])
    for name, value in read(meta_root / 'seal.json').items():
        assert sha(meta_root / name) == value
    expected_state = read(meta_root / 'meta-state.json')
    primary_config = AutoConfig.from_pretrained(reference['primary_model'], local_files_only=True, trust_remote_code=True)
    auxiliary_config = AutoConfig.from_pretrained(aux_model, local_files_only=True, trust_remote_code=False)
    primary_config._attn_implementation = auxiliary_config._attn_implementation = 'sdpa'
    previous_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.bfloat16)
        with torch.device('meta'):
            primary_meta = AutoModelForImageTextToText.from_config(primary_config, trust_remote_code=True)
            auxiliary = Qwen3_5ForConditionalGeneration(auxiliary_config)
    finally:
        torch.set_default_dtype(previous_dtype)
    assert sha(Path(inspect.getfile(type(primary_meta)))) == bound['native_source_sha256']
    def records(pairs):
        return [dict(name=name, dtype=str(t.dtype), shape=list(t.shape), bytes=t.numel() * t.element_size())
                for name, t in pairs]
    actual_state = records(primary_meta.state_dict().items())
    fields = ['name', 'dtype', 'shape', 'bytes']
    assert len(actual_state) == len(expected_state)
    assert {row['name']: {key: row[key] for key in fields} for row in actual_state} == {
        row['name']: {key: row[key] for key in fields} for row in expected_state}
    # state_dict excludes nonpersistent native buffers. The original actual
    # tensor auditor includes them; retain their source-created float32 dtype.
    primary = records(list(primary_meta.named_parameters()) + list(primary_meta.named_buffers()))
    aux_rows = records(list(auxiliary.named_parameters()) + list(auxiliary.named_buffers()))
    assert aux_rows and all(t.device.type == 'meta' for model in [primary_meta, auxiliary]
                            for t in list(model.parameters()) + list(model.buffers()))
    del auxiliary, primary_meta

    def summarize(rows, auxiliary=False):
        byte_counts, dtype_counts = {}, {}
        for row in rows:
            n = 1
            for width in row['shape']:
                n *= width
            if auxiliary:
                device = 'cuda:3'
            else:
                matches = [name for name in device_map if row['name'] == name or row['name'].startswith(name + '.')]
                assert matches, row['name']
                device = 'cuda:' + str(device_map[max(matches, key=len)])
            byte_counts[device] = byte_counts.get(device, 0) + row['bytes']
            dtype_counts[row['dtype']] = dtype_counts.get(row['dtype'], 0) + n
        return dict(devices=sorted(byte_counts), tensor_count=len(rows), tensor_bytes_by_device=byte_counts,
                    dtype_elements={name: dtype_counts[name] for name in sorted(dtype_counts)})
    primary_proof, aux_proof = summarize(primary), summarize(aux_rows, True)
    assert primary_proof == read(root / 'worker/loaded.json')['primary_CUDA']
    assert not torch.cuda.is_initialized()
    return [aux_proof, primary_proof], dict(primary_meta_receipt=str(bound_path), primary_meta_receipt_sha256=sha(bound_path),
        primary_meta_state_sha256=sha(meta_root / 'meta-state.json'), auxiliary_native_meta_only=True,
        auxiliary_config_sha256=sha(aux_model / 'config.json'), BF16_parameters_with_native_buffer_dtypes_preserved=True,
        primary_nonpersistent_native_buffers_included=True,
        current_GPU_tensor_values_independently_hashed=False)
