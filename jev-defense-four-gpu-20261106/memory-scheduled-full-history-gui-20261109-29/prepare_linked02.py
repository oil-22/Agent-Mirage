"""New linked package; retain the failed original package and all its sources."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
pointer = json.loads((HERE / 'preparation-failure-preserved.json').read_bytes())
failure = Path(pointer['preservation'])
assert hashlib.sha256((failure / 'seal.json').read_bytes()).hexdigest() == pointer['seal_sha256']
assert (failure / 'prepare_once.py').read_bytes() == (HERE / 'prepare_once.py').read_bytes()
source = (failure / 'prepare_once.py').read_text(encoding='utf8')
assert source.count("OUT = HERE / 'runtime-package'") == 1
source = source.replace("OUT = HERE / 'runtime-package'", "OUT = HERE / 'runtime-package-linked02'")
before = "for name in old_manifest['files']:\n        target = OUT / name"
assert source.count(before) == 1
source = source.replace(before, "for name in old_manifest['files']:\n        if name == 'admission.json':\n            continue\n        target = OUT / name")
exec(compile(source, str(HERE / 'prepare_linked02.py'), 'exec'), {'__name__': '__main__', '__file__': str(HERE / 'prepare_linked02.py')})
