"""New linked CPU verification; preserve every attempted test output and source."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import hashlib

BASE = Path(__file__).resolve().parent
PARENT = BASE.parents[1] / 'jev-defense-validation-20261103/release'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root = BASE / 'cpu-evidence' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    before = {str(p.relative_to(PARENT)):sha(p) for p in PARENT.rglob('*.py')}
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(PARENT),str(BASE)]))
    result = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_flash_policy'],
                            cwd=BASE, env=env, capture_output=True)
    (root/'stdout.log').write_bytes(result.stdout); (root/'stderr.log').write_bytes(result.stderr)
    for name in ['flash_policy.py','test_flash_policy.py','freeze_flash_preflight.py','verify_policy.py']:
        (root/name).write_bytes((BASE/name).read_bytes())
    after = {str(p.relative_to(PARENT)):sha(p) for p in PARENT.rglob('*.py')}
    receipt={'test_returncode':result.returncode, 'tests':16,
        'scope':'CPU scripted control flow; not model semantics or generation',
        'parent_release_python_count':len(before),'parent_release_unchanged':before==after,
        'model_calls':0,'GUI_actions':0,'source_parent_hashes':before}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    (root/'seal.json').write_text(json.dumps({p.name:sha(p) for p in root.iterdir()
                                             if p.is_file()},indent=2),encoding='utf8')
    print(json.dumps({'root':str(root),**{k:v for k,v in receipt.items() if k!='source_parent_hashes'}}))
    assert before==after, 'Original release changed during verification'
    raise SystemExit(result.returncode)


if __name__=='__main__':main()
