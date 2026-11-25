"""Recorded SSH transport; no embedded credentials and no old queue actions."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SSH = ['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config',
       '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with Path(p).open('x', encoding='utf8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def remote(host, code, label, timeout=55, private_prefix=''):
    root = HERE / 'operations' / (str(time.time_ns()) + '-' + label)
    root.mkdir(parents=True)
    (root / 'source.py').write_text(code, encoding='utf8')
    python = '/opt/whz/conda-envs/webmall-vlm/bin/python' if host == '3090' else '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python'
    try:
        completed = subprocess.run(SSH + [host, python + ' -B -'], input=private_prefix + code,
                                   text=True, encoding='utf8', capture_output=True, timeout=timeout)
        (root / 'stdout.txt').write_text(completed.stdout, encoding='utf8')
        (root / 'stderr.txt').write_text(completed.stderr, encoding='utf8')
        save(root / 'receipt.json', {'host': host, 'returncode': completed.returncode,
                                    'source_sha256': sha(root / 'source.py'), 'time': time.time()})
    except BaseException as exc:
        if isinstance(exc, subprocess.TimeoutExpired):
            for name, value in [('stdout', exc.stdout), ('stderr', exc.stderr)]:
                (root / (name + '-partial.bin')).write_bytes(value.encode('utf8') if isinstance(value, str) else value or b'')
        save(root / 'failure.json', {'type': type(exc).__name__, 'message': str(exc)})
        raise
    finally:
        save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    if completed.returncode:
        raise RuntimeError(str(root) + '\n' + completed.stderr[-3500:] + '\n' + completed.stdout[-1500:])
    return completed.stdout, root
