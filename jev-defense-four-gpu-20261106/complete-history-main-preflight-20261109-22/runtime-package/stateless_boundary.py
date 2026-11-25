"""Measured per-invocation auxiliary boundary, without main-model references."""
import gc
import hashlib
import io
import json
from pathlib import Path
import uuid
import weakref

from PIL import Image


def _cache_length(cache):
    if cache is None:
        return 0
    method = getattr(cache, 'get_seq_length', None)
    if not callable(method):
        raise RuntimeError('Unreviewed auxiliary cache type')
    length = int(method())
    if length < 0:
        raise RuntimeError('Invalid auxiliary cache length')
    return length


def _save(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')


class StatelessAuxiliaryBoundary:
    """Surround one native generation and release only its auxiliary state.

    Weights and static tokenizer/grammar vocabulary may remain resident. Receipts
    are retained as immutable experiment evidence, never supplied as conversation.
    Successful calls must release every cache object observed by the hook.
    """

    def __init__(self, model, processor, image_raw, fixed_prompt, target):
        self.model, self.processor = model, processor
        self.expected_image_sha256 = hashlib.sha256(image_raw).hexdigest()
        with Image.open(io.BytesIO(image_raw)) as original:
            self.expected_size = original.size
            self.expected_rgb_sha256 = hashlib.sha256(original.convert('RGB').tobytes()).hexdigest()
        self.fixed_prompt, self.target = fixed_prompt, Path(target)
        self.call_id = uuid.uuid4().hex
        self.template_calls = self.forward_calls = 0
        self.first_cache_length = self.last_cache_length_before_forward = None
        self.cache_refs = {}
        self.untrackable_cache_types = set()

    def __enter__(self):
        for obj, prefix in [(self.model, 'auxiliary'),
                            (getattr(self.model, 'model', None), 'auxiliary.model')]:
            if obj is None:
                continue
            for name in ['_cache', 'past_key_values']:
                if _cache_length(getattr(obj, name, None)):
                    raise RuntimeError('Previous auxiliary context survived: ' + prefix + '.' + name)
            if getattr(obj, 'rope_deltas', None) is not None:
                raise RuntimeError('Previous auxiliary positional state survived: ' + prefix)

        self.original_apply = self.processor.apply_chat_template

        def apply(messages, *args, **kwargs):
            self.template_calls += 1
            if self.template_calls != 1 or len(messages) != 1 or messages[0].get('role') != 'user':
                raise RuntimeError('Auxiliary input is not a new single-user-message invocation')
            blocks = messages[0].get('content')
            if not isinstance(blocks, list) or len(blocks) != 2:
                raise RuntimeError('Auxiliary must receive exactly image plus fixed prompt')
            if [value.get('type') for value in blocks] != ['image', 'text']:
                raise RuntimeError('Unexpected auxiliary input content')
            if blocks[1].get('text') != self.fixed_prompt:
                raise RuntimeError('Task/history/candidate or nonfixed prompt detected')
            if set(blocks[0]) != {'type', 'image'} or set(blocks[1]) != {'type', 'text'}:
                raise RuntimeError('Unexpected auxiliary multimodal input fields')
            actual = blocks[0]['image']
            if not isinstance(actual, Image.Image) or actual.size != self.expected_size:
                raise RuntimeError('Auxiliary does not receive the complete original image')
            if hashlib.sha256(actual.convert('RGB').tobytes()).hexdigest() != self.expected_rgb_sha256:
                raise RuntimeError('Auxiliary image pixels differ from the complete supplied PNG')
            if kwargs.get('tools') is not None:
                raise RuntimeError('Auxiliary tool/history input is not allowed')
            _save(self.target / 'stateless-input-boundary.json', {
                'call_id': self.call_id, 'message_count': 1, 'role': 'user',
                'content_types': ['image', 'text'],
                'complete_image_sha256': self.expected_image_sha256,
                'complete_RGB_sha256': self.expected_rgb_sha256,
                'size': list(self.expected_size),
                'fixed_prompt_sha256': hashlib.sha256(self.fixed_prompt.encode('utf8')).hexdigest(),
                'task_history_candidate_previous_auxiliary_content_supplied': False,
                'actual_first_forward_cache_recorded_separately': True,
            })
            return self.original_apply(messages, *args, **kwargs)

        def forward(_model, _args, kwargs):
            cache = kwargs.get('past_key_values')
            length = _cache_length(cache)
            if self.forward_calls == 0:
                self.first_cache_length = length
                if length != 0:
                    raise RuntimeError('Actual first auxiliary forward has nonempty past state')
            if cache is not None:
                try:
                    self.cache_refs[id(cache)] = weakref.ref(cache)
                except TypeError:
                    self.untrackable_cache_types.add(type(cache).__module__ + '.' + type(cache).__name__)
            self.forward_calls += 1
            self.last_cache_length_before_forward = length

        self.processor.apply_chat_template = apply
        try:
            self.hook = self.model.register_forward_pre_hook(forward, with_kwargs=True)
        except BaseException:
            self.processor.apply_chat_template = self.original_apply
            raise
        return self

    def __exit__(self, error_type, error, traceback):
        self.hook.remove()
        self.processor.apply_chat_template = self.original_apply
        reset = []
        for obj, prefix in [(self.model, 'auxiliary'),
                            (getattr(self.model, 'model', None), 'auxiliary.model')]:
            if obj is None:
                continue
            for name in ['rope_deltas', 'past_key_values', '_cache']:
                if hasattr(obj, name):
                    setattr(obj, name, None)
                    reset.append(prefix + '.' + name)
        gc.collect()
        remaining = sum(reference() is not None for reference in self.cache_refs.values())
        all_released = not remaining and not self.untrackable_cache_types
        _save(self.target / 'stateless-context-discarded.json', {
            'call_id': self.call_id, 'template_calls': self.template_calls,
            'actual_forward_calls': self.forward_calls,
            'actual_first_forward_cache_length': self.first_cache_length,
            'last_within_call_cache_length_before_forward': self.last_cache_length_before_forward,
            'observed_cache_objects': len(self.cache_refs),
            'observed_cache_objects_still_alive': remaining,
            'untrackable_cache_types': sorted(self.untrackable_cache_types),
            'all_observed_cache_objects_released': all_released,
            'known_auxiliary_per_generation_fields_reset_to_none': reset,
            'main_model_or_main_context_referenced': False,
            'weights_unloaded': False, 'raw_experiment_receipts_deleted': False,
            'error_type': None if error_type is None else error_type.__name__,
            'on_error_traceback_may_temporarily_retain_native_locals': error_type is not None,
            'not_a_claim_of_physical_GPU_memory_zeroization': True,
        })
        if error_type is None:
            if self.template_calls != 1 or self.forward_calls < 1 or self.first_cache_length != 0:
                raise RuntimeError('Actual auxiliary call did not pass the stateless boundary')
            if not all_released:
                raise RuntimeError('Auxiliary output returned with unverified surviving cache objects')
        return False
