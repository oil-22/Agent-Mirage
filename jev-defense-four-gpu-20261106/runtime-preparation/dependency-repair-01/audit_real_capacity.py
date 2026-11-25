"""Read-only real capacity audit plus exact native CPU input reconstruction.

No request, model load, generation, GUI, scorer or resource allocation. Run in the
original environment with CUDA_VISIBLE_DEVICES='' while both tested servers stay
resident, after the one actual primary response is sealed.
"""
import argparse
import ast
import base64
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import time
import traceback

WIRE_SHA = '921d1df12734b116f3a920e6caa769c9b148990c2efb6439febe9c47231e6a92'
FLASH_REVISION = '9ff7cf9838e59df461c276b7699d56b244d2af58'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as handle: json.dump(value, handle, ensure_ascii=False, indent=2)


def verify_seal(root, name='seal.json'):
    for relative, expected in json.loads((root / name).read_bytes()).items():
        if sha(root / relative) != expected:
            raise RuntimeError('Immutable file SHA mismatch: ' + str(root / relative))


def identity(pid):
    path = Path('/proc') / str(pid)
    stat = (path / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': int(pid), 'uid': path.stat().st_uid,
        'command': (path / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip(),
        'start_ticks': stat[19]}


def same_identity(actual, expected):
    return all(str(actual[key]) == str(expected[key]) for key in ('pid', 'uid', 'command', 'start_ticks'))


def actual_residency(group, config, lease):
    holder = identity(lease['holder']['pid'])
    assert same_identity(holder, lease['holder'])
    live = {}
    for role in ('primary', 'pplx_flash'):
        record = json.loads((group / role / 'process.json').read_bytes())
        actual = identity(record['identity']['pid'])
        assert same_identity(actual, record['identity']) and actual['uid'] == 1033
        assert actual['command'] == ' '.join(config['commands'][role])
        locks = []
        for row in lease['lock_records']:
            info = Path('/proc', str(actual['pid']), 'fdinfo', str(row['fd'])).read_text()
            path = Path('/proc', str(actual['pid']), 'fd', str(row['fd']))
            assert os.readlink(path) == row['path'] and path.stat().st_ino == row['inode'] and 'lock:' in info
            locks.append({'path': row['path'], 'inode': row['inode'], 'fd': row['fd']})
        assert len(locks) == 9
        live[role] = {'identity': actual, 'actual_inherited_held_locks': locks}
    raw_compute = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,used_memory',
        '--format=csv,noheader,nounits'], text=True)
    compute = [{'gpu_uuid': row.split(',')[0].strip(), 'pid': int(row.split(',')[1]),
                'used_MiB': int(row.split(',')[2])}
               for row in raw_compute.splitlines() if row.strip()]
    cards = {row['index']: row['uuid'] for row in lease['gpu']}
    assert sorted(cards) == [4, 5, 6, 7]
    owned = {row['identity']['pid']: role for role, row in live.items()}
    relevant = [row for row in compute if row['gpu_uuid'] in cards.values()]
    assert relevant and all(row['pid'] in owned for row in relevant)
    primary_pid = live['primary']['identity']['pid']
    flash_pid = live['pplx_flash']['identity']['pid']
    assert {r['gpu_uuid'] for r in relevant if r['pid'] == primary_pid} == set(cards.values())
    assert {r['gpu_uuid'] for r in relevant if r['pid'] == flash_pid} == {cards[7]}
    raw_gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.used,memory.free,memory.total',
        '--format=csv,noheader,nounits'], text=True)
    return {'time': time.time(), 'holder': holder, 'workers': live,
        'actual_task_compute': relevant, 'nvidia_compute_raw': raw_compute, 'nvidia_gpu_raw': raw_gpu,
        'both_models_actual_co_resident': True, 'no_unrelated_compute_on_four_leased_cards': True}


