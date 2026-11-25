"""Linked read-only observation retry; preserve every original SHA check."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'full-history-gui-development-20261109-23'
sys.path.insert(0, str(OLD))
pointer = json.loads((HERE / 'inspection-timeout-preservation-created.json').read_bytes())
preserved = Path(pointer['root'])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(preserved / 'seal.json') == pointer['seal_sha256']
for name, expected in json.loads((preserved / 'seal.json').read_bytes()).items():
    assert sha(preserved / name) == expected, name
source = (OLD / 'inspect_actual_evidence.py').read_text(encoding='utf8')
source = source.replace('from remote_control import remote, save, sha, ROOT3090, ROOT4090',
    "from remote_control import remote, save, sha\nROOT3090='/home/researcher/jev-defense-four-gpu-20261106/" + HERE.name + "'\nROOT4090='/data/researcher/jev-defense-four-gpu-20261106/" + HERE.name + "'")
assert source.count('timeout=55') == 2
source = source.replace('timeout=55', 'timeout=120')
before = 'primary = json.loads(output)'
assert source.count(before) == 1
source = source.replace(before, before + "\n    primary['observation_timeout_linked_retry']={'prior_preservation':" + repr(str(preserved)) + ", 'SSH_read_only_observation_timeout_seconds':120, 'all_original_SHA_checks_retained':True, 'new_model_GUI_calls':0}")
exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
