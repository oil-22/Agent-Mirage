"""Audit-only native call wrapper; no imports or weight loading at module scope.

Caller supplies the unchanged LocalQwen engine and actual resource admission.
Unlike the original actor-only recorder, this supports the proposed 4096-token
preread explicitly. No new source code is installed into the model backend.
"""
import hashlib
from pathlib import Path
from offline_protocol import require, save


def tensor_records(torch, tensors):
    out = {}
    for key, value in tensors.items():
        require(isinstance(value, torch.Tensor), 'Unknown native input type')
        raw = value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()
        out[key] = {'shape': list(value.shape), 'dtype': str(value.dtype), 'bytes': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest()}
    return out


def compare_records(actual, expected):
    require(set(actual) == set(expected), 'Native input tensor set changed')
    for name, row in actual.items():
        require(all(row[k] == expected[name][k] for k in ['shape', 'dtype', 'bytes', 'sha256']),
                'Native input changed: ' + name)


def audited_generate(native, body, folder, expected, original_effective_generation,
                     max_output_tokens, resource_admission):
    engine, torch = native.engine, native.torch
    require(max_output_tokens in (2048, 4096) and body['max_tokens'] == max_output_tokens,
            'Unapproved output limit')
    expected_generation = dict(original_effective_generation)
    expected_generation['max_new_tokens'] = max_output_tokens
    apply_original = engine.processor.apply_chat_template
    generate_original = engine.model.generate
    seen = {'apply': 0, 'generate': 0, 'forward': 0, 'natural_EOS': False}

    def apply(*args, **kwargs):
        seen['apply'] += 1
        require(seen['apply'] == 1, 'Unexpected repeated preprocessing')
        tensors = apply_original(*args, **kwargs)
        records = tensor_records(torch, tensors)
        compare_records(records, expected)
        save(folder / 'actual-prepared.json', records)
        for key, value in tensors.items():
            with (folder / ('prepared_' + key + '.tensor')).open('xb') as stream:
                stream.write(value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())
        return tensors

    def first_forward(_model, args, kwargs):
        if seen['forward'] == 0:
            require(not args, 'Unexpected positional native input')
            resource_admission(True)
            compare_records(tensor_records(torch, {k: kwargs[k] for k in expected}), expected)
            save(folder / 'actual-first-forward.json', tensor_records(torch, {k: kwargs[k] for k in expected}))
            cache = kwargs.get('past_key_values')
            require(cache is None or cache.get_seq_length() == 0, 'Previous request KV state retained')
        seen['forward'] += 1

    def generate(*args, **kwargs):
        seen['generate'] += 1
        require(seen['generate'] == 1 and not args, 'Unexpected additional model.generate')
        effective = kwargs['generation_config'].to_dict()
        require(effective == expected_generation, 'Original effective generation config changed')
        require(effective['do_sample'] is False and effective['max_new_tokens'] == max_output_tokens,
                'Greedy or output cap changed')
        save(folder / 'effective-generation.json', effective)
        sequence = generate_original(**kwargs)
        size = kwargs['input_ids'].shape[-1]
        require(torch.equal(sequence[:, :size], kwargs['input_ids']), 'Output prefix differs from actual input IDs')
        ids = sequence[0, size:].detach().cpu().tolist()
        eos = effective['eos_token_id']; eos = [eos] if isinstance(eos, int) else eos
        seen['natural_EOS'] = bool(ids and ids[-1] in eos)
        raw = sequence.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()
        with (folder / 'sequence_ids.tensor').open('xb') as stream:
            stream.write(raw)
        save(folder / 'actual-generation.json', {'input_tokens': size, 'output_tokens': len(ids),
             'output_ids': ids, 'natural_EOS': seen['natural_EOS'], 'actual_forward_calls': seen['forward'],
             'sequence_shape': list(sequence.shape), 'sequence_dtype': str(sequence.dtype),
             'sequence_raw_sha256': hashlib.sha256(raw).hexdigest()})
        require(seen['natural_EOS'], 'Original EOS missing; preserve cap failure without retry')
        return sequence

    engine.processor.apply_chat_template = apply
    engine.model.generate = generate
    handle = engine.model.register_forward_pre_hook(first_forward, with_kwargs=True)
    try:
        # The original LocalQwen.generate implementation remains unchanged.
        text = engine.generate(body['messages'], max_output_tokens, folder / 'native-call.json',
                               seed=42, original_body=body)
        require(seen['apply'] == seen['generate'] == 1 and seen['forward'] > 0,
                'Missing actual input/generation/first forward')
        return {'text': text, 'natural_EOS': seen['natural_EOS'], 'model_generate_calls': seen['generate'],
                'first_forward_seen': seen['forward'] > 0, 'native_backend_unchanged': True,
                'proposed_actions_not_executed': True}
    finally:
        handle.remove()
        engine.processor.apply_chat_template = apply_original
        engine.model.generate = generate_original
        save(folder / 'native-call-accounting.json', seen)
