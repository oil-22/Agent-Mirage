"""Root's once-only linked submit invocation; capture the real SSH streams."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).resolve().parent
PROOF = BASE / 'runtime-preparation/submit-control-evidence/1793986405735234912'

if __name__ == '__main__':
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(PROOF / 'submit_path_compatible.py') == 'a2046fc4862714791462681f04f8384485e8a2fa195abb227ff03c15dfd787c8'
    assert sha(PROOF / 'receipt.json') == 'f8d958d006cb6fd1626a3ddd5a540cfc02161bbf894254fcef42dbc97572598f'
    seal = json.loads((PROOF / 'seal.json').read_bytes())
    for name, expected in seal.items():
        assert sha(PROOF / name) == expected, name
    output = BASE / 'runtime-preparation/actual-three-submission-01'
    output.mkdir(exist_ok=False)
    argv = [r'D:\Git\usr\bin\ssh.exe', '-F', r'C:\Users\researcher\.ssh\config',
        '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '3090',
        '/opt/whz/conda-envs/webmall-vlm/bin/python',
        '/home/researcher/jev-defense-four-gpu-20261106/online-submit-control-repair/1793986405735234912/submit_path_compatible.py',
        '--command', '/home/researcher/jev-defense-four-gpu-20261106/online-three-source-preparation/1793985778592347799/holder-command.proposed.json',
        '--command-sha256', 'ba037c55849e953c73e5320f084a86a49069045449dec5fad9f4667c3171d246']
    (output / 'invocation.json').write_text(json.dumps({'time': time.time(), 'argv': argv,
        'root_source_sha256': sha(Path(__file__)), 'no_automatic_retry': True}, indent=2), encoding='utf8')
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    (output / 'stdout.txt').write_bytes(result.stdout)
    (output / 'stderr.txt').write_bytes(result.stderr)
    (output / 'result.json').write_text(json.dumps({'returncode': result.returncode, 'time': time.time(),
        'stdout_sha256': sha(output / 'stdout.txt'), 'stderr_sha256': sha(output / 'stderr.txt')}, indent=2), encoding='utf8')
    (output / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in output.iterdir() if p.is_file()}, indent=2), encoding='utf8')
    print(result.stdout.decode(errors='replace'))
    if result.returncode:
        print(result.stderr.decode(errors='replace'))
    print(json.dumps({'output': str(output), 'returncode': result.returncode, 'seal_sha256': sha(output / 'seal.json')}))
    raise SystemExit(result.returncode)
