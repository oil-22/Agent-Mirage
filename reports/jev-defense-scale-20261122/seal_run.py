"""Seal a worker's closed evidence, including failed or partial trials."""
from pathlib import Path
import sys

from live_common import save, sha

root = Path(__file__).resolve().parent
run = root / 'run'
assert run.is_dir()
save(root / 'remote-seal.json', {'input_manifest_sha256': sha(root / 'manifest.json'), 'exit_status': int(sys.argv[1]),
                                 'files': {p.relative_to(root).as_posix(): sha(p) for p in run.rglob('*') if p.is_file()}})
