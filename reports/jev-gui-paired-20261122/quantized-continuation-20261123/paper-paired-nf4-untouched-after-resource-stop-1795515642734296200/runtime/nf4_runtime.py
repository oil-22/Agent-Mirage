"""Load the original checkpoint in NF4 and qualify full native three-card inference."""
import hashlib
import json
import time
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def load(model_path, placement, torch, bnb, auto_model, config_cls):
    assert torch.cuda.device_count() == 3 and torch.cuda.is_bf16_supported()
    assert bnb.__version__ == '0.50.2'
    quant = config_cls(load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True,
                       bnb_4bit_compute_dtype=torch.bfloat16,
                       llm_int8_skip_modules=['model.visual', 'lm_head'])
    model = auto_model.from_pretrained(model_path, dtype=torch.bfloat16, attn_implementation='sdpa',
        device_map=placement, max_memory={i: '21GiB' for i in range(3)}, quantization_config=quant,
        local_files_only=True, trust_remote_code=True).eval()
    assert model.is_loaded_in_4bit and model.hf_device_map == placement
    return model, quant


def audit(model, expected, placement, torch, bnb):
    # Audit the real packed weights and their quantization state. The synthetic
    # state_dict export of bitsandbytes may serialize metadata on the CPU.
    known = {v['name']: v for v in expected}
    wanted = {n for n, v in known.items() if n.startswith('model.language_model.layers.') and
              n.endswith('.weight') and len(v['shape']) == 2}
    assert len(wanted) == 496, len(wanted)
    found = {n+'.weight': m for n, m in model.named_modules() if isinstance(m, bnb.nn.Linear4bit)}
    assert found.keys() == wanted, {'missing': sorted(wanted-found.keys()), 'unexpected': sorted(found.keys()-wanted)}
    tensors = dict(model.named_parameters(remove_duplicate=False))
    for name, t in model.named_buffers(remove_duplicate=False):
        if name in known:
            assert name not in tensors
            tensors[name] = t
    assert tensors.keys() == known.keys(), {'missing': sorted(known.keys()-tensors.keys()), 'unexpected': sorted(tensors.keys()-known.keys())}
    result, quant_states = [], []
    for name, t in tensors.items():
        matches = [p for p in placement if name.startswith(p+'.')]
        assert matches and t.device.type == 'cuda' and t.device.index == placement[max(matches,key=len)], name
        expected_t = known[name]
        row = {'name': name, 'shape': list(t.shape), 'dtype': str(t.dtype), 'device': str(t.device),
               'bytes': t.numel()*t.element_size()}
        if name in found:
            mod = found[name]; state = t.quant_state
            assert mod.weight is t and t.bnb_quantized and (mod.quant_state is None or state is mod.quant_state)
            assert t.dtype == torch.uint8 and t.numel() == (expected_t['bytes']//2+1)//2, name
            assert state.quant_type == 'nf4' and state.nested and list(state.shape) == expected_t['shape'], name
            assert state.dtype == torch.bfloat16 and mod.compute_dtype == torch.bfloat16, name
            row['original_shape'] = list(state.shape)
            row['quantization'] = 'nf4_double'
            for attr, value in (('absmax', state.absmax), ('code', state.code), ('offset', state.offset),
                                ('state2.absmax', state.state2.absmax), ('state2.code', state.state2.code)):
                assert isinstance(value, torch.Tensor) and value.device == t.device, (name, attr, value.device)
                quant_states.append({'weight': name, 'field': attr, 'device': str(value.device),
                                     'dtype': str(value.dtype), 'bytes': value.numel()*value.element_size()})
        else:
            assert all(row[k] == expected_t[k] for k in ('shape', 'dtype', 'bytes')), name
        result.append(row)
    devices = {row['device'] for row in result}
    assert devices == {'cuda:0', 'cuda:1', 'cuda:2'}
    summary = {'original_logical_parameter_and_persistent_buffer_names': len(known),
               'quantized_language_linear_modules': len(found), 'native_MTP_not_instantiated': True,
               'unquantized_visual_embedding_and_head': True, 'CPU_disk_offload': False,
               'weight_and_quantization_metadata_bytes_by_device': {
                   d: sum(row['bytes'] for row in result + quant_states if row['device'] == d)
                   for d in sorted(devices)}}
    return result, quant_states, summary


def qualify(native, package, root, save, sha, resource, journal):
    target = root/'capacity'; target.mkdir(exist_ok=False)
    binding = read(package/'parent-capacity.json')
    capacity = Path(binding['output'])/'capacity'
    source = capacity/'50-image-source-bound-stress'
    probe = binding['capacity_terminal']['probes'][0]
    assert sha(capacity/'seal.json') == binding['parent_capacity_seal_sha256']
    assert sha(source/'body.json') == probe['body_sha256']
    source_seal = read(source/'seal.json')
    assert sha(source/'first-forward.json') == source_seal['first-forward.json']
    (target/'body.json').write_bytes((source/'body.json').read_bytes())
    body = read(target/'body.json'); expected = read(source/'first-forward.json')
    template = read(package/'actor-template.json')
    assert body['messages'][0] == template['messages'][0]
    assert {k:v for k,v in body.items() if k!='messages'} == {k:v for k,v in template.items() if k!='messages'}
    assert body['max_tokens'] == 2048
    save(target/'source.json', {'source': str(source), 'source_body_sha256': sha(target/'body.json'),
         'BF16_forward_tensor_manifest_sha256': sha(source/'first-forward.json'),
         'expected_input_tokens': 53167, 'expected_images': 50, 'independent_capacity_only': True})
    save(target/'admission-before.json',resource(True))
    native.support.reset_memory(native.torch)
    started = time.monotonic()
    journal.emit('NF4_capacity_request', {'body_sha256':sha(target/'body.json'), 'engineering_only':True})
    try:
        reply = native.generate(body, target)
        first = read(target/'first-forward.json'); prepared = read(target/'prepared.json')
        assert first.keys() == prepared.keys() == expected.keys()
        for key in first:
            for field in ('shape','dtype','bytes','sha256'):
                assert first[key][field] == prepared[key][field] == expected[key][field], (key,field)
        assert first['input_ids']['shape'] == [1,53167] and first['image_grid_thw']['shape'] == [50,3]
        g = read(target/'actual-generation.json')
        assert g['natural_EOS'] and g['actual_forward_calls'] >= 1
        assert read(target/'effective-generation.json')['max_new_tokens'] == 2048
        save(target/'admission-after.json',resource(True))
        save(target/'qualification.json', {'passed': True, 'body_sha256': sha(target/'body.json'),
             'actual_first_forward_sha256': sha(target/'first-forward.json'),
             'reply_sha256': hashlib.sha256(reply.encode()).hexdigest(), 'input_tokens': g['input_tokens'],
             'output_tokens': g['output_tokens'], 'natural_EOS': True, 'actual_forward_calls':g['actual_forward_calls'],
             'original_2048_output_cap': True, 'identical_complete_native_input_bytes_to_BF16': True,
             'peak_memory': g['memory'], 'seconds_with_audit': time.monotonic()-started,
             'NF4_engineering_calls': 1, 'GUI_actions': 0, 'official_scores': 0,
             'not_an_experiment_trajectory_or_output_equivalence_test': True})
    finally:
        save(target/'seal.json',{p.name:sha(p) for p in target.iterdir() if p.is_file()})
    journal.emit('NF4_capacity_passed', {'seal_sha256':sha(target/'seal.json'), 'engineering_only':True})
    return {'summary': read(target/'qualification.json'), 'seal_sha256':sha(target/'seal.json')}
