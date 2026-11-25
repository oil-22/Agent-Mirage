"""Reuse unchanged ABI-independent CUDA dependencies in a separate env, with RECORD byte verification."""
import base64
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import time

BASE = Path(__file__).resolve().parent
OLD = Path('/home/researcher/jev-defense-local-20261102/env-style').resolve()
NEW = (BASE / 'env-flash-01').resolve()
SOURCE = OLD / 'lib/python3.11/site-packages'
TARGET = NEW / 'lib/python3.14/site-packages'
PID = 2569143
START_TICKS = '1159219968'
COMMAND = [str(NEW / 'bin/python'), '-m', 'pip', 'install', 'torch==2.14.0', 'torchvision==0.29.0',
           '--index-url', 'https://download.pytorch.org/whl/cu126', '--report',
           str(BASE / 'env-torch-install-report.json')]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    assert os.getuid() == 1033
    root = BASE / 'env-install-transport-preservations' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    proc = Path('/proc') / str(PID)
    assert proc.stat().st_uid == 1033
    cmd = [p.decode() for p in proc.joinpath('cmdline').read_bytes().split(b'\0') if p]
    assert cmd == COMMAND
    assert proc.joinpath('stat').read_text().split()[21] == START_TICKS
    before = {'uid': 1033, 'pid': PID, 'command': cmd, 'start_ticks': START_TICKS,
              'reason': 'Preserve slow unfinished installer; reuse exact ABI-independent CUDA library bytes from own verified old env',
              'model_calls': 0, 'GPU_allocations': 0}
    # Preserve the in-flight wheel as partial data, not a successful downloaded artifact.
    partials = []
    for fd in proc.joinpath('fd').iterdir():
        try:
            path = Path(os.readlink(fd))
            if str(path).startswith('/tmp/pip-unpack-') and path.is_file():
                dest = root / (path.name + '.unfinished-snapshot')
                shutil.copyfile(path, dest)
                partials.append({'source': str(path), 'snapshot': dest.name, 'snapshot_bytes': dest.stat().st_size,
                                 'snapshot_sha256': sha(dest), 'complete_wheel': False})
        except OSError:
            pass
    before['unfinished_downloads'] = partials
    (root / 'before-stop.json').write_text(json.dumps(before, indent=2))
    pidfd = os.pidfd_open(PID) if hasattr(os, 'pidfd_open') else None
    if pidfd is not None:
        signal.pidfd_send_signal(pidfd, signal.SIGTERM)
    else:
        assert proc.stat().st_uid == 1033
        assert proc.joinpath('stat').read_text().split()[21] == START_TICKS
        assert [p.decode() for p in proc.joinpath('cmdline').read_bytes().split(b'\0') if p] == COMMAND
        os.kill(PID, signal.SIGTERM)
    deadline = time.time() + 15
    while proc.exists() and proc.joinpath('stat').read_text().split()[2] != 'Z' and time.time() < deadline:
        time.sleep(0.1)
    assert not proc.exists() or proc.joinpath('stat').read_text().split()[2] == 'Z'
    if pidfd is not None:
        os.close(pidfd)
    packages = sorted(SOURCE.glob('nvidia*.dist-info'))
    packages += [SOURCE / 'cuda_toolkit-12.6.3.dist-info', SOURCE / 'cuda_pathfinder-1.6.0.dist-info']
    copied = []
    for metadata in packages:
        wheel = (metadata / 'WHEEL').read_text()
        tags = [line.split(': ', 1)[1] for line in wheel.splitlines() if line.startswith('Tag: ')]
        assert tags and all('-none-' in tag and ('py3' in tag or 'py2' in tag) for tag in tags), metadata
        record = metadata / 'RECORD'
        files = []
        for name, expected, size in csv.reader(record.open()):
            source = (SOURCE / name).resolve()
            target = (TARGET / name).resolve()
            assert source.is_relative_to(OLD) and target.is_relative_to(NEW)
            if '__pycache__' in source.parts or source.suffix == '.pyc':
                continue
            assert source.is_file(), source
            actual = sha(source)
            if expected:
                algorithm, digest = expected.split('=', 1)
                assert algorithm == 'sha256', (metadata, name)
                expected_hex = base64.urlsafe_b64decode(digest + '=' * (-len(digest) % 4)).hex()
                assert actual == expected_hex, (metadata, name)
            if size:
                assert source.stat().st_size == int(size)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert sha(target) == actual, ('Unexpected preexisting target', target)
            else:
                shutil.copy2(source, target)
            assert sha(target) == actual
            files.append({'path': name, 'bytes': source.stat().st_size, 'sha256': actual,
                          'distribution_record_verified': bool(expected)})
        copied.append({'distribution': metadata.name, 'wheel_tags': tags,
                       'source_record_sha256': sha(record), 'files': files})
    receipt = {'status': 'complete', 'source_env': str(OLD), 'target_env': str(NEW),
               'all_old_files_unchanged': True, 'hardlinks_or_symlinks_created': False,
               'copied_distributions': copied, 'cp311_cuda_bindings_not_copied': True,
               'transport_change_only': True, 'native_model_requirement_versions_unchanged': True,
               'new_model_calls': 0, 'GPU_allocations': 0}
    (root / 'receipt.json').write_text(json.dumps(receipt, indent=2))
    (root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)): sha(p)
                                              for p in root.rglob('*') if p.is_file()}, indent=2))
    print(json.dumps({'root': str(root), 'copied_distributions': len(copied),
                      'copied_bytes': sum(f['bytes'] for d in copied for f in d['files']),
                      'stopped_only_owned_installer': PID, 'model_calls': 0}))


if __name__ == '__main__':
    main()
