"""Freeze new Controller routing check and package-source invariance receipt."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    assert not (HERE / 'CPU-routing-current.json').exists()
    prepared = json.loads((HERE / 'preparation-current.json').read_bytes())
    package = Path(prepared['package'])
    manifest = json.loads((package / 'manifest.json').read_bytes())
    assert sha(package / 'manifest.json') == prepared['manifest_sha256']
    for name, expected in manifest['files'].items():
        assert sha(package / name) == expected
    cpu = json.loads((HERE / 'CPU-source-current.json').read_bytes())
    assert cpu['passed']
    root = HERE / ('cpu-routing-' + str(time.time_ns()))
    root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    (root / 'test-source.py').write_bytes((HERE / 'test_trusted_routing.py').read_bytes())
    argv = [sys.executable, '-B', '-X', 'utf8', str(HERE / 'test_trusted_routing.py')]
    with (root / 'stdout.bin').open('xb') as out, (root / 'stderr.bin').open('xb') as err:
        result = subprocess.run(argv, cwd=HERE, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                                                    'PYTHONPATH': str(package / 'flash') + os.pathsep + str(package)}, stdout=out, stderr=err)
    passed = result.returncode == 0
    save(root / 'result.json', {'passed': passed, 'returncode': result.returncode, 'routing_controls': 11,
                              'manifest_sha256': prepared['manifest_sha256'], 'CPU_source_controls': cpu,
                              'new_model_GUI_calls': 0, 'not_real_defense_effectiveness': True})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    if not passed:
        print((root / 'stderr.bin').read_text('utf-8'))
        raise RuntimeError('Routing qualification failed; preserved ' + str(root))
    save(HERE / 'CPU-routing-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                                           'passed': True, 'manifest_sha256': prepared['manifest_sha256']})
    print(json.dumps({'root': str(root), 'passed': True, 'routing_controls': 11, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
