# Linked root control: only the local preservation output path changed.
# Parent source SHA256: 3a805d5bb1c897d4af31d5d6a5ea336f25cd380ead75198d40f63bc92df6d133
"""Root-only sequential fresh ownership, exact GUI preparation and one launch."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
COLLECTOR = BASE / 'transport-preparation/ownership-proof-collector-three-01/collect_ownership_transport.py'
GROUP = '/home/researcher/jev-defense-four-gpu-20261106/online-three-service-group-1793985778592347799'
PACKAGE = '/data/researcher/jev-defense-four-gpu-20261106/gui-migration-three-linked02'
CONTROL = '/data/researcher/jev-defense-four-gpu-20261106/gui-three-control-preparation-01'
REMOTE = r'''
import hashlib,json,pathlib,subprocess,sys
B=pathlib.Path('/data/researcher/jev-defense-four-gpu-20261106')
C=B/'gui-three-control-preparation-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(C/'seal.json')==CFG['control_seal_sha256']
for name,expected in json.loads((C/'seal.json').read_bytes()).items():assert sha(C/name)==expected,name
P='/data/researcher/venvs/qwen35-9b-full-20261019/bin/python'
argv=[P,'-B',str(C/'prepare_bound_once.py'),'--resource',CFG['resource'],'--resource-sha256',CFG['resource_sha256'],
 '--ownership',CFG['ownership'],'--ownership-sha256',CFG['ownership_sha256'],
 '--output',str(B/'gui-three-evidence-binding-01')]
r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
sys.stdout.buffer.write(r.stdout);sys.stdout.buffer.flush()
sys.stderr.buffer.write(r.stderr);sys.stderr.buffer.flush()
if r.returncode:raise SystemExit(r.returncode)
spec=B/'gui-final-readiness-three-01/launch-spec.json'
actual=sha(spec)
print(json.dumps({'actual_launch_spec':str(spec),'sha256':actual}),flush=True)
r=subprocess.run([P,'-B',str(C/'background_three_once.py'),'--spec',str(spec),'--spec-sha256',actual],
 stdout=subprocess.PIPE,stderr=subprocess.PIPE)
sys.stdout.buffer.write(r.stdout);sys.stdout.buffer.flush()
sys.stderr.buffer.write(r.stderr);sys.stderr.buffer.flush()
raise SystemExit(r.returncode)
'''


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for key in ('resource', 'resource-sha256', 'ready-evidence', 'ready-evidence-sha256', 'control-seal-sha256'):
        p.add_argument('--' + key, required=True)
    a = p.parse_args()
    assert sha(COLLECTOR) == '890480f21c5eefd363564a95563cc713f720accb79eb227f8fa82831ceff2ecf'
    out = BASE / 'actual-three-GUI-start-linked02'
    out.mkdir(exist_ok=False)
    (out / 'root-invocation.json').write_text(json.dumps({'time': time.time(), 'arguments': vars(a),
        'root_source_sha256': sha(Path(__file__)), 'automatic_retry': False}, indent=2), encoding='utf8')
    argv = [sys.executable, '-B', str(COLLECTOR), '--group', GROUP,
        '--bridge-session', str(BASE / 'transport-preparation/three-bridge-session-01'),
        '--wrapper-local', str(BASE / 'policy-preparation/image-observer-policy/gui-migration-three-linked02/gui_once.py'),
        '--wrapper-remote', PACKAGE + '/gui_once.py',
        '--wrapper-sha256', 'e660bd664ca94355a3d1109611dc18aa8069abd77f92c9dcb18265477f58792d',
        '--ready-evidence', a.ready_evidence, '--ready-evidence-sha256', a.ready_evidence_sha256,
        '--output', str(out / 'fresh-ownership')]
    try:
        c = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        (out / 'collector.stdout.txt').write_bytes(c.stdout)
        (out / 'collector.stderr.txt').write_bytes(c.stderr)
        if c.returncode:
            print(c.stderr.decode(errors='replace'))
            raise RuntimeError('Fresh collector failed; no GUI launch or automatic retry')
        proof = json.loads(c.stdout.decode().splitlines()[-1])
        print(json.dumps({'fresh_ownership': proof}), flush=True)
        cfg = {'resource': a.resource, 'resource_sha256': a.resource_sha256,
            'ownership': proof['proof'], 'ownership_sha256': proof['sha256'],
            'control_seal_sha256': a.control_seal_sha256}
        code = 'CFG=' + repr(cfg) + '\n' + REMOTE
        (out / 'remote-invocation.py').write_text(code, encoding='utf8')
        r = subprocess.run([r'D:\Git\usr\bin\ssh.exe', '-F', r'C:\Users\researcher\.ssh\config',
            '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '4090', 'python3', '-'],
            input=code.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        (out / 'prepare-and-background.stdout.txt').write_bytes(r.stdout)
        (out / 'prepare-and-background.stderr.txt').write_bytes(r.stderr)
        (out / 'result.json').write_text(json.dumps({'returncode': r.returncode,
            'no_automatic_retry': True, 'completion_requires_actual_requests': True, 'time': time.time()}, indent=2), encoding='utf8')
        print(r.stdout.decode(errors='replace'))
        if r.returncode:
            print(r.stderr.decode(errors='replace'))
            raise RuntimeError('GUI control returned failure; inspect actual claims and preserve')
    except subprocess.TimeoutExpired as error:
        (out / 'timeout.partial.stdout.txt').write_bytes(error.stdout or b'')
        (out / 'timeout.partial.stderr.txt').write_bytes(error.stderr or b'')
        (out / 'timeout.json').write_text(json.dumps({'timeout_seconds': error.timeout,
            'launch_state': 'unknown_requires_actual_claim_process_request_inspection',
            'no_automatic_retry': True, 'time': time.time()}, indent=2), encoding='utf8')
        raise
    finally:
        (out / 'seal.json').write_text(json.dumps({f.name: sha(f) for f in out.iterdir() if f.is_file()}, indent=2), encoding='utf8')
        print(json.dumps({'output': str(out), 'seal_sha256': sha(out / 'seal.json')}), flush=True)
