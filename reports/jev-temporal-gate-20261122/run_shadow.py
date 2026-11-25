"""Run the frozen Flash double-image panel once; collect and verify after the process exits."""

import argparse
import io
from pathlib import Path
import shlex
import subprocess
import tarfile
import time

from prepare_and_probe import HERE, PACKAGE, SSH, WORKSPACE, dump, freeze, read, sha


def main(cpu_attempt):
    cpu_root = HERE / 'attempts' / cpu_attempt
    cpu_seal = read(cpu_root / 'seal.json')
    assert all(sha((cpu_root / k).read_bytes()) == v for k, v in cpu_seal.items())
    python, files = freeze()
    frozen = read(cpu_root / 'input-manifest.json')
    assert {k: sha(v) for k, v in files.items()} == frozen
    files.pop('cpu_native.py')
    reference = WORKSPACE / 'jev-defense-four-gpu-20261106' / 'flash-quality-only-development-20261116-10'
    prepared = reference / 'preparation-1794818715065933700' / 'package'
    guard = (prepared / 'flash' / 'resource_guard.py').read_bytes()
    assert sha(guard) == read(prepared / 'manifest.json')['files']['flash/resource_guard.py']
    files.update({'cpu-prepared.json': (cpu_root / 'stdout.json').read_bytes(),
                  'shadow_gpu.py': (HERE / 'shadow_gpu.py').read_bytes(), 'resource_guard.py': guard,
                  **{k: (PACKAGE / k).read_bytes() for k in ('flash-identity.json', 'service-config.json')}})
    name = f'shadow-{time.time_ns()}'
    remote = '/data/researcher/jev-temporal-gate-20261122/' + name
    home = HERE / 'attempts' / name
    home.mkdir(exist_ok=False)
    files['manifest.json'] = dump({'max_new_native_calls': 8, 'retries': 0,
                                  'cpu_input_seal_sha256': sha((cpu_root / 'seal.json').read_bytes()),
                                  'files': {k: sha(v) for k, v in files.items()}})
    for k, v in files.items():
        if not k.startswith('images/'):
            (home / k).write_bytes(v)
    (home / 'remote-root.txt').write_text(remote + '\n', encoding='ascii')
    print(name, 'manifest', sha(files['manifest.json']), flush=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tar:
        for k, v in files.items():
            entry = tarfile.TarInfo(k)
            entry.size, entry.mode = len(v), 0o600
            tar.addfile(entry, io.BytesIO(v))
    command = (f'umask 077; mkdir {remote} && tar -xf - -C {remote} && cd {remote} '
               f'&& {shlex.quote(python)} -B -u shadow_gpu.py')
    with (home / 'worker-stderr.log').open('xb') as stderr:
        worker = subprocess.run(SSH + [command], input=buf.getvalue(), stderr=stderr)
    worker_command = f'cd {remote} && {shlex.quote(python)} -B -u shadow_gpu.py --audit'
    proof = subprocess.run(SSH + [worker_command], capture_output=True, timeout=50)
    (home / 'audit-stdout.json').write_bytes(proof.stdout)
    (home / 'audit-stderr.log').write_bytes(proof.stderr)
    if proof.returncode:
        print(proof.stderr.decode('utf-8', 'replace'), flush=True)
        raise SystemExit(proof.returncode)
    audit = read(home / 'audit-stdout.json')
    raw = subprocess.check_output(SSH + [f'cd {remote} && tar -cf - run'], timeout=35)
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        archive.extractall(home, filter='data')
    actual = {p.relative_to(home / 'run').as_posix(): sha(p.read_bytes())
              for p in (home / 'run').rglob('*') if p.is_file()}
    assert actual == audit['sealed_members'] and read(home / 'run' / 'terminal.json') == audit['terminal']
    (home / 'local-seal.json').write_bytes(dump({p.relative_to(home).as_posix(): sha(p.read_bytes())
                                              for p in home.rglob('*') if p.is_file()}))
    summary = audit['terminal']
    print(summary['status'], 'attempted', summary['attempted'], 'replies', len(summary['replies']), flush=True)
    if worker.returncode:
        print(summary['error'], flush=True)
        raise SystemExit(worker.returncode)
    assert audit['lease_process_exited'] and len(audit['released_locks']) == 3
    assert summary['attempted'] == 8 and len(summary['replies']) == 8
    for row in summary['replies']:
        print(row['case'], row['choice'], 'P(YES)', round(row['probabilities']['YES'], 5), flush=True)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('cpu_attempt')
    args = cli.parse_args()
    assert args.cpu_attempt.startswith('cpu-probe-') and args.cpu_attempt[10:].isdigit()
    main(args.cpu_attempt)
