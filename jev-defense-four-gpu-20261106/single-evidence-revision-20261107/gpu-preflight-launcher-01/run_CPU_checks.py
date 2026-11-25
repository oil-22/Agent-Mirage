"""Run only pure safety controls and preserve one local immutable receipt."""
import json
import hashlib
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
output = HERE / 'CPU-resource-contract-01'
output.mkdir(exist_ok=False)
started = time.time()
result = subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v', 'test_resource_and_launch_contract'],
                        cwd=str(HERE), capture_output=True)
for name, raw in [('stdout.log', result.stdout), ('stderr.log', result.stderr)]:
    with (output / name).open('xb') as stream:
        stream.write(raw)
files = ['resource_gate.py', 'launch_once.py', 'test_resource_and_launch_contract.py', 'run_CPU_checks.py']
source = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in files}
receipt = {'started_unix': started, 'finished_unix': time.time(), 'returncode': result.returncode,
           'source_SHA256': source, 'CPU_fixture_only': True, 'actual_GPU_or_proc_gate_exercised': False,
           'model_import_calls_GUI_health_network_process_or_GPU_lock_mutations': 0,
           'actual_remote_stage_or_submit': False}
with (output / 'receipt.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
with (output / 'seal.json').open('x', encoding='utf-8') as stream:
    json.dump({x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(output.iterdir()) if x.is_file()}, stream, indent=2)
print(json.dumps({'returncode': result.returncode, 'receipt_SHA256': hashlib.sha256((output / 'receipt.json').read_bytes()).hexdigest(),
                  'seal_SHA256': hashlib.sha256((output / 'seal.json').read_bytes()).hexdigest(), 'source_SHA256': source}))
if result.returncode:
    print(result.stderr.decode(errors='replace'))
raise SystemExit(result.returncode)
