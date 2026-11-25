"""Install the exact previously validated process-local code, without replaying controls.

This is historical source-proof reuse, never a current-process capacity or logit test.
NativeActor construction and request generation remain byte-for-byte unchanged.
"""
import ast
import hashlib
import inspect
import json
import sys
import textwrap
from pathlib import Path


def validate_proof(binding):
    proof = binding['capacity_terminal']['memory_lifetime_patch']
    assert binding['capacity_terminal']['status'] == 'passed'
    assert proof['installed'] and proof['all_kernel_tests_bitwise_equal']
    assert proof['kernel_tests'] == 9 and proof['full_model_cached_steps'] == 3
    assert proof['all_full_vocab_logits_and_sequence_ids_bitwise_equal']
    assert proof['normalized_arithmetic_AST_equal_after_restoring_product_destinations']
    mlp = proof['MLP_memory_proof']
    assert mlp['actual_weight_GPU_output_bitwise_tests'] == 14 and mlp['all_tests_passed']
    assert mlp['actual_devices'] == ['cuda:' + str(i) for i in range(7)]
    terminal = binding['capacity_terminal']
    assert terminal['actual_capacity_model_generate_calls'] == 3
    assert terminal['physical_main_gpus'] == list(range(7)) and terminal['Flash_physical_gpu'] == 7
    assert terminal['main_precision'] == 'BF16' and terminal['attention'] == 'SDPA'
    assert len(terminal['probes']) == 1
    stress = terminal['probes'][0]
    assert stress['complete_images'] == 50 and stress['input_tokens'] == 53167
    assert stress['natural_EOS'] and stress['output_tokens'] == 126
    assert stress['complete_sequence_ids_equal_prior_unbatched_lifetime_result']
    assert len(stress['memory']) == 7
    assert min(r['headroom_at_reserved_peak_bytes'] for r in stress['memory']) >= 3 * 1024**3
    assert not terminal['all_future_histories_or_2048_token_each_worst_case_fit_proven']
    return proof


def install(native, package, root, save, sha, resource):
    from memory_lifetime import arithmetic_ast
    import mlp_lifetime

    binding = json.loads((package / 'parent-capacity.json').read_bytes())
    proof = validate_proof(binding)
    parent = Path(binding['output'])
    paths = {
        'capacity/seal.json': binding['parent_capacity_seal_sha256'],
        'capacity/terminal.json': binding['parent_capacity_terminal_sha256'],
        'capacity/lifetime-validation/source-proof.json': binding['parent_capacity_source_proof_sha256'],
        'capacity/lifetime-validation/result.json': binding['parent_capacity_result_sha256'],
    }
    for name, expected in paths.items():
        assert sha(parent / name) == expected, name
    assert json.loads((parent / 'capacity/terminal.json').read_bytes()) == binding['capacity_terminal']
    for name in ['memory_lifetime.py', 'torch_chunk_lifetime.py', 'mlp_lifetime.py',
                 'explicit-placement.json', 'actor-template.json', 'release/defense/qwen_backend.py',
                 'flash/gate-contract.json', 'flash/flash_runtime.py']:
        assert sha(package / name) == binding['source_hashes'][name], name
    resource(True)
    model = native.engine.model
    module = sys.modules[type(model).__module__]
    assert sha(Path(module.__file__)) == proof['source_native_module_sha256']
    raw = inspect.unwrap(module.torch_chunk_gated_delta_rule)
    before_chunk = raw.__code__
    original = inspect.getsource(raw)
    source_path = package / 'torch_chunk_lifetime.py'
    source = source_path.read_text()
    arithmetic = arithmetic_ast(original)
    assert arithmetic == arithmetic_ast(source)
    assert hashlib.sha256(arithmetic.encode()).hexdigest() == proof['arithmetic_AST_sha256']
    namespace = dict(raw.__globals__)
    exec(compile(source, str(source_path), 'exec'), namespace)
    candidate = namespace['torch_chunk_gated_delta_rule']
    assert not before_chunk.co_freevars and not candidate.__code__.co_freevars
    assert inspect.signature(raw) == inspect.signature(candidate)

    cls = module.Qwen3_5MLP
    mlp = cls.forward
    original_mlp = inspect.getsource(mlp)
    expected = ('def forward(self, x):\n'
                '    down_proj = self.down_proj(self.act_fn(self.gate_proj(x)) * self.up_proj(x))\n'
                '    return down_proj\n')
    assert ast.dump(ast.parse(textwrap.dedent(original_mlp)), include_attributes=False) == ast.dump(ast.parse(expected), include_attributes=False)
    mlp_proof = proof['MLP_memory_proof']
    assert hashlib.sha256(original_mlp.encode()).hexdigest() == mlp_proof['source_native_MLP_sha256']
    assert sha(package / 'mlp_lifetime.py') == mlp_proof['memory_MLP_source_sha256']
    assert model.config.text_config.hidden_act == 'silu'
    assert not mlp.__code__.co_freevars and not mlp_lifetime.forward.__code__.co_freevars
    assert inspect.signature(mlp) == inspect.signature(mlp_lifetime.forward)
    layers = [v for v in model.modules() if isinstance(v, cls)]
    assert len(layers) == 64
    assert {str(v.gate_proj.weight.device) for v in layers} == {'cuda:' + str(i) for i in range(7)}
    before_mlp = mlp.__code__
    target = root / 'historical-memory-installation'
    target.mkdir(exist_ok=False)
    record = {
        'parent_output': str(parent), 'parent_capacity_files_sha256': paths,
        'source_native_module_sha256': sha(Path(module.__file__)),
        'chunk_patch_sha256': sha(source_path), 'chunk_arithmetic_AST_sha256': proof['arithmetic_AST_sha256'],
        'MLP_patch_sha256': sha(package / 'mlp_lifetime.py'),
        'original_MLP_source_sha256': mlp_proof['source_native_MLP_sha256'],
        'exact_historical_function_code_installed': True,
        'actual_CUDA_inventory_already_audited': sha(root / 'loaded.json'),
        'historical_proof_only': True, 'new_capacity_or_invariance_generate_calls': 0,
        'current_process_full_logit_invariance_tested': False,
        'current_process_capacity_tested': False, 'all_future_histories_fit_proven': False,
        'native_constructor_and_generate_unchanged': True,
        'original_native_source_file_modified': False,
    }
    try:
        raw.__code__ = candidate.__code__
        mlp.__code__ = mlp_lifetime.forward.__code__
        assert raw.__code__ is candidate.__code__ and mlp.__code__ is mlp_lifetime.forward.__code__
        resource(True)
        save(target / 'result.json', record)
        save(target / 'seal.json', {'result.json': sha(target / 'result.json')})
    except BaseException:
        raw.__code__ = before_chunk
        mlp.__code__ = before_mlp
        raise
    return record
