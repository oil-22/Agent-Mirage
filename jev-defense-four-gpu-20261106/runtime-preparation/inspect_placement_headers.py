"""Read safetensors headers only; never reads full weights or imports torch."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import time

from four_gpu_contract import primary_device_map, validate_layout


def main(a):
    index_path = a.model / 'model.safetensors.index.json'
    expected = json.loads(a.expected_runtime.read_bytes())
    if hashlib.sha256(index_path.read_bytes()).hexdigest() != expected['metadata_sha256']['model.safetensors.index.json']:
        raise RuntimeError('Original weight index identity differs')
    index = json.loads(index_path.read_bytes())
    mapping = primary_device_map()
    layout = json.loads(a.layout.read_bytes())
    validate_layout(layout)
    records = []
    totals = {i: 0 for i in range(4)}
    found = set()
    for name in sorted(set(index['weight_map'].values())):
        path = a.model / name
        before = path.stat()
        with path.open('rb') as handle:
            length = struct.unpack('<Q', handle.read(8))[0]
            if not 0 < length <= 64 * 1024 ** 2:
                raise RuntimeError('Unexpected safetensors metadata size')
            raw = handle.read(length)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError('Weight shard changed during header inspection')
        header = json.loads(raw)
        for tensor_name, value in header.items():
            if tensor_name == '__metadata__':
                continue
            if index['weight_map'].get(tensor_name) != name:
                raise RuntimeError('Shard tensor and original index disagree')
            prefixes = [prefix for prefix in mapping if tensor_name == prefix or tensor_name.startswith(prefix + '.')]
            if not prefixes:
                raise RuntimeError('Tensor is unassigned: ' + tensor_name)
            prefix = max(prefixes, key=len)
            size = value['data_offsets'][1] - value['data_offsets'][0]
            if value['dtype'] != 'BF16':
                raise RuntimeError('Original weight dtype is not BF16')
            totals[mapping[prefix]] += size
            found.add(tensor_name)
        records.append({'file': name, 'bytes': before.st_size, 'mtime_ns': before.st_mtime_ns,
                        'header_bytes_read': len(raw), 'header_sha256': hashlib.sha256(raw).hexdigest()})
    if found != set(index['weight_map']):
        raise RuntimeError('Header inspection did not cover all index tensors')
    report = {'scope': 'CPU parameter-placement lower bound only; not GPU or complete weight identity',
              'time': time.time(), 'model': str(a.model), 'mapped_tensor_count': len(found),
              'planned_parameter_bytes_by_logical_device': totals,
              'planned_parameter_GiB_by_logical_device': {i: size / 1024 ** 3 for i, size in totals.items()},
              'physical_mapping': [4, 5, 6, 7],
              'within_proposed_parameter_budgets': all(size <= layout['primary_max_memory_gib'][i] * 1024 ** 3
                                                       for i, size in totals.items()),
              'shards': records, 'full_weight_bytes_read': False, 'full_weight_hashes_repeated': False,
              'GPU_allocations': 0, 'model_calls': 0, 'GUI_actions': 0}
    with a.output.open('x', encoding='utf8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != 'shards'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--expected-runtime', type=Path, required=True)
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args())
