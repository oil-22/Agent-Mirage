"""Read back the three small native files used to audit Flash probability provenance."""

from pathlib import Path
import shlex
import subprocess

from launch_panel import HERE, SSH
from live_common import hash_bytes, load, put, save

FILES = ('decision_config.json', 'source/src/pplx_decider/model.py', 'source/src/pplx_decider/protocol.py')


def main():
    cfg = load(HERE / 'service-config.json')
    expected = {v['file']: v['sha256'] for v in load(HERE / 'flash-identity.json')['files']}
    dest = HERE / 'flash-native-audit-source'
    dest.mkdir(exist_ok=False)
    for rel in FILES:
        path = shlex.quote(cfg['model_dir'] + '/' + rel)
        proc = subprocess.run(SSH + [f'cat {path}'], capture_output=True, timeout=20, check=True)
        assert hash_bytes(proc.stdout) == expected[rel], rel
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        put(out, proc.stdout)
    save(dest / 'source-seal.json', {'revision': cfg['revision'], 'files': {p: expected[p] for p in FILES}})
    print('Verified 3 small native source/config files against the existing complete weight identity.')


if __name__ == '__main__':
    main()
