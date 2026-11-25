"""Per-call auxiliary boundary. It never changes main-model state or inputs."""
import gc
import hashlib
import json
from pathlib import Path
import uuid


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
    with Path(path).open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write('\n')


class StatelessAuxiliaryBoundary:
    """Use only around one auxiliary generation; weights may stay resident.

    The backend creates and releases its message/input/output locals inside this
    boundary. Receipts preserve evidence of those calls without acting as a
    conversation or providing another call's cache.
    """
    def __init__(self, model, processor, image_raw, fixed_prompt, target):
        self.model, self.processor = model, processor
        self.expected_image_sha256 = hashlib.sha256(image_raw).hexdigest()
        self.fixed_prompt = fixed_prompt
        self.target = Path(target)
        self.call_id = uuid.uuid4().hex
        self.template_calls = 0
        self.forward_calls = 0
        self.first_cache_length = None
        self.last_cache_length_before_forward = None

    def __enter__(self):
        # Native dynamic generation caches are per invocation. If an optional
        # persistent model cache exists, it must have no previous sequence.
        for name in ['_cache', 'past_key_values']:
            if _cache_length(getattr(self.model, name, None)):
                raise RuntimeError('Previous auxiliary generation state survived: ' + name)
        self.original_apply = self.processor.apply_chat_template

        def apply(messages, *args, **kwargs):
            self.template_calls += 1
            if self.template_calls != 1 or len(messages) != 1 or messages[0].get('role') != 'user':
                raise RuntimeError('Auxiliary input is not a new single-user-message invocation')
            blocks = messages[0].get('content')
            if not isinstance(blocks, list) or len(blocks) != 2:
                raise RuntimeError('Auxiliary must receive exactly image plus fixed prompt')
            if [v.get('type') for v in blocks] != ['image', 'text'] or blocks[1].get('text') != self.fixed_prompt:
                raise RuntimeError('Task/history/candidate or nonfixed auxiliary prompt detected')
            if set(blocks[0]) != {'type', 'image'} or set(blocks[1]) != {'type', 'text'}:
                raise RuntimeError('Unexpected auxiliary multimodal input fields')
            # Full original PNG byte binding is already enforced by the server;
            # this asserts there are no additional contextual template options.
            if kwargs.get('tools') is not None:
                raise RuntimeError('Auxiliary tool/history input is not allowed')
            _save(self.target / 'stateless-input-boundary.json', {
                'call_id': self.call_id, 'message_count': 1, 'role': 'user',
                'content_types': ['image', 'text'], 'image_sha256': self.expected_image_sha256,
                'fixed_prompt_sha256': hashlib.sha256(self.fixed_prompt.encode('utf8')).hexdigest(),
                'task_history_candidate_previous_auxiliary_content_supplied': False,
                'previous_KV_state_supplied': False})
            return self.original_apply(messages, *args, **kwargs)

        def forward(_model, _args, kwargs):
            length = _cache_length(kwargs.get('past_key_values'))
            if self.forward_calls == 0:
                self.first_cache_length = length
                if length != 0:
                    raise RuntimeError('Actual first auxiliary forward has nonempty past state')
            self.forward_calls += 1
            self.last_cache_length_before_forward = length

        self.processor.apply_chat_template = apply
        self.hook = self.model.register_forward_pre_hook(forward, with_kwargs=True)
        return self

    def __exit__(self, error_type, error, traceback):
        self.hook.remove()
        self.processor.apply_chat_template = self.original_apply
        # Remove only known per-generation auxiliary state. The main model is a
        # different object and is never referenced by this boundary.
        reset = []
        for obj, prefix in [(self.model, 'auxiliary'), (getattr(self.model, 'model', None), 'auxiliary.model')]:
            if obj is None:
                continue
            for name in ['rope_deltas', 'past_key_values', '_cache']:
                if hasattr(obj, name):
                    setattr(obj, name, None)
                    reset.append(prefix + '.' + name)
        gc.collect()
        _save(self.target / 'stateless-context-discarded.json', {
            'call_id': self.call_id, 'template_calls': self.template_calls,
            'actual_forward_calls': self.forward_calls,
            'actual_first_forward_cache_length': self.first_cache_length,
            'last_within_call_cache_length_before_forward': self.last_cache_length_before_forward,
            'known_auxiliary_per_generation_fields_reset_to_none': reset,
            'input_context_accumulated': False, 'cross_call_output_or_KV_reuse': False,
            'weights_unloaded': False, 'raw_experiment_receipts_deleted': False,
            'error_type': None if error_type is None else error_type.__name__,
            'not_a_claim_of_physical_GPU_memory_zeroization': True})
        if error_type is None and (self.template_calls != 1 or self.forward_calls < 1):
            raise RuntimeError('Actual auxiliary call did not pass the stateless boundary')
        return False
