"""Run original27 plus4 new linked safety controls; preserve new source bindings."""
import json
import hashlib
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'launcher-linked02'
OUT = HERE / 'CPU-resource-contract-linked02'
OUT.mkdir(exist_ok=False)
started = time.time()
result = subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v', 'test_resource_and_launch_contract', 'test_linked_safety'],
                        cwd=str(SOURCE), capture_output=True)
for name, raw in [('stdout.log', result.stdout), ('stderr.log', result.stderr)]:
    with (OUT / name).open('xb') as stream:
        stream.write(raw)
source = {x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(SOURCE.iterdir()) if x.is_file()}
receipt = {'started_unix': started, 'completed_unix': time.time(), 'returncode': result.returncode,
           'source_SHA256': source, 'CPU_fixture_only': True, 'expected_test_count': 31,
           'actual_remote_proc_GPU_model_GUI_health_stage_submit_calls': 0,
           'old_CPU27_sources_and_receipt_untouched': True}
with (OUT / 'receipt.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
with (OUT / 'seal.json').open('x', encoding='utf-8') as stream:
    json.dump({x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(OUT.iterdir()) if x.is_file()}, stream, indent=2)
print(json.dumps({'returncode': result.returncode, 'receipt_SHA256': hashlib.sha256((OUT / 'receipt.json').read_bytes()).hexdigest(),
                  'seal_SHA256': hashlib.sha256((OUT / 'seal.json').read_bytes()).hexdigest(), 'source_SHA256': source}))
if result.returncode:
    print(result.stderr.decode(errors='replace'))
raise SystemExit(result.returncode)