def reconstruct_native_inputs(config, body, torch):
    sys.path[:0] = [config['primary_release']]
    import defense.qwen_backend as backend
    from defense.core import PublicView, VisibleImage, canonical, digest
    from transformers import AutoProcessor, GenerationConfig
    assert sha(Path(backend.__file__)) == config['primary_backend_sha256']
    v = body['view']
    images = tuple(VisibleImage(base64.b64decode(item['raw_base64']), item['role']) for item in v['images'])
    view = PublicView(v['observation_id'], v['messages'], images,
        v.get('recent_action', ''), v.get('execution_feedback', ''), v['observed_at'])
    captured = {}
    class Capture:
        def generate(self, messages, max_tokens, receipt, seed=42, original_body=None, json_schema=None):
            captured.update(messages=messages, max_tokens=max_tokens, seed=seed,
                original_body=original_body, json_schema=json_schema)
            return 'CPU construction only; no model call'
    backend.LocalQwen.judge(Capture(), body['system'], view, body.get('candidate'), None)
    assert captured['max_tokens'] == 4096 and captured['original_body'] is None
    # Execute the exact original conversion + apply_chat_template AST prefix.
    # The model/grammar/generation statements after input construction are absent.
    source = textwrap.dedent(inspect.getsource(backend.LocalQwen.generate))
    function = ast.parse(source).body[0]
    end = [i for i, node in enumerate(function.body) if isinstance(node, ast.Assign)
           and any(isinstance(target, ast.Name) and target.id == 'inputs' for target in node.targets)]
    assert len(end) == 1
    original_prefix = copy.deepcopy(function.body[:end[0] + 1])
    function.name = 'native_CPU_input_prefix'
    function.body = original_prefix + [ast.Return(value=ast.Name(id='inputs', ctx=ast.Load()))]
    namespace = dict(vars(backend))
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(module, '<exact-original-native-input-prefix>', 'exec'), namespace)
    processor = AutoProcessor.from_pretrained(config['primary_model'], local_files_only=True, trust_remote_code=True)
    holder = type('CPUProcessorOnly', (), {'processor': processor})()
    inputs = namespace['native_CPU_input_prefix'](holder, captured['messages'], 4096, None,
        seed=42, original_body=None, json_schema=captured['json_schema'])
    assert all(value.device.type == 'cpu' for value in inputs.values() if isinstance(value, torch.Tensor))
    expected_cfg = GenerationConfig.from_pretrained(config['primary_model'], local_files_only=True)
    expected_cfg.do_sample = False; expected_cfg.max_new_tokens = 4096
    expected_cfg.temperature = 1.0; expected_cfg.top_p = 1.0; expected_cfg.top_k = 0
    return inputs, processor, expected_cfg.to_dict(), {'original_view_messages': len(v['messages']),
        'original_view_images': len(images), 'original_image_sha256': [digest(image.raw) for image in images],
        'constructed_request_messages_sha256': digest(canonical(captured['messages'])),
        'verifier_schema_sha256': digest(canonical(captured['json_schema'])),
        'original_generate_prefix_AST_sha256': hashlib.sha256(ast.dump(ast.Module(
            body=original_prefix, type_ignores=[]), include_attributes=False).encode()).hexdigest(),
        'original_generate_source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'original_judge_source_sha256': hashlib.sha256(inspect.getsource(backend.LocalQwen.judge).encode()).hexdigest(),
        'native_processor_only': True, 'source_conversion_AST_executed_unchanged': True}


