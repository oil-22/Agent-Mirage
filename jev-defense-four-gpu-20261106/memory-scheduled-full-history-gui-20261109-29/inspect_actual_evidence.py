"""New29 actual locks/UID/cmd/request seals/chains; no inference probes."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'full-history-gui-development-20261109-23'
sys.path.insert(0, str(OLD))
source = (OLD / 'inspect_actual_evidence.py').read_text(encoding='utf8')
source = source.replace("HERE / 'runtime-package/manifest.json'", "HERE / 'runtime-package-linked02/manifest.json'")
source = source.replace('from remote_control import remote, save, sha, ROOT3090, ROOT4090',
    "from remote_control import remote, save, sha\nROOT3090='/home/researcher/jev-defense-four-gpu-20261106/" + HERE.name + "'\nROOT4090='/data/researcher/jev-defense-four-gpu-20261106/" + HERE.name + "'")
exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
