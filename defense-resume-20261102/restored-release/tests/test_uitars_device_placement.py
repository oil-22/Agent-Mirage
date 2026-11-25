import unittest
from types import SimpleNamespace
from defense.uitars_backend import verified_device_placement


class Model:
    def __init__(self,parameters,buffers=(),mapping=None):
        self.ps=[SimpleNamespace(device=d)for d in parameters]
        self.bs=[SimpleNamespace(device=d)for d in buffers]
        if mapping is not None:self.hf_device_map=mapping
    def parameters(self):return iter(self.ps)
    def buffers(self):return iter(self.bs)


class PlacementTests(unittest.TestCase):
    def test_direct_cuda_load_without_accelerate_metadata(self):
        mapping,devices,source=verified_device_placement(Model(['cuda:0'],['cuda:0']))
        self.assertEqual((mapping,devices,source),({'':'cuda:0'},['cuda:0'],'actual_tensors_direct_load'))
    def test_declared_map_still_checks_actual_buffers(self):
        with self.assertRaises(RuntimeError):verified_device_placement(Model(['cuda:0'],['cpu'],{'':0}))
    def test_declared_cpu_offload_rejected(self):
        with self.assertRaises(RuntimeError):verified_device_placement(Model(['cuda:0'],mapping={'x':'cpu'}))
    def test_declared_disk_offload_rejected(self):
        with self.assertRaises(RuntimeError):verified_device_placement(Model(['cuda:0'],mapping={'x':'disk'}))
    def test_missing_metadata_does_not_hide_cpu_parameters(self):
        with self.assertRaises(RuntimeError):verified_device_placement(Model(['cuda:0','cpu']))
    def test_unmaterialized_meta_tensor_rejected(self):
        with self.assertRaises(RuntimeError):verified_device_placement(Model(['meta']))
    def test_empty_model_rejected(self):
        with self.assertRaises(RuntimeError):verified_device_placement(Model([]))
    def test_declared_cuda_map_preserved(self):
        mapping,devices,source=verified_device_placement(Model(['cuda:0'],mapping={'':0}))
        self.assertEqual((mapping,devices,source),({'':'0'},['cuda:0'],'hf_device_map_and_actual_tensors'))


if __name__=='__main__':unittest.main()
