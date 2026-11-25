"""Repair only CPU placement accounting using sealed header+meta inventories.

No model import, tensor payload read or old output mutation. The exact 15 native
unused MTP tensors are reported separately; any other unmapped tensor fails.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from four_gpu_contract import primary_device_map, validate_layout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed(root):
    for name, expected in json.loads((root / 'seal.json').read_bytes()).items():
        if sha(root / name) != expected:
            raise RuntimeError('Source receipt seal mismatch: ' + str(root / name))


def main(a):
    sealed(a.header_inventory_root)
    sealed(a.meta_root)
    meta = json.loads((a.meta_root / 'receipt.json').read_bytes())
    states = {r['name']: r for r in json.loads((a.meta_root / 'meta-state.json').read_bytes())}
    if (meta['class'] != 'Qwen3_5ForConditionalGeneration' or not meta['all_state_tensors_meta'] or
            meta['cuda_initialized'] is not False or meta['missing_checkpoint_tensors'] != [] or
            meta['native_ignored_unexpected_patterns'] != ['^mtp.*']):
        raise RuntimeError('Native meta proof does not bind the original architecture/unused MTP')
    if sha(Path(meta['native_source'])) != meta['native_source_sha256']:
        raise RuntimeError('Actual native implementation differs from sealed meta proof')
    index_path = a.model / 'model.safetensors.index.json'
    expected = json.loads(a.expected_runtime.read_bytes())
    if sha(index_path) != expected['metadata_sha256']['model.safetensors.index.json']:
        raise RuntimeError('Original checkpoint index differs')
    if sha(index_path) != sha(a.header_inventory_root / 'model-index.json'):
        raise RuntimeError('Header inventory binds a different checkpoint index')
    layout = json.loads(a.layout.read_bytes()); validate_layout(layout)
    mapping = primary_device_map()
    tensors = json.loads((a.header_inventory_root / 'tensor-inventory.json').read_bytes())
    inventory = {row['name']: row for row in tensors}
    if len(inventory) != len(tensors) or set(inventory) != set(json.loads(index_path.read_bytes())['weight_map']):
        raise RuntimeError('Header inventory does not exactly cover the checkpoint')
    ignored = set(meta['checkpoint_only_native_ignored_tensors'])
    if (len(ignored) != 15 or any(not name.startswith('mtp.') for name in ignored) or
            set(inventory) - set(states) != ignored or set(states) - set(inventory)):
        raise RuntimeError('Only the exact native non-instantiated MTP set may be separated')
    totals = {i: 0 for i in range(4)}
    for name, value in inventory.items():
        if value['dtype'] != 'BF16': raise RuntimeError('Checkpoint native dtype changed')
        if name in ignored: continue
        state = states[name]
        if state['shape'] != value['shape'] or state['bytes'] != value['bytes']:
            raise RuntimeError('Actual native state layout and checkpoint header differ: ' + name)
        prefixes = [prefix for prefix in mapping if name == prefix or name.startswith(prefix + '.')]
        if not prefixes: raise RuntimeError('Unmapped actual native tensor: ' + name)
        totals[mapping[max(prefixes, key=len)]] += value['bytes']
    headers = json.loads((a.header_inventory_root / 'headers.json').read_bytes())
    for row in headers:
        stamp = (a.model / row['file']).stat()
        if (stamp.st_size, stamp.st_mtime_ns) != (row['bytes'], row['mtime_ns']):
            raise RuntimeError('Checkpoint shard changed after header inventory')
    root = a.output_root / str(time.time_ns()); root.mkdir(parents=True, exist_ok=False)
    report = {'scope': 'native meta-bound CPU parameter placement lower bound; not GPU capacity',
        'header_inventory_root': str(a.header_inventory_root),
        'header_inventory_seal_sha256': sha(a.header_inventory_root / 'seal.json'),
        'meta_root': str(a.meta_root), 'meta_receipt_sha256': sha(a.meta_root / 'receipt.json'),
        'native_source': meta['native_source'], 'native_source_sha256': meta['native_source_sha256'],
        'model': str(a.model), 'original_index_sha256': sha(index_path),
        'contract_source_sha256': sha(Path(__file__).resolve().parent.parent / 'four_gpu_contract.py'),
        'layout_sha256': sha(a.layout), 'mapped_native_tensor_count': len(states),
        'mapped_native_parameter_bytes': sum(totals.values()),
        'checkpoint_unused_native_MTP': [inventory[name] for name in sorted(ignored)],
        'checkpoint_unused_native_MTP_bytes': sum(inventory[name]['bytes'] for name in ignored),
        'planned_parameter_bytes_by_logical_device': totals,
        'planned_parameter_GiB_by_logical_device': {i: size / 1024**3 for i, size in totals.items()},
        'physical_mapping': [4, 5, 6, 7],
        'within_proposed_parameter_budgets': all(value <= layout['primary_max_memory_gib'][i] * 1024**3
                                               for i, value in totals.items()),
        'full_weight_bytes_read': False, 'full_weight_hashes_repeated': False,
        'header_bytes_reread': False, 'shards_fresh_stat_bound': True,
        'GPU_allocations': 0, 'model_calls': 0, 'GUI_actions': 0}
    (root / 'receipt.json').write_text(json.dumps(report, indent=2))
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    (root / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in root.iterdir() if p.is_file()}, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'checkpoint_unused_native_MTP'} | {'root': str(root)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--expected-runtime', type=Path, required=True)
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--header-inventory-root', type=Path, required=True)
    parser.add_argument('--meta-root', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    main(parser.parse_args())
