"""Transport-only linked attempt using the existing complete Python environment."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('original_finite_stager', HERE / 'stage_and_submit.py')
original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
original.REMOTE_PACKAGE += '/staged-linked02'


def remote(code, target):
    if target.name == 'actual-stage-01':
        target = target.with_name('actual-stage-linked02')
        # Seal the interrupted transport root before creating its linked child.
        prefix = r'''
from pathlib import Path
import json,hashlib,time
failed=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/joint-main-controls-20261108-01')
assert failed.is_dir() and not (failed/'staged-linked02').exists()
files={str(p.relative_to(failed)):hashlib.sha256(p.read_bytes()).hexdigest()for p in failed.rglob('*')if p.is_file()}
with (failed/'transport-failure-preservation.json').open('x')as f:
 json.dump({'time_unix':time.time(),'files_after_failed_extraction':files,'failure':'system python lacks zlib',
 'model_GUI_calls':0,'claim_or_holder_command_written':False,'linked_child':'staged-linked02','old_files_untouched':True},f,indent=2)
'''
        code = prefix + '\n' + code
    assert not target.exists()
    target.mkdir()
    (target / 'source.py').write_text(code, encoding='utf8')
    r = subprocess.run(['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=15', '3090', '/opt/whz/conda-envs/webmall-vlm/bin/python', '-'],
        input=code.encode(), capture_output=True, timeout=90)
    (target / 'stdout.json').write_bytes(r.stdout); (target / 'stderr.txt').write_bytes(r.stderr)
    original.save(target / 'process.json', {'returncode': r.returncode, 'GPU_allocations': 0,
        'repair': 'transport interpreter only; source input precision budgets unchanged'})
    original.save(target / 'seal.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest()for p in target.iterdir()if p.is_file()})
    print(r.stdout.decode())
    if r.returncode:
        print(r.stderr.decode()); raise RuntimeError('Preserved linked transport error; inspect before any retry')
    return json.loads(r.stdout)


original.remote = remote
if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['stage', 'submit'])
    if p.parse_args().action == 'stage':
        first = HERE / 'actual-stage-01'
        original.save(HERE / 'transport-failure-seal-01.json', {q.name: hashlib.sha256(q.read_bytes()).hexdigest()
            for q in first.iterdir() if q.is_file()})
        original.stage()
    else:
        original.submit()
