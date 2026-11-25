"""Preserve failed CPU header check; inspect all headers and native MTP source.

Run via stdin only; the local sender prepends TASK_SOURCE with these exact bytes.
No torch/model imports or weight tensor payload reads.
"""
import hashlib
import json
from pathlib import Path
import struct
import time

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
MODEL = Path('/data/llms/Qwen3.8-27B')
root = BASE / 'header-failure-diagnostics' / str(time.time_ns())
root.mkdir(parents=True, exist_ok=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2))


(root / 'diagnostic-source.py').write_text(TASK_SOURCE)
for name, path in [('failed-header-source.py', BASE / 'runtime-preparation/inspect_placement_headers.py'),
                   ('failed-contract-source.py', BASE / 'runtime-preparation/four_gpu_contract.py'),
                   ('failed-layout.json', BASE / 'runtime-preparation/layout.proposed.json'),
                   ('original-runtime.json', BASE / 'original-runtime.json'),
                   ('model-index.json', MODEL / 'model.safetensors.index.json'),
                   ('model-config.json', MODEL / 'config.json')]:
    (root / name).write_bytes(path.read_bytes())
save('failure.json', {'status': 'failed_CPU_header_inspection', 'returncode': 1,
    'command': '/opt/whz/conda-envs/webmall-vlm/bin/python ' + str(BASE / 'runtime-preparation/inspect_placement_headers.py') +
       ' --model /data/llms/Qwen3.8-27B --expected-runtime ' + str(BASE / 'original-runtime.json') +
       ' --layout ' + str(BASE / 'runtime-preparation/layout.proposed.json') +
       ' --output ' + str(BASE / 'placement-header-20261106-01.json'),
    'captured_stderr': "Traceback: inspect_placement_headers.py line74 main -> line43: RuntimeError: Tensor is unassigned: mtp.fc.weight",
    'stderr_provenance': 'Root reported tool-captured stderr; original remote command did not persist stdout/stderr files before failing.',
    'original_output_file_exists': (BASE / 'placement-header-20261106-01.json').exists(),
    'GPU_allocations': 0, 'model_calls': 0, 'GUI_actions': 0})
index = json.loads((MODEL / 'model.safetensors.index.json').read_bytes())
headers = []
tensors = []
for shard in sorted(set(index['weight_map'].values())):
    path = MODEL / shard
    before = path.stat()
    with path.open('rb') as handle:
        length = struct.unpack('<Q', handle.read(8))[0]
        assert 0 < length <= 64 * 1024**2
        raw = handle.read(length)
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    header = json.loads(raw)
    headers.append({'file': shard, 'bytes': before.st_size, 'mtime_ns': before.st_mtime_ns,
                    'header_bytes_read': len(raw), 'header_sha256': sha(raw)})
    for name, value in header.items():
        if name == '__metadata__': continue
        assert index['weight_map'].get(name) == shard
        tensors.append({'name': name, 'shard': shard, 'dtype': value['dtype'],
            'shape': value['shape'], 'bytes': value['data_offsets'][1] - value['data_offsets'][0]})
save('headers.json', headers)
save('tensor-inventory.json', tensors)
mtp = [r for r in tensors if r['name'].startswith('mtp.')]
sources = list(Path('/opt/whz/conda-envs/webmall-vlm/lib').glob('python*/site-packages/transformers/models/qwen3_5/modeling_qwen3_5.py'))
assert len(sources) == 1
source = sources[0]
raw = source.read_bytes()
(root / 'actual-modeling_qwen3_5.py').write_bytes(raw)
lines = raw.decode().splitlines()
hits = []
for i, line in enumerate(lines):
    if 'mtp' in line.lower() or 'class Qwen3_5' in line or '_keys_to_ignore_on_load' in line:
        hits.append({'line': i + 1, 'context': '\n'.join(lines[max(0, i-2):i+5])})
save('native-source-hits.json', {'path': str(source), 'sha256': sha(raw), 'hits': hits})
report = {'root': str(root), 'status': 'diagnostic_complete', 'tensor_count': len(tensors),
    'index_tensor_count': len(index['weight_map']), 'mtp_tensor_count': len(mtp),
    'mtp_bytes': sum(r['bytes'] for r in mtp), 'mtp': mtp,
    'native_source_path': str(source), 'native_source_sha256': sha(raw), 'source_hits': hits,
    'header_only': True, 'full_weight_hashes_repeated': False,
    'GPU_allocations': 0, 'model_calls': 0, 'GUI_actions': 0}
save('receipt.json', report)
save('seal.json', {p.name: sha(p.read_bytes()) for p in root.iterdir() if p.is_file()})
print(json.dumps(report))
