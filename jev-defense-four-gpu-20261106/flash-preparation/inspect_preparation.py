"""Read only this preparation's processes, download logs and open pip download files."""
import json
import os
from pathlib import Path
import time

base = Path(__file__).resolve().parent
rows = []
for proc in Path('/proc').iterdir():
    try:
        if not proc.name.isdigit() or proc.stat().st_uid != 1033:
            continue
        cmd = proc.joinpath('cmdline').read_bytes().split(b'\0')
        cmd = [part.decode() for part in cmd if part]
        if not cmd or not any(str(base) in arg for arg in cmd):
            continue
        if not (any('download_pinned_flash' in arg for arg in cmd) or
                ('pip' in cmd and str(base / 'env-flash-01') in cmd[0])):
            continue
        row = {'pid': int(proc.name), 'uid': proc.stat().st_uid, 'command': cmd,
               'start_ticks': proc.joinpath('stat').read_text().split()[21],
               'io': proc.joinpath('io').read_text(), 'open_pip_files': []}
        for descriptor in proc.joinpath('fd').iterdir():
            try:
                target = Path(os.readlink(descriptor))
                if str(target).startswith('/tmp/pip-') and target.is_file():
                    stat = target.stat()
                    row['open_pip_files'].append({'path': str(target), 'bytes': stat.st_size,
                                                  'allocated_disk_bytes': stat.st_blocks * 512})
            except OSError:
                pass
        rows.append(row)
    except (OSError, ProcessLookupError):
        pass
out = {'time': time.time(), 'processes': rows, 'download_logs': []}
for root in sorted((base / 'download-attempts').iterdir()):
    if (root / 'failure.json').exists():
        continue
    for log in root.glob('*.download.log'):
        text = log.read_text(errors='replace')
        progress = [line for line in text.splitlines() if 'GiB/' in line or 'MiB/' in line]
        out['download_logs'].append({'file': str(log), 'last_progress': progress[-1:]})
target = base / 'inspections' / (str(time.time_ns()) + '.json')
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(out, indent=2))
print(json.dumps({'receipt': str(target), **out}, indent=2))
