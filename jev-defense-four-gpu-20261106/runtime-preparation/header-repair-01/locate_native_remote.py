"""Preserve first diagnostic failure and locate native module via original env."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

base = Path('/home/researcher/jev-defense-four-gpu-20261106')
attempts = base / 'header-failure-diagnostics'
previous = sorted(attempts.iterdir())[-1]
if not (previous / 'seal.json').exists():
    (previous / 'diagnostic-failure.json').write_text(json.dumps({
        'captured_stderr': 'AssertionError at native source path glob: expected one conventional site-packages source, found another installation layout.',
        'provenance': 'Tool-captured traceback: stdin line68 (prepended source assignment adds one line)',
        'GPU_allocations': 0, 'model_calls': 0, 'GUI_actions': 0}, indent=2))
    (previous / 'seal.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in previous.iterdir() if p.is_file()}, indent=2))
root = attempts / str(time.time_ns())
root.mkdir()
(root / 'source.py').write_text(TASK_SOURCE)
cmd = ['/opt/whz/conda-envs/webmall-vlm/bin/python', '-c',
       'import transformers,json; print(json.dumps({"file":transformers.__file__,"version":transformers.__version__}))']
result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
(root / 'stdout.txt').write_bytes(result.stdout)
(root / 'stderr.txt').write_bytes(result.stderr)
assert result.returncode == 0
location = json.loads(result.stdout)
path = Path(location['file']).parent / 'models/qwen3_5/modeling_qwen3_5.py'
raw = path.read_bytes()
(root / 'actual-modeling_qwen3_5.py').write_bytes(raw)
lines = raw.decode().splitlines()
hits = [{'line': i + 1, 'context': '\n'.join(lines[max(0, i-3):i+8])}
        for i, line in enumerate(lines)
        if 'mtp' in line.lower() or 'class Qwen3_5' in line or '_keys_to_ignore_on_load' in line]
previous_inventory = json.loads((previous / 'tensor-inventory.json').read_bytes())
mtp = [r for r in previous_inventory if r['name'].startswith('mtp.')]
receipt = {'root': str(root), 'previous': str(previous),
    'previous_seal_sha256': hashlib.sha256((previous / 'seal.json').read_bytes()).hexdigest(),
    'transformers': location, 'native_source_path': str(path),
    'native_source_sha256': hashlib.sha256(raw).hexdigest(), 'mtp_tensor_count': len(mtp),
    'mtp_bytes': sum(r['bytes'] for r in mtp), 'mtp': mtp, 'source_hits': hits,
    'GPU_allocations': 0, 'model_calls': 0, 'GUI_actions': 0, 'headers_only': True}
(root / 'receipt.json').write_text(json.dumps(receipt, indent=2))
(root / 'seal.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
    for p in root.iterdir() if p.is_file()}, indent=2))
print(json.dumps(receipt))
