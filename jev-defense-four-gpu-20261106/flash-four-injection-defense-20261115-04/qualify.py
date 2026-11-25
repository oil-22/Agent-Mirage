"""Seal CPU routing checks without any model or real GUI execution."""
import json
import subprocess
import sys
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    root = HERE / ('CPU-routing-' + str(time.time_ns()))
    root.mkdir()
    preparation = json.loads((HERE / 'preparation-current.json').read_bytes())
    package = Path(preparation['package'])
    manifest = json.loads((package / 'manifest.json').read_bytes())
    assert sha(package / 'manifest.json') == preparation['manifest_sha256']
    for name, expected in manifest['files'].items():
        assert sha(package / name) == expected, name
    for name in ['test_four_routes.py', 'qualify.py', 'prepare.py', 'injection.py', 'continuation_guard.py']:
        (root / name).write_bytes((HERE / name).read_bytes())
    command = [sys.executable, '-B', '-u', '-X', 'utf8', str(HERE / 'test_four_routes.py')]
    with (root / 'stdout.bin').open('xb') as stdout, (root / 'stderr.bin').open('xb') as stderr:
        completed = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=60)
    result = {'passed': completed.returncode == 0, 'return_code': completed.returncode,
              'tests': 11, 'manifest_sha256': sha(package / 'manifest.json'),
              'real_model_calls': 0, 'real_GUI_calls': 0, 'CPU_fixtures_not_model_evidence': True}
    save(root / 'result.json', result)
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    pointer = {'root': str(root), 'seal_sha256': sha(root / 'seal.json'), **result}
    if result['passed']:
        save(HERE / 'CPU-routing-current.json', pointer)
    print(json.dumps(pointer))
    if not result['passed']:
        print((root / 'stderr.bin').read_text('utf8'))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
