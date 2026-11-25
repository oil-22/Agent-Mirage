import hashlib,inspect,sys
from pathlib import Path
from runtime_guard import P,require,save,sha,load

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
