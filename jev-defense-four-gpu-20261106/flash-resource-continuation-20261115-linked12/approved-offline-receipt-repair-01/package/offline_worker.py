from receipt_binding import verify_cpu_receipt
"""Ten approved offline primary calls; zero GUI/Flash/scorer or automatic retries."""
import copy
import hashlib
import inspect
import json
import os
import signal
import sys
import textwrap
import time
import traceback
from pathlib import Path

import offline_guard as guard
from offline_guard import P, save, sha, load, require


def install_previous_memory_implementation(native, root, manifest):
    """Reinstall exactly the already tested implementation, without extra calls.

    Prior bitwise/capacity results are referenced at their original test times;
    this is not a fresh numerical-invariance or altered-input capacity test.
    """
    import memory_lifetime
    import mlp_lifetime
    package = P / 'native'
    prior = Path(manifest['prior_memory_proof'])
    require(sha(prior) == manifest['prior_memory_proof_sha256'], 'Previous memory proof changed')
    proof = load(prior)
    require(proof['installed'] and proof['all_full_vocab_logits_and_sequence_ids_bitwise_equal'], 'Missing prior numerical proof')
    module = sys.modules[type(native.engine.model).__module__]
    require(sha(Path(module.__file__)) == proof['source_native_module_sha256'], 'Native model source changed')
    raw = inspect.unwrap(module.torch_chunk_gated_delta_rule)
    source = (package / 'torch_chunk_lifetime.py').read_text()
    require(sha(package / 'torch_chunk_lifetime.py') == proof['repair_source_sha256'], 'Validated chunk implementation changed')
    normalized = memory_lifetime.arithmetic_ast(inspect.getsource(raw))
    require(normalized == memory_lifetime.arithmetic_ast(source), 'Normalized numerical AST changed')
    require(hashlib.sha256(normalized.encode()).hexdigest() == proof['arithmetic_AST_sha256'], 'Prior numerical AST binding changed')
    namespace = dict(raw.__globals__)
    exec(compile(source, str(package / 'torch_chunk_lifetime.py'), 'exec'), namespace)
    candidate = namespace['torch_chunk_gated_delta_rule']
    mlp = module.Qwen3_5MLP.forward
    require(hashlib.sha256(inspect.getsource(mlp).encode()).hexdigest() == proof['MLP_memory_proof']['source_native_MLP_sha256'], 'Original MLP source changed')
    require(sha(package / 'mlp_lifetime.py') == proof['MLP_memory_proof']['memory_MLP_source_sha256'], 'Validated MLP implementation changed')
    require(native.engine.model.config.text_config.hidden_act == 'silu', 'Unexpected activation')
    require(not raw.__code__.co_freevars and not candidate.__code__.co_freevars and not mlp.__code__.co_freevars and not mlp_lifetime.forward.__code__.co_freevars, 'Unbound function closure')
    raw.__code__ = candidate.__code__
    mlp.__code__ = mlp_lifetime.forward.__code__
    save(root / 'prior-memory-implementation-reinstalled.json', {
        'prior_result': str(prior), 'prior_result_sha256': sha(prior),
        'same_source_implementation_reinstalled': True,
        'new_capacity_or_invariance_generations': 0,
        'previous_tests_retained_at_original_time': True,
        'changed_prompt_input_GPU_capacity_not_yet_proven': True})
    return raw, candidate.__code__, mlp, mlp_lifetime.forward.__code__


