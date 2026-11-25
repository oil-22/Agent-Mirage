"""Download fixed public Flash checkpoint and verify complete Git/LFS identity. No model execution."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

BASE = Path(__file__).resolve().parent
REPO = 'perplexity-ai/pplx-decider-flash-v1.2'
REV = '9ff7cf9838e59df461c276b7699d56b244d2af58'
HOST = 'https://hf-mirror.com'


def sha(path, kind='sha256'):
    h = hashlib.new(kind)
    if kind == 'sha1':
        h.update(('blob ' + str(path.stat().st_size) + '\0').encode())
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def request(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mirage-pinned-model-download/1.0'})
    return urllib.request.urlopen(req, timeout=40)


def main():
    assert os.getuid() == 1033
    root = BASE / 'download-attempts' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    state = {'pid': os.getpid(), 'uid': os.getuid(), 'revision': REV, 'repository': REPO,
             'started': time.time(), 'GPU_allocations': 0, 'model_calls': 0}
    (root / 'downloader-source.py').write_bytes(Path(__file__).read_bytes())
    (root / 'process.json').write_text(json.dumps(state, indent=2))
    dest = root / 'checkpoint'
    dest.mkdir()
    try:
        url = HOST + '/api/models/' + REPO + '/tree/' + REV + '?recursive=true&expand=true&limit=50'
        items = []
        page = 0
        while url:
            with request(url) as response:
                raw = response.read(20 * 1024**2)
                (root / ('tree-page-' + str(page) + '.json')).write_bytes(raw)
                parsed = json.loads(raw)
                assert isinstance(parsed, list)
                items.extend(parsed)
                link = response.headers.get('Link', '')
                nextlinks = [part.strip().split('>')[0].lstrip('<') for part in link.split(',') if 'rel="next"' in part]
                url = nextlinks[0] if nextlinks else None
                page += 1
        files = [item for item in items if item['type'] == 'file']
        assert len(files) >= 18 and any(item['path'].startswith('source/') for item in files)
        (root / 'complete-tree.json').write_text(json.dumps(files, indent=2))
        aria = shutil.which('aria2c')

        def download(item):
            name = item['path']
            path = dest / name
            assert path.resolve().is_relative_to(dest.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            fileurl = HOST + '/' + REPO + '/resolve/' + REV + '/' + name
            part = path.with_name(path.name + '.partial')
            if item['size'] >= 100_000_000 and aria:
                log = root / (name.replace('/', '--') + '.download.log')
                with log.open('xb') as output:
                    result = subprocess.run([aria, '--allow-overwrite=false', '--auto-file-renaming=false',
                        '--continue=true', '--max-tries=3', '--retry-wait=3', '--timeout=40',
                        '--connect-timeout=20', '--max-connection-per-server=8', '--split=8',
                        '--file-allocation=none', '--summary-interval=10', '--console-log-level=notice',
                        '--dir=' + str(path.parent), '--out=' + part.name, fileurl],
                        stdout=output, stderr=subprocess.STDOUT)
                assert result.returncode == 0, 'Download failed: ' + name
            else:
                with request(fileurl) as response, part.open('xb') as output:
                    shutil.copyfileobj(response, output, 8 * 1024**2)
            assert part.stat().st_size == item['size'], 'Byte count mismatch: ' + name
            actual_sha = sha(part)
            if item.get('lfs'):
                assert actual_sha == item['lfs']['oid'], 'LFS SHA mismatch: ' + name
            else:
                assert sha(part, 'sha1') == item['oid'], 'Git blob mismatch: ' + name
            part.rename(path)
            receipt = {'file': name, 'bytes': path.stat().st_size, 'sha256': actual_sha,
                       'expected_git_blob': item['oid'], 'expected_lfs_sha256': item.get('lfs', {}).get('oid')}
            print(json.dumps({'verified_file': name, 'bytes': receipt['bytes']}), flush=True)
            return receipt

        receipts = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(download, item) for item in files]
            for future in as_completed(futures):
                receipts.append(future.result())
        receipts.sort(key=lambda row: row['file'])
        completed = {**state, 'completed': time.time(), 'status': 'complete',
                     'files': receipts, 'file_count': len(receipts),
                     'total_bytes': sum(row['bytes'] for row in receipts),
                     'identity_method': 'Fixed-revision recursive Git tree: Git blob SHA1 and LFS SHA256; local SHA256 all files',
                     'checkpoint': str(dest)}
        (root / 'download-complete-receipt.json').write_text(json.dumps(completed, indent=2))
        (BASE / 'download-current.json').write_text(json.dumps({'root': str(root), 'checkpoint': str(dest),
                'revision': REV, 'receipt_sha256': sha(root / 'download-complete-receipt.json')}, indent=2))
        print(json.dumps({'completed': str(root), 'checkpoint': str(dest), 'files': len(receipts)}), flush=True)
    except BaseException as error:
        import traceback
        (root / 'failure.json').write_text(json.dumps({**state, 'failed': time.time(),
            'error': type(error).__name__ + ': ' + str(error), 'traceback': traceback.format_exc()}, indent=2))
        raise
    finally:
        seal = {str(path.relative_to(root)): sha(path) for path in root.rglob('*')
                if path.is_file() and path.name != 'seal.json' and not path.name.endswith('.partial')}
        (root / 'seal.json').write_text(json.dumps(seal, indent=2))


if __name__ == '__main__':
    main()
