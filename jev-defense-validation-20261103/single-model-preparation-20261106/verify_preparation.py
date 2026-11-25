"""One immutable CPU preparation receipt; never contacts a model or GPU."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
RELEASE = ROOT.parent / 'release'

def hashes(root):
    return {str(p.relative_to(root)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*.py'))}

before = hashes(RELEASE)
attempt = ROOT / 'cpu-evidence' / str(time.time_ns())
attempt.mkdir(parents=True, exist_ok=False)
(attempt / 'parent-before.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
run = subprocess.run([sys.executable, '-B', str(ROOT / 'test_single_jev_controller.py'), '-v'],
                     capture_output=True, text=True, cwd=str(ROOT))
(attempt / 'stdout.txt').write_text(run.stdout, encoding='utf-8')
(attempt / 'stderr.txt').write_text(run.stderr, encoding='utf-8')
after = hashes(RELEASE)
(attempt / 'parent-after.json').write_text(json.dumps(after, indent=2), encoding='utf-8')
receipt = {'scope': 'CPU contract fixtures; not semantic/model/GUI verification',
           'test_returncode': run.returncode,
           'parent_python_files': len(before), 'parent_python_unchanged': before == after,
           'selected_model_option': 'neohorse', 'selection_final': False,
           'new_model_calls': 0, 'new_GUI_actions': 0, 'new_GPU_allocations': 0,
           'service_process_changes': 0, 'deployment_applied': False,
           'full_GUI_launch_ready': False,
           'source_files': hashes(ROOT)}
(attempt / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
seal = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(attempt.iterdir()) if p.is_file()}
(attempt / 'seal.json').write_text(json.dumps(seal, indent=2), encoding='utf-8')
print(json.dumps({'root': str(attempt), **receipt}, indent=2))
sys.exit(0 if run.returncode == 0 and before == after else 1)
