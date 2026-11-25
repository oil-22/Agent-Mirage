"""Sequential GPU inference with idle weights in RAM; no CPU forward allowed."""
import gc
import time
from model_runtime import save


class ResidentSchedule:
    def __init__(self, runtime, root, journal, resource):
        self.runtime, self.root, self.journal, self.resource = runtime, root, journal, resource
        self.torch, self.save = runtime['torch'], save
        self.primary = runtime['engine'].model
        self.auxiliary = runtime['auxiliary_model']
        self.groups = [name for name, device in runtime['device_map'].items() if device == 3]
        assert self.groups and len(self.groups) == 15
        self.phase, self.transitions = 'primary', []
        self.primary_calls = self.auxiliary_calls = 0
        self.primary_hook = self.primary.register_forward_pre_hook(self.primary_guard, with_kwargs=True)
        self.auxiliary_hook = self.auxiliary.register_forward_pre_hook(self.auxiliary_guard, with_kwargs=True)
        self.assert_primary_resident()

    def primary_guard(self, model, args, kwargs):
        assert self.phase == 'primary', 'CPU primary inference is forbidden'
        assert all(t.device.type == 'cuda' for t in model.parameters())
        self.primary_calls += 1

    def auxiliary_guard(self, model, args, kwargs):
        assert self.phase == 'auxiliary', 'CPU auxiliary inference is forbidden'
        assert all(t.device == self.torch.device('cuda:3') for t in model.parameters())
        self.auxiliary_calls += 1

    def assert_primary_resident(self):
        assert all(t.device.type == 'cpu' for t in self.auxiliary.parameters())
        for name, tensor in self.primary.named_parameters():
            keys = [k for k in self.runtime['device_map'] if name == k or name.startswith(k + '.')]
            assert keys, name
            expected = self.runtime['device_map'][max(keys, key=len)]
            assert tensor.device == self.torch.device('cuda:' + str(expected)), name
            if tensor.is_floating_point():
                assert tensor.dtype == self.torch.bfloat16

    def move_group(self, module, device):
        metadata = [(n, tuple(t.shape), str(t.dtype), t.numel() * t.element_size())
                    for n, t in list(module.named_parameters()) + list(module.named_buffers())]
        module.to(device=device)
        after = [(n, tuple(t.shape), str(t.dtype), t.numel() * t.element_size())
                 for n, t in list(module.named_parameters()) + list(module.named_buffers())]
        assert metadata == after, 'Residency transfer altered native tensor metadata'
        assert all(t.device == self.torch.device(device) for t in module.parameters())

    def to_auxiliary(self):
        assert self.phase == 'primary'
        self.resource()
        started = time.perf_counter()
        self.torch.cuda.synchronize()
        for name in self.groups:
            self.move_group(self.primary.get_submodule(name), 'cpu')
        gc.collect()
        self.torch.cuda.empty_cache()
        self.move_group(self.auxiliary, 'cuda:3')
        self.torch.cuda.synchronize()
        self.phase = 'auxiliary'
        proof = self.runtime['support'].audit_tensors(self.torch, [('single_auxiliary', self.auxiliary)], ['cuda:3'])
        self.record('to_auxiliary', started, proof)

    def to_primary(self):
        assert self.phase == 'auxiliary'
        self.resource()
        started = time.perf_counter()
        self.torch.cuda.synchronize()
        self.move_group(self.auxiliary, 'cpu')
        gc.collect()
        self.torch.cuda.empty_cache()
        for name in self.groups:
            self.move_group(self.primary.get_submodule(name), 'cuda:3')
        self.torch.cuda.synchronize()
        self.phase = 'primary'
        self.assert_primary_resident()
        proof = self.runtime['support'].audit_tensors(self.torch, [('primary', self.primary)],
                                                    ['cuda:0', 'cuda:1', 'cuda:2', 'cuda:3'])
        self.record('to_primary', started, proof)

    def record(self, kind, started, proof):
        row = {'kind': kind, 'seconds': time.perf_counter() - started,
               'actual_CUDA_tensors': proof, 'memory': self.runtime['support'].memory(self.torch),
               'primary_forward_calls': self.primary_calls, 'auxiliary_forward_calls': self.auxiliary_calls,
               'all_actual_model_forwards_GPU_only': True, 'precision_unchanged': 'bfloat16',
               'transferred_primary_groups': self.groups, 'CPU_storage_only_no_CPU_inference': True}
        self.transitions.append(row)
        self.save(self.root / ('residency-transition-%02d.json' % len(self.transitions)), row)
        self.journal.append('GPU_weight_residency_transition', row)

