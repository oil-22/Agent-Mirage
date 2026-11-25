"""Move idle BF16 groups through RAM during an unchanged native prefill.

The native model/attention/generation functions, inputs, KV cache and outputs
are untouched. Each group's forward stays on its original execution device.
After prefill, all groups are restored for ordinary GPU-resident decoding.
"""
import time


class PrefillResidency:
    def __init__(self, runtime, resident, root, journal, resource):
        self.runtime, self.resident = runtime, resident
        self.model, self.torch = resident.primary, runtime['torch']
        self.root, self.journal, self.resource = root, journal, resource
        self.save = resident.save
        self.active = False
        self.failed = False
        self.current_group = None
        self.session = 0
        self.records = []
        self.groups = dict(runtime['device_map'])
        self.modules = {name:self.model.get_submodule(name) for name in self.groups}
        assert len(self.groups) == 69
        assert self.model.config.tie_word_embeddings is False
        # This mover requires disjoint groups and unchanged resident hooks.
        names = list(self.groups)
        assert not any(a != b and a.startswith(b + '.') for a in names for b in names)
        owners = {}
        for name, module in self.modules.items():
            for tensor in module.parameters():
                key = (tensor.device, tensor.data_ptr())
                assert key not in owners, 'Tied storage across residency groups is unsupported'
                owners[key] = name
            for child in module.modules():
                hook = getattr(child, '_hf_hook', None)
                if hook is not None:
                    assert not getattr(hook, 'offload', False), 'Nested offload hooks are unsupported'
        self.handles = []
        for name, module in self.modules.items():
            self.handles.append(module.register_forward_pre_hook(self.group_pre(name), with_kwargs=True))
            self.handles.append(module.register_forward_hook(self.group_post(name), with_kwargs=True, always_call=True))
        # ResidentSchedule's full CUDA guard runs before this hook. Its
        # next decode guard again sees the original full CUDA placement.
        self.handles.append(self.model.register_forward_pre_hook(self.start, with_kwargs=True))
        self.handles.append(self.model.register_forward_hook(self.finish, with_kwargs=True, always_call=True))

    @staticmethod
    def metadata(module):
        return [(kind, name, tuple(tensor.shape), str(tensor.dtype))
                for kind, rows in [('parameter', module.named_parameters()), ('buffer', module.named_buffers())]
                for name, tensor in rows]

    def move(self, name, device):
        module = self.modules[name]
        before = self.metadata(module)
        started = time.perf_counter()
        module.to(device=device)
        assert before == self.metadata(module), 'Weight residency altered shape or dtype'
        assert all(tensor.device == self.torch.device(device) for tensor in module.parameters())
        assert all(tensor.device == self.torch.device(device) for tensor in module.buffers())
        self.records.append({'group':name, 'device':device, 'seconds':time.perf_counter()-started})

    def empty_cache(self):
        for device in range(4):
            with self.torch.cuda.device(device):
                self.torch.cuda.empty_cache()

    def start(self, module, args, kwargs):
        assert not args and not self.active and not self.failed
        assert self.resident.phase == 'primary'
        ids = kwargs.get('input_ids')
        assert ids is not None and ids.ndim == 2 and ids.shape[0] == 1
        if ids.shape[1] == 1:
            return
        cache = kwargs.get('past_key_values')
        assert cache is None or cache.get_seq_length() == 0, 'Only a fresh complete prefill is supported'
        self.resource()
        self.resident.assert_primary_resident()
        self.session += 1
        self.records = []
        self.started = time.perf_counter()
        self.tokens = int(ids.shape[1])
        self.active = True
        self.visited = []
        # Parameters are stored without quantization/casting; no CPU forward
        # is permitted. Existing Accelerate alignment retains device routing.
        for name in self.groups:
            self.move(name, 'cpu')
        self.empty_cache()
        self.journal.append('native_prefill_idle_weights_stored_in_RAM', {
            'session':self.session, 'input_tokens':self.tokens,
            'original_execution_devices_unchanged':True,
            'native_forward_source_inputs_and_KV_not_modified':True,
            'CPU_forward_forbidden':True})

    def group_pre(self, name):
        def hook(module, args, kwargs):
            if self.active:
                assert self.current_group is None
                self.current_group = name
                self.move(name, 'cuda:' + str(self.groups[name]))
                self.visited.append(name)
            expected = self.torch.device('cuda:' + str(self.groups[name]))
            assert all(t.device == expected for t in module.parameters()), 'Non-native execution device'
            assert all(t.device == expected for t in module.buffers()), 'Non-native buffer device'
            assert all(t.dtype == self.torch.bfloat16 for t in module.parameters() if t.is_floating_point())
        return hook

    def group_post(self, name):
        def hook(module, args, kwargs, output):
            if not self.active:
                return
            assert self.current_group == name
            self.move(name, 'cpu')
            with self.torch.cuda.device(self.groups[name]):
                self.torch.cuda.empty_cache()
            self.current_group = None
        return hook

    def finish(self, module, args, kwargs, output):
        if not self.active:
            return
        assert self.current_group is None
        row = {'session':self.session, 'input_tokens':self.tokens, 'visited_groups':self.visited,
               'same_native_execution_device_map':self.groups,
               'all_group_forward_parameters_BF16_on_original_GPU':True,
               'native_attention_generation_inputs_outputs_and_cache_unmodified':True,
               'all_transfer_seconds':sum(r['seconds'] for r in self.records),
               'partial_prefill_seconds':time.perf_counter()-self.started}
        if output is None:
            self.failed = True
            row.update(success=False, full_GPU_restore_attempted_after_failure=False)
        else:
            # Native prefill temporaries have gone out of scope. Keep the
            # original returned output/KV on GPU and restore only weights.
            self.empty_cache()
            for name, device in self.groups.items():
                self.move(name, 'cuda:' + str(device))
            self.resident.assert_primary_resident()
            row.update(success=True, full_GPU_resident_before_decode=True,
                       seconds_including_restore=time.perf_counter()-self.started,
                       all_transfer_seconds=sum(r['seconds'] for r in self.records),
                       memory_after_restore=self.runtime['support'].memory(self.torch))
        row['moves'] = self.records
        self.active = False
        self.save(self.root / ('prefill-residency-%03d.json' % self.session), row)
        self.journal.append('native_prefill_residency_completed' if output is not None else
                            'native_prefill_residency_failed_no_retry', row)

    def close(self):
        assert not self.active
        for handle in self.handles:
            handle.remove()
        self.handles.clear()
