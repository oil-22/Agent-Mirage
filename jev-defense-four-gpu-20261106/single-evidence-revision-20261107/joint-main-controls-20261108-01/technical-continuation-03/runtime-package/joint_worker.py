"""Finite real 27B + one image-only 9B development controls. No GUI/server."""
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

HERE = Path(__file__).resolve().parent
BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
LEASE = BASE / 'resource-attempt-20261106-01/lease.json'


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


def run(args):
    assert sha(args.manifest) == args.manifest_sha256
    package = args.manifest.parent
    manifest = json.loads(args.manifest.read_bytes())
    for n, h in manifest['files'].items():
        assert sha(package / n) == h, n
    assert sha(__file__) == manifest['worker_source_sha256']
    plan = json.loads((package / 'plan.json').read_bytes())
    assert plan['limits'] == {'auxiliary': 0, 'judge': 8, 'actor': 0, 'GUI': 0, 'scorer': 0,
                             'paid_API': 0, 'format_retries_per_judge': 1, 'semantic_resampling': False}
    assert not plan['auxiliary'] and [v['id'] for v in plan['judges']] == ['C05','C06','C07','C08']
    continuation = json.loads((package / 'continuation.json').read_bytes())
    parent = Path(continuation['parent_remote_root'])
    assert sha(parent / 'terminal-manifest.json') == continuation['parent_terminal_manifest_sha256']
    for n,h in json.loads((parent / 'terminal-manifest.json').read_bytes()).items():
        assert sha(parent / n) == h, 'Original preserved terminal changed: ' + n
    assert sha(parent / 'worker/terminal.json') == continuation['parent_terminal_sha256']
    assert sha(parent / 'exit.json') == continuation['parent_exit_sha256']
    parent_t = json.loads((parent / 'worker/terminal.json').read_bytes())
    assert parent_t['status'] == 'technical_failure'
    assert len(parent_t['attempted']['judge']) == continuation['prior_calls_including_OOM'] == 6
    assert parent_t['attempted']['judge'][-1] == {'case':'C05','call':'06'}
    assert len(parent_t['completed']['judge']) == 5 and len(parent_t['completed']['auxiliary']) == 4
    assert 6 + plan['limits']['judge'] <= continuation['original_judge_cap'] == 16
    assert not ({v['id'] for v in plan['judges']} & set(continuation['prior_completed_logical_controls']))
    for n in ['worker/process.json','launcher-process.json']:
        old_pid = json.loads((parent / n).read_bytes())['pid']
        assert not Path('/proc',str(old_pid)).exists(), 'Old process still exists; no duplicate allocation'
    assert os.getuid() == 1033 and os.environ['CUDA_VISIBLE_DEVICES'] == '4,5,6,7'
    assert os.environ['PYTORCH_CUDA_ALLOC_CONF'] == 'expandable_segments:True'
    assert not args.output.exists()
    args.output.mkdir()
    root = args.output
    sys.path.insert(0, str(package / 'release'))
    from defense.core import Controller, Journal, Limits, PublicView, VisibleImage, ValidationError
    from defense.qwen_backend import LocalQwen
    import image_evidence as contract
    from native_direction_consistency import check_direction
    journal = Journal(root / 'journal')
    from resource_gate import assert_owned_resources, identity, same_identity
    launcher = json.loads(os.environ['MIRAGE_JEV_LAUNCHER_IDENTITY'])
    assert same_identity(identity(os.getppid()), launcher)
    holder = manifest['expected_holder']
    me = identity(os.getpid())
    attempted = {'auxiliary': [], 'judge': []}
    completed = {'auxiliary': [], 'judge': []}
    error = None
    start = time.time()
    save(root / 'process.json', me)

    def resource(empty=False):
        assert not (root.parent / 'stop-requested.json').exists(), 'Stop marker; no next call'
        proof = assert_owned_resources(LEASE, holder, {me['pid']: me, launcher['pid']: launcher}, empty)
        journal.append('actual_resource_check', proof)
        return proof

    try:
        resource(True)
        # All model operations are in one process; separately opened mutex also
        # excludes any unrelated cooperative client using this task lease.
        mutex = Path(json.loads(LEASE.read_bytes())['inference_lock']).open('a')
        fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
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
                if target == root / 'judges/01':
                    assert set(prepared) == set(continuation['parent_failed_prepared'])
                    for n,v in prepared.items():
                        assert all(v[k] == continuation['parent_failed_prepared'][n][k]
                                   for k in ['shape','dtype','bytes','sha256']), 'Failed input changed: ' + n
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

        auxiliary_root = root / 'auxiliary'; auxiliary_root.mkdir()
        generation = copy.deepcopy(auxiliary_model.generation_config)
        for name in ['max_new_tokens', 'do_sample', 'temperature', 'top_p', 'top_k', 'num_beams', 'num_return_sequences', 'eos_token_id']:
            setattr(generation, name, aux_ref['generation'][name])
        assert generation.max_new_tokens == 2048 and generation.eos_token_id == [248044, 248046]
        for row in plan['auxiliary']:
            resource(); support.reset_memory(torch)
            p = package / row['path']; assert sha(p) == row['sha256']
            request = json.loads(p.read_bytes()); raw = contract.validate_image_only_request(request)
            target = auxiliary_root / row['id']; target.mkdir()
            save(target / 'request.json', request)
            (target / 'original.png').write_bytes(raw)
            messages = [{'role': 'user', 'content': [{'type': 'image', 'image': Image.open(io.BytesIO(raw)).convert('RGB')},
                                                    {'type': 'text', 'text': contract.FIXED_PROMPT}]}]
            attempted['auxiliary'].append(row['id'])
            journal.append('auxiliary_request', {'id': row['id'], 'request_sha256': row['sha256'], 'image_sha256': digest(raw),
                                                'task_history_candidate_or_labels_supplied': False})
            started = time.perf_counter(); torch.manual_seed(0)
            with audited_generation(auxiliary_model, auxiliary_processor, target):
                inputs = auxiliary_processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                    enable_thinking=False, tools=None, return_dict=True, return_tensors='pt')
                with torch.inference_mode():
                    output = auxiliary_model.generate(**inputs.to('cuda:3'), generation_config=generation,
                                                       return_dict_in_generate=True, output_scores=False)
            actual = json.loads((target / 'actual-generation.json').read_bytes())
            text = auxiliary_processor.tokenizer.decode(actual['output_ids'], skip_special_tokens=True, clean_up_tokenization_spaces=False)
            (target / 'raw-output.txt').write_bytes(text.encode())
            packet = None; contract_error = None
            try:
                packet = contract.actor_packet(request, text, actual['natural_EOS'])
                save(target / 'packet.json', packet)
            except Exception as exc:
                contract_error = {'type': type(exc).__name__, 'message': str(exc)}
                save(target / 'contract-error.json', contract_error)
            save(target / 'result.json', {'natural_EOS': actual['natural_EOS'], 'contract_valid': packet is not None,
                'contract_error': contract_error, 'seconds_including_instrumentation': time.perf_counter() - started,
                'semantic_correctness': None, 'no_retry': True})
            save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
            completed['auxiliary'].append(row['id'])
            journal.append('auxiliary_reply_sealed', {'id': row['id'], 'seal_sha256': sha(target / 'seal.json'),
                                                     'EOS': actual['natural_EOS'], 'contract_valid': packet is not None})
            del output, inputs
            torch.cuda.empty_cache()

        native_source = package / 'native-parser-source.py'
        tree = ast.parse(native_source.read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
        namespace = {'json': json, 're': re}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(native_source), 'exec'), namespace)
        parse = namespace['parse']
        judge_root = root / 'judges'; judge_root.mkdir()
        current_case = {'id': None}
        call_count = {'value': 0}
        def judge(system, view, candidate):
            resource()
            assert call_count['value'] < 8, 'Frozen continuation judge budget; prior6+new8<=16'
            call_count['value'] += 1
            rid = '%02d' % call_count['value']
            target = judge_root / rid; target.mkdir()
            save(target / 'request.json', {'case': current_case['id'], 'system': system, 'public': view.data(),
                'images': [{'raw_base64': base64.b64encode(im.raw).decode(), 'role': im.role} for im in view.images],
                'candidate': candidate, 'strict_native_judge_output_cap': 4096})
            if rid == '01':
                assert current_case['id'] == 'C05'
                assert sha(target / 'request.json') == continuation['parent_failed_request_sha256'], 'Original failed full request differs'
            attempted['judge'].append({'case': current_case['id'], 'call': rid})
            journal.append('primary_real_request', {'case': current_case['id'], 'call': rid, 'request_sha256': sha(target / 'request.json')})
            support.reset_memory(torch)
            with audited_generation(engine.model, engine.processor, target):
                text = engine.judge(system, view, candidate, receipt=target / 'generation.json')
            actual = json.loads((target / 'actual-generation.json').read_bytes())
            assert actual['natural_EOS'], 'Incomplete primary output preserved; no retry'
            (target / 'raw-output.txt').write_bytes(text.encode())
            save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
            completed['judge'].append({'case': current_case['id'], 'call': rid})
            journal.append('primary_real_reply_sealed', {'case': current_case['id'], 'call': rid,
                                                       'seal_sha256': sha(target / 'seal.json'), 'natural_EOS': True})
            return text
        ctl = Controller(judge, journal, 'post_only', Limits(max_verifier_calls=16), sleeper=lambda _: None)
        results = []
        for row in plan['judges']:
            resource()
            p = package / row['path']; assert sha(p) == row['sha256']
            frozen = json.loads(p.read_bytes()); v = frozen['view']; candidate = frozen['candidate']
            images = tuple(VisibleImage(base64.b64decode(im['raw_base64']), im['role']) for im in v['images'])
            view = PublicView(v['observation_id'], v['messages'], images, v['recent_action'], v['execution_feedback'], v['observed_at'])
            payload = parse(candidate)
            assert payload['type'] in {'click', 'scroll', 'wait'}
            if payload['type'] == 'click':
                assert all(type(payload[k]) in {int, float} and 0 < payload[k] < 1000 for k in ['x', 'y'])
            if payload['type'] == 'scroll':
                assert payload['direction'] in {'up', 'down'}
            proposal = {'name': payload['type'], 'parsed': True, 'executor_fallback_wait': False,
                        'payload': payload, 'coordinate_space': 'normalized_1000'}
            current_case['id'] = row['id']
            direction = check_direction(candidate, proposal)
            journal.observation(view, audience='new_constructed_control_main_judge')
            before = ctl.verifier_calls
            try:
                verdict = ctl.inspect('verify', view, candidate, proposal)
                result = {'id': row['id'], 'format_citation_contract_valid': True, 'verdict': verdict,
                          'supplemental_native_direction': direction, 'semantic_pass': None}
            except ValidationError as exc:
                result = {'id': row['id'], 'format_citation_contract_valid': False, 'error': str(exc),
                          'supplemental_native_direction': direction, 'semantic_pass': None}
            result['actual_judge_calls'] = ctl.verifier_calls - before
            save(root / (row['id'] + '-result.json'), result)
            results.append(result)
            journal.append('constructed_control_terminal', result)
            torch.cuda.empty_cache()
        save(root / 'summary.json', {'status': 'finite_joint_development_completed', 'actual_auxiliary_calls': len(attempted['auxiliary']),
            'actual_judge_calls': call_count['value'], 'actor_GUI_scorer_paid_calls': 0, 'controls': results,
            'both_models_jointly_resident': True, 'auxiliary_loaded_with_zero_new_auxiliary_calls': True,
            'prior_auxiliary_results_preserved': True, 'parent_judge_calls_including_OOM': 6,
            'cumulative_judge_calls_in_original16cap': 6 + call_count['value'],
            'full_GUI_capacity_or_efficacy_proven': False,
            'single_auxiliary_model_only': True, 'new_constructed_candidates_on_old_reviewed_views': True})
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'traceback': traceback.format_exc(),
                 'resource_evidence': getattr(exc, 'resource_evidence', None), 'no_automatic_retry': True}
        save(root / 'failure.json', error)
        journal.append('technical_failure_preserved', error)
    finally:
        save(root / 'terminal.json', {'status': 'technical_failure' if error else 'completed', 'attempted': attempted,
            'completed': completed, 'error': error, 'started_unix': start, 'ended_unix': time.time(),
            'GUI_actions': 0, 'scorer_calls': 0, 'old_terminals_reexecuted': False})
        journal.append('worker_terminal', {'status': 'technical_failure' if error else 'completed'})
        save(root / 'worker-manifest.json', {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()})
    return 1 if error else 0


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    try:
        code = run(a)
    except BaseException:
        # Pre-admission errors cannot alter any existing output or terminal.
        target = HERE / 'pre-admission-failures' / str(time.time_ns())
        target.mkdir(parents=True)
        save(target / 'failure.json', {'traceback': traceback.format_exc(), 'no_retry': True})
        code = 1
    raise SystemExit(code)