def audit(a, root):
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    group = a.group
    config = json.loads((group / 'runtime-config.json').read_bytes())
    spec = json.loads((group / 'launch-specification.json').read_bytes())
    for name in ('runtime-config.json', 'launch-specification.json', 'process.json'):
        (root / name).write_bytes((group / name).read_bytes())
    native = Path(config['commands']['primary'][2]).parent
    # Exact command is [python,-u,worker,...].
    assert sha(native / 'preflight_service.py') == spec['worker_source_sha256']
    assert sha(native / 'four_gpu_contract.py') == spec['contract_source_sha256']
    sys.path.insert(0, str(native))
    from preflight_service import tensor_record, verify_flash_checkpoint
    lease_index = config['commands']['primary'].index('--lease')
    lease = json.loads(Path(config['commands']['primary'][lease_index + 1]).read_bytes())
    residency_before = actual_residency(group, config, lease)
    save(root / 'actual-residency-before.json', residency_before)
    requests = list((group / 'primary/requests').glob('*'))
    assert len(requests) == 1 and list((group / 'pplx_flash/requests').glob('*')) == []
    primary_admission = json.loads(Path(spec['roles']['primary']['admission']).read_bytes())
    helper_admission = json.loads(Path(spec['roles']['pplx_flash']['admission']).read_bytes())
    assert primary_admission['max_new_calls'] == 1
    assert helper_admission['mode'] == 'resident_only' and helper_admission['max_new_calls'] == 0 and helper_admission['requests'] == []
    request = requests[0]; verify_seal(request)
    assert sha(request / 'request.json') == WIRE_SHA and (request / 'response.json').exists()
    assert not (request / 'failure.json').exists()
    body = json.loads((request / 'request.json').read_bytes()); assert body['operation'] == 'judge'
    generation = json.loads((request / 'generation.json').read_bytes())
    response = json.loads((request / 'response.json').read_bytes())
    forwards = json.loads((request / 'forward-trace.json').read_bytes())
    assert sha(request / 'forward-trace.json') == response['forward_trace_sha256']
    primary_loaded = json.loads((group / 'primary/loaded.json').read_bytes())
    helper_loaded = json.loads((group / 'pplx_flash/loaded.json').read_bytes())
    runtime = json.loads((group / 'primary/runtime.json').read_bytes())
    original_runtime = json.loads(Path(config['primary_expected_runtime']).read_bytes())
    assert all(primary_loaded[key] == value for key, value in runtime.items())
    assert runtime['dtype'] == 'torch.bfloat16' and runtime['backend'] == 'sdpa'
    assert runtime['torch'] == original_runtime['torch'] and runtime['transformers'] == original_runtime['transformers']
    assert runtime['metadata_sha256'] == original_runtime['metadata_sha256']
    assert all(sha(Path(config['primary_model']) / name) == value for name, value in runtime['metadata_sha256'].items())
    assert primary_loaded['generate_and_judge_inherited_unchanged'] is True
    assert primary_loaded['native_MTP_not_instantiated'] is True and primary_loaded['actual_state_tensor_count'] == 1184
    assert primary_loaded['devices'] == ['cuda:0', 'cuda:1', 'cuda:2', 'cuda:3']
    assert primary_loaded['primary_dependency_receipt_sha256'] == spec['primary_dependency_receipt_sha256']
    assert primary_loaded['integration_sha256'] == '223e56d56be3f60d14b270c6db6cfedd19000adefb22f9d3aeaf5925a6035f47'
    assert helper_loaded['revision'] == FLASH_REVISION and helper_loaded['devices'] == ['cuda:0']
    assert helper_loaded['checkpoint_identity'] == verify_flash_checkpoint(config)
    import torch
    assert not torch.cuda.is_initialized()
    inputs, processor, expected_cfg, construction = reconstruct_native_inputs(config, body, torch)
    assert construction['original_view_messages'] == 43 and construction['original_view_images'] == 4
    cpu = {key: tensor_record(torch, value, key in {'input_ids', 'image_grid_thw', 'video_grid_thw'})
           for key, value in inputs.items() if isinstance(value, torch.Tensor)}
    assert 'input_ids' in cpu and 'pixel_values' in cpu and 'image_grid_thw' in cpu
    assert generation['input_ids'] == inputs['input_ids'][0].tolist()
    assert generation['request_messages_sha256'] == construction['constructed_request_messages_sha256']
    assert generation['verifier_grammar']['schema_sha256'] == construction['verifier_schema_sha256']
    assert generation['verifier_grammar']['engine'] == 'lm-format-enforcer' and generation['verifier_grammar']['version'] == '0.11.3'
    prefills = [record for record in forwards if 'pixel_values' in record.get('tensors', {})]
    assert len(prefills) == 1
    for key in ('input_ids', 'pixel_values', 'image_grid_thw'):
        assert prefills[0]['tensors'][key] == cpu[key], 'Actual native prefill differs from exact CPU processor: ' + key
    preparation_fields = {key: {'CPU_processor': value,
        'actual_native_prefill': prefills[0]['tensors'].get(key),
        'byte_identical': prefills[0]['tensors'].get(key) == value}
        for key, value in cpu.items() if key not in {'input_ids', 'pixel_values', 'image_grid_thw'}}
    actual_cfg = generation['generation_config']
    assert actual_cfg == expected_cfg, {key: [expected_cfg.get(key), actual_cfg.get(key)]
        for key in set(expected_cfg) | set(actual_cfg) if expected_cfg.get(key) != actual_cfg.get(key)}
    ids = generation['generated_ids']
    eos = actual_cfg['eos_token_id']; eos = eos if isinstance(eos, list) else [eos]
    assert 0 < len(ids) < 4096 and ids[-1] in eos and generation['hit_output_cap'] is False
    assert processor.tokenizer.decode(ids, skip_special_tokens=True).strip() == generation['text'] == response['verdict']
    assert response['input_tokens'] == len(generation['input_ids']) and response['output_tokens'] == len(ids)
    peaks = response['per_device_memory']; assert [row['logical_device'] for row in peaks] == [0, 1, 2, 3]
    assert all(0 < row['allocated_bytes'] <= row['peak_allocated_bytes'] <= row['peak_reserved_bytes'] for row in peaks)
    assert not torch.cuda.is_initialized()
    residency_after = actual_residency(group, config, lease)
    save(root / 'CPU-input-tensors.json', cpu)
    save(root / 'other-native-preparation-fields.json', preparation_fields)
    save(root / 'native-input-construction.json', construction)
    save(root / 'actual-residency-after.json', residency_after)
    save(root / 'per-role-memory.json', {'primary_actual_generation': peaks,
        'helper_loaded_memory': helper_loaded['memory'],
        'scope': 'role allocator peaks plus actual joint-residency samples; no invented simultaneous NVML peak sum'})
    return {'status': 'passed', 'capacity_passed': True, 'full_input_preserved': True,
        'actual_input_forward_audited': True, 'output_budget_4096_preserved': True,
        'scope': 'one selected known full-input engineering capacity request; not GUI history upper bound, semantic success, defense efficacy or independent task',
        'group': str(group), 'actual_request': str(request), 'request_seal_sha256': sha(request / 'seal.json'),
        'original_wire_sha256': WIRE_SHA, 'view_messages': 43, 'original_images': 4,
        'input_tokens': len(generation['input_ids']), 'output_tokens': len(ids), 'natural_EOS': True,
        'generation_seconds': generation['seconds'], 'primary_actual_model_forwards_requests': 1,
        'helper_new_model_requests': 0, 'helper_residency_only': True,
        'both_models_actual_co_resident': True, 'reserved_GPU_count': 4,
        'generation_config_sha256': hashlib.sha256(json.dumps(actual_cfg, sort_keys=True).encode()).hexdigest(),
        'primary_loaded_sha256': sha(group / 'primary/loaded.json'),
        'helper_loaded_sha256': sha(group / 'pplx_flash/loaded.json'),
        'dependency_cpu_receipt_sha256': spec['primary_dependency_receipt_sha256'],
        'CPU_audit_weights_loaded': False, 'CPU_audit_GPU_allocations': 0,
        'CPU_audit_model_requests': 0, 'GUI_actions': 0, 'currency': None, 'energy': None,
        'semantic_accuracy': None, 'defense_success': None, 'GUI_full_history_capacity_proven': False}


def main(a):
    root = a.output_root / str(time.time_ns()); root.mkdir(parents=True, exist_ok=False)
    (root / 'auditor-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        result = audit(a, root)
        save(root / 'receipt.json', result)
        print(json.dumps({'root': str(root), **result}))
    except BaseException:
        save(root / 'failure.json', {'status': 'audit_failed', 'traceback': traceback.format_exc(),
            'group': str(a.group), 'semantic_pass': None, 'model_requests_by_auditor': 0,
            'GPU_allocations_by_auditor': 0, 'weights_loaded_by_auditor': False})
        raise
    finally:
        save(root / 'seal.json', {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    main(parser.parse_args())
