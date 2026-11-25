"""Prepare an exact new-layout launch command, without submitting it to holder."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, indent=2)


assert os.getuid() == 1033
old = BASE / 'concrete-preparation-1793974680915187332/paths.json'
assert sha(old) == '56b6885dbe2ec944df90404daab1fabd09f1da0aad28c39ab775d7e025a93c44'
layout = BASE / 'placement-header-linked/1793975022794954809/receipt.json'
assert sha(layout) == 'bbeb9fcc8659fefcdc3e99196c283b469b073bcb66d80a47b6b14a45b0a0359c'
worker = BASE / 'runtime-preparation/preflight_service.py'
assert sha(worker) == '90604e7f75fb2d43aebae5f634c9f07b59fb18566434851d686090d4fa70a877'
prepare = BASE / 'runtime-preparation/prepare_launch_spec.py'
assert sha(prepare) == '6f8b8652d74a9b29f243811f8d1f33d8c144a6e9dcd17bec86bc4ff241bdb270'
launcher = BASE / 'runtime-preparation/launch_preflight_group.py'
assert sha(launcher) == '3a42b90cd56b7bbe0bf21c90fc21927b5652a50fe1c5e30741c2de63f55af073'
root = BASE / ('reviewed-launch-' + str(time.time_ns()))
root.mkdir(exist_ok=False)
paths = json.loads(old.read_bytes())
paths.update(primary_native_layout_receipt=str(layout),
             primary_native_layout_receipt_sha256=sha(layout))
save(root / 'paths.json', paths)
spec = root / 'spec.json'
subprocess.run([sys.executable, str(prepare), '--paths', str(root / 'paths.json'),
    '--output', str(spec)], check=True)
group = BASE / ('model-preflight-group-' + str(time.time_ns()))
command = {'action': 'launch', 'argv': [sys.executable, str(launcher), '--root', str(group),
    '--spec', str(spec), '--spec-sha256', sha(spec)], 'script_sha256': sha(launcher)}
assert sys.executable == '/opt/whz/conda-envs/webmall-vlm/bin/python'
save(root / 'holder-command.json', command)
save(root / 'receipt.json', {'time': time.time(), 'model_calls': 0, 'GPU_allocations': 0,
    'launch_submitted': False, 'group': str(group),
    'spec_sha256': sha(spec), 'command_sha256': sha(root / 'holder-command.json'),
    'native_header_receipt_sha256': sha(layout),
    'worker_sha256': sha(worker), 'launcher_sha256': sha(launcher)})
save(root / 'seal.json', {path.name: sha(path) for path in root.iterdir() if path.is_file()})
print(json.dumps({'root': str(root), 'group': str(group), 'spec_sha256': sha(spec),
    'holder_command': str(root / 'holder-command.json'), 'launch_submitted': False}))
