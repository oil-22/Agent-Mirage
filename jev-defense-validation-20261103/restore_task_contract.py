"""Extract only the historical task configuration; never display evaluator answers."""
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import time

BASE = Path('/data/researcher/jev-defense-validation-20261103')
ARCHIVE = Path('/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz')
EXPECTED = 'b2dd3cef7cc6357376b95ef8c64ae4fcad839fd7f705e55afbdeb4a3d6a83603'


def main():
    root = BASE / ('task-restore-' + str(time.time_ns()))
    root.mkdir(parents=True, exist_ok=False)
    rows = [json.loads(line) for line in gzip.open('/data/researcher/attention-audit-20261031/members.jsonl.gz', 'rt')]
    table = {r[0]: r for r in rows}
    targets = {r[0] for r in rows if r[0].endswith('/classifieds_112.json')}
    for name in list(targets):
        while table[name][2] == '1':
            name = table[name][3];targets.add(name)
    initial = ARCHIVE.stat();found = None;started = time.time()
    with (root / 'decompress.log').open('xb') as log:
        p = subprocess.Popen(['pigz', '-p', '2', '-dc', str(ARCHIVE)], stdout=subprocess.PIPE, stderr=log)
        try:
            with tarfile.open(fileobj=p.stdout, mode='r|') as archive:
                for member in archive:
                    if member.name not in targets or not member.isfile():continue
                    rel = PurePosixPath(member.name)
                    assert not rel.is_absolute() and '..' not in rel.parts
                    raw = archive.extractfile(member).read()
                    if hashlib.sha256(raw).hexdigest() != EXPECTED:continue
                    (root / 'classifieds_112.PRIVATE.json').write_bytes(raw)
                    found = member.name;break
        finally:
            p.terminate();p.wait(timeout=15)
    assert ARCHIVE.stat().st_size == initial.st_size and ARCHIVE.stat().st_mtime_ns == initial.st_mtime_ns
    result = {'source_archive': str(ARCHIVE), 'archive_bytes': initial.st_size,
              'source_member': found, 'exact_historical_task_sha256': EXPECTED if found else None,
              'private_evaluator_answer_exported_to_model': False, 'model_calls': 0,
              'seconds': time.time() - started, 'status': 'complete' if found else 'not_found'}
    (root / 'receipt.json').write_text(json.dumps(result, indent=2))
    assert found, 'Exact historical task bytes not found; no replacement allowed'
    print(json.dumps({'root': str(root), 'status': result['status'], 'task_sha256': EXPECTED}))


if __name__ == '__main__':main()
