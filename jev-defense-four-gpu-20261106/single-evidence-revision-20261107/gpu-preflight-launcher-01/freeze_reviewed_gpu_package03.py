"""Root-authorized local freeze only. No stage, holder submission or GPU actions."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVISION = HERE.parent
FINAL_WORKER = 'a451142e4233913cc1fca4c86421b9feeb3655c5ad3eed6643e010b35db9fbfb'
worker = REVISION / 'native_image_gpu_preflight.py'
assert hashlib.sha256(worker.read_bytes()).hexdigest() == FINAL_WORKER, 'Wait for final root-reviewed worker SHA'
value = json.loads((HERE / 'builder-inputs-linked02.pending.json').read_bytes())
value.update({'root_execution_review': True, 'final_worker_source_sha256': FINAL_WORKER,
              'lease_sha256': hashlib.sha256((REVISION.parent / 'resource-attempt-20261106-01/lease.json').read_bytes()).hexdigest(),
              'launcher_output_root': '/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-four-first-attempts-01'})
inputs = HERE / 'builder-inputs-linked02.reviewed.json'
with inputs.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(value, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
invocation = HERE / 'freeze-invocation-linked03'
invocation.mkdir(exist_ok=False)
output = HERE / 'frozen-gpu-four-linked02-01'
argv = [sys.executable, '-B', str(HERE / 'build_gpu_manifest_linked02.py'), '--inputs', str(inputs), '--output', str(output)]
started = time.time()
result = subprocess.run(argv, cwd=str(HERE), capture_output=True)
for name, raw in [('stdout.log', result.stdout), ('stderr.log', result.stderr)]:
    with (invocation / name).open('xb') as stream:
        stream.write(raw)
receipt = {'argv': argv, 'started_unix': started, 'finished_unix': time.time(), 'returncode': result.returncode,
           'inputs_SHA256': hashlib.sha256(inputs.read_bytes()).hexdigest(),
           'builder_SHA256': hashlib.sha256((HERE / 'build_gpu_manifest_linked02.py').read_bytes()).hexdigest(),
           'final_worker_SHA256': FINAL_WORKER, 'local_freeze_only': True,
           'stage_submit_model_GPU_GUI_health_network_calls': 0}
if result.returncode == 0:
    receipt['manifest_SHA256'] = hashlib.sha256((output / 'gpu-manifest.json').read_bytes()).hexdigest()
    receipt['launch_spec_SHA256'] = hashlib.sha256((output / 'launch-specification.json').read_bytes()).hexdigest()
    receipt['package_seal_SHA256'] = hashlib.sha256((output / 'seal.json').read_bytes()).hexdigest()
with (invocation / 'receipt.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
with (invocation / 'seal.json').open('x', encoding='utf-8') as stream:
    json.dump({x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(invocation.iterdir()) if x.is_file()}, stream, indent=2)
print(json.dumps(receipt))
if result.returncode:
    print(result.stderr.decode(errors='replace'))
raise SystemExit(result.returncode)