def checked_generate(native, body, folder, cpu, old_generation):
    torch = native.torch
    engine = native.engine
    expected = cpu['proposed_prepared']
    original_apply = engine.processor.apply_chat_template
    original_generate = engine.model.generate
    first_seen = [False]
    generate_calls = [0]

    def records(tensors):
        return {key: {'shape': list(value.shape), 'dtype': str(value.dtype),
                      'bytes': value.numel() * value.element_size(),
                      'sha256': hashlib.sha256(value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()}
                for key, value in tensors.items()}

    def apply(*args, **kwargs):
        value = original_apply(*args, **kwargs)
        actual = records(value)
        guard.validate_tensor_records(actual, expected)
        save(folder / 'frozen-CPU-prepared-match.json', actual)
        return value

    def forward_hook(_model, args, kwargs):
        if first_seen[0]:
            return
        first_seen[0] = True
        require(not args, 'Unexpected positional model input')
        guard.resource(True)
        actual = records({key: kwargs[key] for key in expected})
        guard.validate_tensor_records(actual, expected)
        save(folder / 'frozen-CPU-first-forward-match.json', actual)

    def generate(*args, **kwargs):
        generate_calls[0] += 1
        require(generate_calls[0] == 1 and not args, 'Unexpected extra model.generate call')
        effective = kwargs['generation_config'].to_dict()
        require(effective == old_generation, 'Original effective generation config changed')
        require(effective['max_new_tokens'] == 2048 and effective['do_sample'] is False, 'Approved cap or greedy mode changed')
        save(folder / 'original-effective-generation-match.json', effective)
        return original_generate(**kwargs)

    engine.processor.apply_chat_template = apply
    engine.model.generate = generate
    handle = engine.model.register_forward_pre_hook(forward_hook, with_kwargs=True)
    try:
        result = native.generate(body, folder)
        require(first_seen[0] and generate_calls[0] == 1, 'Expected one actual first forward/generation')
        return result
    finally:
        handle.remove()
        engine.processor.apply_chat_template = original_apply
        engine.model.generate = original_generate
        save(folder / 'offline-generation-count.json', {'generate_calls': generate_calls[0], 'first_forward_seen': first_seen[0]})


def main():
    manifest, plan = guard.verify_package()
    root = Path(manifest['output']) / 'worker'
    root.mkdir(exist_ok=False)
    (root / 'requests').mkdir()
    save(root / 'process.json', guard.identity(os.getpid()))
    from gate_core import Journal
    journal = Journal(root / 'journal')
    stopped = [False]
    signal.signal(signal.SIGTERM, lambda *_: stopped.__setitem__(0, True))
    signal.signal(signal.SIGINT, lambda *_: stopped.__setitem__(0, True))
    attempted, finished, failure = 0, [], None
    began = time.time()
    native = None
    folder = None
    try:
        guard.resource(False)
        # Import and use the exact frozen NativeActor class. Only its resource
        # callback is redirected to the isolated offline ownership guard.
        for frozen in plan['inputs']:
            verify_cpu_receipt(P, Path(frozen['proposed_full_body']).parent, frozen, manifest)
        import primary_server
        primary_server.resource = guard.resource
        native = primary_server.NativeActor(root)
        installed = install_previous_memory_implementation(native, root, manifest)
        journal.emit('loaded', {'loaded_sha256': sha(root / 'loaded.json'), 'new_extra_preflight_model_calls': 0})
        suffix = (P / 'proposed-system-suffix.txt').read_text('utf8')
        for frozen in plan['inputs']:
            number = frozen['case']
            guard.allow_next_call(attempted, number, finished)
            require(not stopped[0], 'Manual stop before next approved call')
            source = Path(frozen['proposed_full_body']).parent
            cpu = verify_cpu_receipt(P, source, frozen, manifest)
            require(sha(source / 'seal.json') == manifest['CPU_case_seals'][str(number)], 'Frozen CPU seal changed')
            for name, expected in load(source / 'seal.json').items():
                require(sha(source / name) == expected, 'Frozen CPU raw file changed: ' + name)
            body_raw = (source / 'proposed-full-body.json').read_bytes()
            body = json.loads(body_raw)
            guard.validate_case(number, hashlib.sha256(body_raw).hexdigest(), body, cpu, frozen, suffix)
            old = guard.PREVIOUS_OUT / 'primary/requests' / ('%05d' % (19 + number))
            old_seal = load(old / 'seal.json')
            require(sha(old / 'seal.json') == cpu['source_request_seal_sha256'], 'Original source seal changed')
            require(sha(old / 'body.json') == frozen['original_body_sha256'] == cpu['source_body_sha256'], 'Original full body changed')
            original = load(old / 'body.json')
            amended = copy.deepcopy(original)
            amended['messages'][0]['content'] += '\n\n' + suffix
            require(amended == body, 'More than authorized system suffix changed')
            require(sha(old / 'effective-generation.json') == old_seal['effective-generation.json'], 'Original generation receipt changed')
            old_generation = load(old / 'effective-generation.json')
            folder = root / 'requests' / ('%02d' % number)
            folder.mkdir(exist_ok=False)
            (folder / 'body.json').write_bytes(body_raw)
            save(folder / 'source-binding.json', {'case': number, 'CPU_source': str(source),
                 'CPU_seal_sha256': sha(source / 'seal.json'), 'original_request': str(old),
                 'original_request_seal_sha256': sha(old / 'seal.json'),
                 'original_baseline_reply_referenced_not_rerun': True,
                 'approved_plan_sha256': sha(P / 'development-plan.json')})
            save(folder / 'admission-before.json', guard.resource(True))
            require(installed[0].__code__ is installed[1] and installed[2].__code__ is installed[3], 'Validated implementation was replaced')
            attempted += 1
            journal.emit('approved_offline_call', {'ordinal': attempted, 'case': number, 'body_file_sha256': sha(folder / 'body.json')})
            start = time.time()
            text = checked_generate(native, body, folder, cpu, old_generation)
            save(folder / 'admission-after.json', guard.resource(True))
            save(folder / 'response.json', {'case': number, 'text': text, 'seconds_with_audit': time.time() - start,
                 'GUI_Flash_scorer_calls': 0, 'proposed_action_not_executed': True})
            save(folder / 'seal.json', {p.name: sha(p) for p in folder.iterdir() if p.is_file()})
            journal.emit('offline_reply_sealed', {'case': number, 'seal_sha256': sha(folder / 'seal.json')})
            finished.append(number)
            folder = None
        require(attempted == 10 and finished == guard.CASES, 'Offline study incomplete')
    except BaseException:
        failure = {'error': traceback.format_exc(), 'time': time.time(),
                   'technical_failure_not_semantic_zero': True, 'no_automatic_retry': True}
        save(root / 'failure.json', failure)
        if folder is not None:
            save(folder / 'failure.json', failure)
            save(folder / 'seal.json', {p.name: sha(p) for p in folder.iterdir() if p.is_file()})
        journal.emit('preserved_failure', failure)
        traceback.print_exc()
    finally:
        save(root / 'terminal.json', {'status': 'completed' if failure is None else 'preserved_failure',
             'attempted_calls': attempted, 'completed_reply_cases': finished, 'maximum_calls': 10,
             'extra_capacity_or_invariance_generations': 0, 'new_Flash_GUI_scorer_paid_calls': 0,
             'baseline_replays': 0, 'format_or_automatic_retries': 0,
             'reserved_GPU_count_for_cost': 8, 'began': began, 'ended': time.time(),
             'Mirage_reduction': None, 'formal_GUI_release': False})
        sys.stdout.flush()
        sys.stderr.flush()
    return 0 if failure is None else 1


if __name__ == '__main__':
    raise SystemExit(main())
