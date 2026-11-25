"""Parallel transport of the exact native cu126 CP314 wheels, pinned by official index SHA256."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parent


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(value for name, value in attrs if name == 'href')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def main():
    root = BASE / 'native-wheel-downloads' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())

    def download(item):
        package, version = item
        index = 'https://download.pytorch.org/whl/cu126/' + package + '/'
        with urllib.request.urlopen(index, timeout=40) as response:
            raw = response.read()
        (root / (package + '-index.html')).write_bytes(raw)
        parser = Links()
        parser.feed(raw.decode())
        prefix = package + '-' + version + '+cu126-cp314-cp314-'
        links = [urllib.parse.urljoin(index, link) for link in parser.links
                 if urllib.parse.unquote(urllib.parse.urlsplit(link).path).split('/')[-1].startswith(prefix)
                 and 'manylinux_2_28_x86_64.whl' in urllib.parse.unquote(link)]
        assert len(links) == 1, (package, len(links))
        url = links[0]
        expected = urllib.parse.parse_qs(urllib.parse.urlsplit(url).fragment)['sha256'][0]
        name = urllib.parse.unquote(urllib.parse.urlsplit(url).path).split('/')[-1]
        dest = root / name
        with (root / (package + '.download.log')).open('xb') as log:
            p = subprocess.run(['/usr/bin/aria2c', '--continue=true', '--allow-overwrite=false',
                '--auto-file-renaming=false', '--file-allocation=none', '--split=16',
                '--max-connection-per-server=16', '--max-tries=3', '--retry-wait=3', '--timeout=40',
                '--connect-timeout=20', '--summary-interval=10', '--dir=' + str(root), '--out=' + name,
                url.split('#')[0]], stdout=log, stderr=subprocess.STDOUT)
        assert p.returncode == 0, package
        assert sha(dest) == expected, package
        row = {'package': package, 'version': version + '+cu126', 'file': str(dest),
               'bytes': dest.stat().st_size, 'sha256': expected, 'source_index': index, 'download_url': url}
        print(json.dumps({'verified_wheel': package, 'bytes': row['bytes']}), flush=True)
        return row

    rows = []
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(download, [('torch', '2.14.0'), ('torchvision', '0.29.0')]))
        (root / 'receipt.json').write_text(json.dumps({'wheels': rows, 'model_calls': 0,
                                                      'GPU_allocations': 0}, indent=2))
        (BASE / 'native-wheel-current.json').write_text(json.dumps({'root': str(root), 'wheels': rows}, indent=2))
        print(json.dumps({'root': str(root), 'status': 'complete'}), flush=True)
    except BaseException:
        import traceback
        (root / 'failure.txt').write_text(traceback.format_exc())
        raise
    finally:
        (root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)): sha(p)
                                                   for p in root.rglob('*') if p.is_file()}, indent=2))


if __name__ == '__main__':
    main()
