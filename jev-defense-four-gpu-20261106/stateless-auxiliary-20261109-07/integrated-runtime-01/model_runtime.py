import argparse
import ast
import base64
import copy
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

def canonical(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')

def digest(v):
    return hashlib.sha256(v).hexdigest()

def sha(p):
    return digest(Path(p).read_bytes())

def save(p, value):
    with Path(p).open('xb') as f:
        f.write(canonical(value) + b'\n'); f.flush(); os.fsync(f.fileno())

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result

def load_runtime(package,root,journal,resource,manifest,me):
    from defense.qwen_backend import LocalQwen
    support = module('joint_primary_support', package / 'preflight_support.py')
    aux_support = module('joint_aux_identity', package / 'aux_identity_support.py')
    reference = json.loads((package / 'primary-reference.json').read_bytes())
    dependencies = support.verify_original_dependencies(reference)
    assert sha(package / 'release/defense/qwen_backend.py') == reference['primary_backend_sha256']
    expected_runtime = json.loads(Path(reference['primary_expected_runtime']).read_bytes())
    primary_path = Path(reference['primary_model'])
    for n, h in expected_runtime['metadata_sha256'].items():
        assert sha(primary_path / n) == h, n
    # Reuse the sealed native meta/header inventory; no full weights rehash.
    bound_path = Path(reference['primary_native_layout_receipt'])
    assert sha(bound_path) == reference['primary_native_layout_receipt_sha256']
    bound = json.loads(bound_path.read_bytes())
    meta_root = Path(bound['meta_root'])
    for n, h in json.loads((meta_root / 'seal.json').read_bytes()).items():
        assert sha(meta_root / n) == h
    expected_state = json.loads((meta_root / 'meta-state.json').read_bytes())
    header_root = Path(bound['header_inventory_root'])
    assert sha(header_root / 'seal.json') == bound['header_inventory_seal_sha256']
    header_seal = json.loads((header_root / 'seal.json').read_bytes())
    assert sha(header_root / 'headers.json') == header_seal['headers.json']
    headers = json.loads((header_root / 'headers.json').read_bytes())
    primary_stats = []
    for r in headers:
        p = primary_path / r['file']; st = p.stat()
        assert (st.st_size, st.st_mtime_ns) == (r['bytes'], r['mtime_ns'])
        primary_stats.append({'name': r['file'], 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns, 'inode': st.st_ino})
    assert len(primary_stats) == 18
    aux_ref = json.loads((package / 'auxiliary-identity-reference.json').read_bytes())
    aux_proof = root / 'auxiliary-identity'; aux_proof.mkdir()
    shards = aux_support.current_weight_identity(aux_ref, aux_proof, journal)
    save(root / 'checkpoint-admission.json', {'primary_header_stat_continuity': primary_stats,
        'primary_native_reference_sha256': sha(bound_path), 'primary_fresh_full_weight_hash': False,
        'auxiliary_sealed_full_SHA_and_current_stat': shards, 'dependencies': dependencies,
        'current_GPU_tensor_identity_still_pending': True})
    import torch
    import transformers
    from transformers import AutoProcessor, AutoModelForImageTextToText, Qwen3_5ForConditionalGeneration
    from PIL import Image
    assert torch.__version__ == expected_runtime['torch'] and transformers.__version__ == expected_runtime['transformers']
    device_map = {'model.visual': 0, 'model.language_model.embed_tokens': 0,
                  'model.language_model.norm': 2, 'model.language_model.rotary_emb': 2, 'lm_head': 2}
    for i in range(64):
        device_map['model.language_model.layers.' + str(i)] = 0 if i < 19 else 1 if i < 43 else 2
    parameter_lower = {i: 0 for i in range(3)}
    for row in expected_state:
        matching = [key for key in device_map if row['name'] == key or row['name'].startswith(key + '.')]
        assert matching, row['name']
        parameter_lower[device_map[max(matching, key=len)]] += row['bytes']
    assert all(v < 20 * 1024 ** 3 for v in parameter_lower.values())
    save(root / 'new-placement.json', {'primary_layer_counts': [19, 24, 21], 'device_map': device_map,
        'primary_parameter_bytes_by_logical_device': parameter_lower, 'primary_physical': [4, 5, 6],
        'auxiliary_physical': 7, 'joint_capacity_proven': False})
    resource(True)
    journal.append('load_started', {'primary': str(primary_path), 'auxiliary': aux_support.MODEL_PATH,
                                  'BF16': True, 'attention': 'sdpa', 'single_auxiliary_only': True})
    load_start = time.perf_counter()
    engine = LocalQwen.__new__(LocalQwen)
    engine.torch = torch
    engine.processor = AutoProcessor.from_pretrained(primary_path, local_files_only=True, trust_remote_code=True)
    engine.model = AutoModelForImageTextToText.from_pretrained(primary_path, dtype=torch.bfloat16,
        attn_implementation='sdpa', device_map=device_map, local_files_only=True, trust_remote_code=True).eval()
    primary_load_seconds = time.perf_counter() - load_start
    native_source = Path(inspect.getfile(type(engine.model)))
    assert sha(native_source) == bound['native_source_sha256']
    actual_state = [{'name': n, 'shape': list(t.shape), 'dtype': str(t.dtype), 'device': str(t.device),
                     'bytes': t.numel() * t.element_size()} for n, t in engine.model.state_dict().items()]
    state_proof = support.validate_native_state_records(actual_state, expected_state)
    primary_cuda = support.audit_tensors(torch, [('primary', engine.model)], ['cuda:0', 'cuda:1', 'cuda:2'])
    resource()
    load_start = time.perf_counter()
    auxiliary_processor = AutoProcessor.from_pretrained(aux_support.MODEL_PATH, local_files_only=True, trust_remote_code=False)
    auxiliary_model = Qwen3_5ForConditionalGeneration.from_pretrained(aux_support.MODEL_PATH,
        dtype=torch.bfloat16, attn_implementation='sdpa', device_map={'': 3}, local_files_only=True, trust_remote_code=False).eval()
    torch.cuda.synchronize()
    auxiliary_load_seconds = time.perf_counter() - load_start
    auxiliary_cuda = support.audit_tensors(torch, [('single_auxiliary', auxiliary_model)], ['cuda:3'])
    assert type(engine.model).__name__ == type(auxiliary_model).__name__ == 'Qwen3_5ForConditionalGeneration'
    for model in [engine.model, auxiliary_model]:
        assert all(t.dtype == torch.bfloat16 for t in model.parameters() if t.is_floating_point())
    for row in primary_stats:
        st = (primary_path / row['name']).stat()
        assert (st.st_size, st.st_mtime_ns, st.st_ino) == (row['bytes'], row['mtime_ns'], row['inode'])
    for row in shards:
        st = (Path(aux_support.MODEL_PATH) / row['filename']).stat()
        assert (st.st_size, st.st_mtime_ns, st.st_ino) == (row['bytes'], row['mtime_ns'], row['inode'])
    save(root / 'loaded.json', {'identity': me, 'primary_CUDA': primary_cuda, 'primary_native_state': state_proof,
        'auxiliary_CUDA': auxiliary_cuda, 'primary_load_seconds': primary_load_seconds,
        'auxiliary_load_seconds': auxiliary_load_seconds, 'primary_generation_backend_sha256': reference['primary_backend_sha256'],
        'native_model_source_sha256': sha(native_source), 'single_auxiliary': aux_ref['base_model'],
        'jev_relationship': aux_ref['jev_relationship'], 'torch': torch.__version__, 'transformers': transformers.__version__,
        'memory': support.memory(torch), 'GUI_started': False})
    journal.append('both_models_loaded', {'primary_load_seconds': primary_load_seconds,
        'auxiliary_load_seconds': auxiliary_load_seconds, 'actual_device_map': device_map, 'joint_generation_not_yet_proven': True})

    # Audit before device transfer and at the actual first forward. No input,
    # decoding, sampling, native generation logic, or returned tensor is edited.
    @contextmanager
    def audited_generation(model, processor, target):
        prepared = {}; count = {'value': 0}; first = {}
        original_apply = processor.apply_chat_template
        original_generate = model.generate
        def apply(*args, **kwargs):
            value = original_apply(*args, **kwargs)
            for name, tensor in value.items():
                assert isinstance(tensor, torch.Tensor), name
                prepared[name] = aux_support.tensor_record(tensor, torch, target, 'prepared_' + name, 'native_CPU_processor_before_device_transfer')
            save(target / 'prepared.json', prepared)
            return value
        def forward_hook(_m, _a, kwargs):
            if count['value'] == 0:
                for name in prepared:
                    tensor = kwargs.get(name)
                    assert isinstance(tensor, torch.Tensor), 'Actual forward omitted ' + name
                    record = aux_support.tensor_record(tensor, torch, target, 'first_forward_' + name, 'actual_model_forward')
                    assert all(record[k] == prepared[name][k] for k in ['shape', 'dtype', 'bytes', 'sha256']), name
                    first[name] = record
                save(target / 'first-forward.json', first)
            count['value'] += 1
        def generate(*args, **kwargs):
            assert not args, 'Unbound positional generation inputs'
            assert kwargs['input_ids'].shape[0] == 1
            cfg = kwargs['generation_config']
            save(target / 'effective-generation.json', cfg.to_dict())
            try:
                result = original_generate(**kwargs)
            except BaseException:
                save(target / 'failed-memory.json', support.memory(torch))
                raise
            sequence = result.sequences if hasattr(result, 'sequences') else result
            length = kwargs['input_ids'].shape[-1]
            assert torch.equal(sequence[:, :length], kwargs['input_ids']) and sequence.shape[0] == 1
            aux_support.tensor_record(sequence, torch, target, 'sequence_ids', 'actual_native_generate_return')
            ids = sequence[0, length:].detach().cpu().tolist()
            eos = cfg.eos_token_id
            eos = [eos] if isinstance(eos, int) else eos
            save(target / 'actual-generation.json', {'input_tokens': int(length), 'output_tokens': len(ids),
                'output_ids': ids, 'natural_EOS': bool(ids and ids[-1] in eos),
                'actual_forward_calls': count['value'], 'memory': support.memory(torch)})
            return result
        processor.apply_chat_template = apply
        model.generate = generate
        hook = model.register_forward_pre_hook(forward_hook, with_kwargs=True)
        try:
            yield
        finally:
            hook.remove(); processor.apply_chat_template = original_apply; model.generate = original_generate
            save(target / 'forward-count.json', {'actual_forward_calls': count['value'], 'first_forward_recorded': bool(first)})

    generation = copy.deepcopy(auxiliary_model.generation_config)
    for name in ['max_new_tokens', 'do_sample', 'temperature', 'top_p', 'top_k', 'num_beams', 'num_return_sequences', 'eos_token_id']:
        setattr(generation, name, aux_ref['generation'][name])
    assert generation.max_new_tokens == 2048 and generation.eos_token_id == [248044, 248046]
    return locals()
