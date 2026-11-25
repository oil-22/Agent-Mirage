"""Publish a new source-linked stable-stat identity receipt. Leave completion terminal unchanged."""
import hashlib
import json
from pathlib import Path
import time

BASE = Path(__file__).resolve().parent
REV = '9ff7cf9838e59df461c276b7699d56b244d2af58'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stat(path):
    row = path.stat()
    return {'dev': row.st_dev, 'ino': row.st_ino, 'size': row.st_size, 'mtime_ns': row.st_mtime_ns}


def main():
    pointer = json.loads((BASE / 'download-current.json').read_bytes())
    completion = Path(pointer['root']) / 'download-complete-receipt.json'
    expected_sha = pointer['receipt_sha256']
    assert sha(completion) == expected_sha
    completed = json.loads(completion.read_bytes())
    assert completed['revision'] == REV and completed['status'] == 'complete'
    checkpoint = Path(completed['checkpoint']).resolve()
    root = BASE / 'identity-bindings' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    files = []
    for row in completed['files']:
        path = (checkpoint / row['file']).resolve()
        assert path.is_relative_to(checkpoint)
        before = stat(path)
        assert before['size'] == row['bytes']
        files.append({'file': row['file'], 'bytes': row['bytes'], 'sha256': row['sha256'], 'stat': before})
    assert {row['file'] for row in files} == {str(path.relative_to(checkpoint))
                                              for path in checkpoint.rglob('*') if path.is_file()}
    assert all(stat(checkpoint / row['file']) == row['stat'] for row in files)
    receipt = {'status': 'identity_bound', 'repository': completed['repository'], 'revision': REV,
               'checkpoint': str(checkpoint), 'completion_receipt': str(completion),
               'completion_receipt_sha256': expected_sha, 'files': files, 'stable_stat_recheck': True,
               'identity_sha_source': 'Completed full Git/LFS verification and SHA256 receipt; no redundant full-weight rehash',
               'new_model_calls': 0, 'GPU_allocations': 0}
    (root / 'receipt.json').write_text(json.dumps(receipt, indent=2))
    (root / 'seal.json').write_text(json.dumps({'receipt.json': sha(root / 'receipt.json')}, indent=2))
    pointer = {'receipt': str(root / 'receipt.json'), 'receipt_sha256': sha(root / 'receipt.json'),
               'checkpoint': str(checkpoint), 'revision': REV, 'status': 'identity_bound'}
    (BASE / 'identity-current.json').write_text(json.dumps(pointer, indent=2))
    print(json.dumps(pointer))


if __name__ == '__main__':
    main()
