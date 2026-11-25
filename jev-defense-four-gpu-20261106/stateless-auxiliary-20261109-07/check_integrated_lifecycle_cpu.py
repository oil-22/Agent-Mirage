"""Exercise the complete new auxiliary helper with native tokenizer/cache on CPU.

The model/processor forward is a protocol mock. No weights, CUDA, inference,
GUI, or semantic result is produced by these controls.
"""
import argparse
from contextlib import contextmanager
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def main(args):
    package, root = args.package.resolve(), args.output.resolve()
    root.mkdir(exist_ok=False)
    sys.path[:0] = [str(package), str(package / 'release')]
    identity = json.loads((package / 'auxiliary-grammar-identity.json').read_bytes())
    sys.path.insert(0, str(Path(identity['canonical_primary_package']).parent))
    import lmformatenforcer
    primary_before = {key: value for key, value in sys.modules.items()
                      if key == 'lmformatenforcer' or key.startswith('lmformatenforcer.')}
    import torch
    from transformers import AutoConfig, AutoTokenizer
    from transformers.cache_utils import DynamicCache
    import aux_identity_support
    import bounded_auxiliary
    from model_runtime import save
    from PIL import Image
    assert not torch.cuda.is_initialized()
    tokenizer = AutoTokenizer.from_pretrained(aux_identity_support.MODEL_PATH,
                                               local_files_only=True, trust_remote_code=False)
    config = AutoConfig.from_pretrained(aux_identity_support.MODEL_PATH,
                                       local_files_only=True, trust_remote_code=False).text_config
    full_layer = next(i for i, kind in enumerate(config.layer_types) if kind == 'full_attention')
    generation = SimpleNamespace(eos_token_id=[248044, 248046], max_new_tokens=2048)
    data = bounded_auxiliary.prepare(SimpleNamespace(tokenizer=tokenizer), generation, root, package)
    text = json.dumps({'schema_version': 'image-evidence-v2-compact',
                       'coordinate_space': 'normalized_1000',
                       'frame': {'kind': 'gui', 'summary': 'CPU protocol mock only', 'limitations': []},
                       'text_spans': [], 'elements': [], 'uncertain_regions': []}, separators=(',', ':'))
    output_ids = tokenizer.encode(text, add_special_tokens=False) + [generation.eos_token_id[0]]

    class Tensor:
        def __init__(self, value):
            self.value = value
        def __getitem__(self, index):
            return Tensor(self.value[index])
        def tolist(self):
            return self.value
        def detach(self):
            return self
        def cpu(self):
            return self

    class Batch(dict):
        def to(self, name):
            assert name == 'cuda:3'
            # Deliberately a mock; never transfer or allocate a GPU tensor.
            return self

    class Handle:
        def __init__(self, model, hook):
            self.model, self.hook = model, hook
        def remove(self):
            self.model.hooks.remove(self.hook)

    class Processor:
        def __init__(self):
            self.tokenizer = tokenizer
        def apply_chat_template(self, messages, **kwargs):
            return Batch(input_ids=Tensor([[10, 20, 30]]))

    class Model:
        def __init__(self):
            self.hooks = []
            self.model = SimpleNamespace(rope_deltas=None)
            self._cache = None
            self.generate_calls = 0
            self.fail_this_call = False
        def register_forward_pre_hook(self, hook, with_kwargs):
            assert with_kwargs
            self.hooks.append(hook)
            return Handle(self, hook)
        def generate(self, input_ids, generation_config, prefix_allowed_tokens_fn, **kwargs):
            self.generate_calls += 1
            cache = DynamicCache(config=config)
            assert cache.get_seq_length() == 0
            prompt = input_ids[0].tolist()
            values = []
            for index, token in enumerate(output_ids):
                for hook in tuple(self.hooks):
                    hook(self, (), {'past_key_values': cache})
                self.model.rope_deltas = torch.zeros((1, 1), dtype=torch.int64)
                key = torch.zeros((1, config.num_key_value_heads, 1, config.head_dim))
                cache.update(key, key.clone(), full_layer)
                if self.fail_this_call:
                    raise RuntimeError('Injected CPU protocol failure after first cache update')
                allowed = prefix_allowed_tokens_fn(0, Tensor(prompt + values))
                assert token in allowed, ('native CPU control token rejected', index, token)
                values.append(token)
            return SimpleNamespace(sequences=Tensor([prompt + values]), past_key_values=cache)

    @contextmanager
    def audit(model, processor, target):
        original_generate = model.generate
        def generate(**kwargs):
            result = original_generate(**kwargs)
            save(target / 'actual-generation.json', {
                'CPU_protocol_mock_not_model_generation': True,
                'input_tokens': 3, 'output_ids': output_ids,
                'output_tokens': len(output_ids), 'natural_EOS': True})
            return result
        model.generate = generate
        try:
            yield
        finally:
            model.generate = original_generate

    source = args.images.resolve()
    image_paths = [source / 'catalog.png', source / 'catalog.png',
                   source / 'footer.png', source / 'form.png']
    model, processor = Model(), Processor()
    receipts, ids = [], []
    for index, image_path in enumerate(image_paths):
        target = root / ('case-%02d' % (index + 1))
        target.mkdir()
        model.fail_this_call = index == 2
        try:
            result = bounded_auxiliary.generate(model, processor, generation, torch,
                                                 audit, data, image_path.read_bytes(), target)
            assert not model.fail_this_call
            assert result[0] == text and result[2] is True
        except RuntimeError as error:
            assert model.fail_this_call and 'Injected CPU protocol failure' in str(error)
            save(target / 'expected-injected-failure.json', {'error': str(error), 'no_retry': True})
        assert not model.hooks and model.model.rope_deltas is None and model._cache is None
        receipt = json.loads((target / 'stateless-context-discarded.json').read_bytes())
        assert receipt['actual_first_forward_cache_length'] == 0
        if not model.fail_this_call:
            assert receipt['all_observed_cache_objects_released']
            assert receipt['observed_cache_objects'] >= 1
        ids.append(receipt['call_id'])
        receipts.append(receipt)
        gc.collect()
    assert len(set(ids)) == 4 and model.generate_calls == 4
    primary_after = {key: value for key, value in sys.modules.items()
                     if key == 'lmformatenforcer' or key.startswith('lmformatenforcer.')}
    assert primary_before == primary_after
    assert not torch.cuda.is_initialized()
    result = {
        'passed': True, 'time': time.time(),
        'test_kind': 'complete integrated helper, real native tokenizer and DynamicCache, CPU forward protocol mock',
        'protocol_mock_invocations': 4, 'successful_mock_calls': 3,
        'same_image_requests_generate_separately': True,
        'injected_failure_followed_by_new_independent_successful_call': True,
        'three_successful_calls_release_all_observed_native_cache_objects': True,
        'first_forward_cache_lengths': [r['actual_first_forward_cache_length'] for r in receipts],
        'native_hybrid_cache_first_full_attention_layer': full_layer,
        'canonical_main_grammar_module_objects_unchanged': True,
        'actual_GPU_context_discard_and_semantic_behavior_not_proven': True,
        'weights_loaded': False, 'CUDA_initialized': False,
        'new_actual_model_GUI_scorer_paid_calls': 0,
    }
    save(root / 'receipt.json', result)
    save(root / 'seal.json', {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in root.rglob('*') if p.is_file()})
    print(json.dumps({'root': str(root), 'passed': True,
                      'protocol_mock_calls': 4, 'actual_model_GUI_calls': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--images', type=Path, required=True)
    main(parser.parse_args())
