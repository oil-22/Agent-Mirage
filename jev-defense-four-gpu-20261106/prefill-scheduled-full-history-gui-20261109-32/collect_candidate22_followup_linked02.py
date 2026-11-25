"""Metadata-only linked repair; reuse the already exported original frame."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
failure = HERE / 'followup22-export-failure-preservation-1794233467678236900'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name, expected in json.loads((failure / 'seal.json').read_bytes()).items():
    assert sha(failure / name) == expected, name
sourcepath = HERE / 'collect_candidate22_followup_once.py'
assert sha(sourcepath) == sha(failure / sourcepath.name)
source = sourcepath.read_text(encoding='utf8')
before = "output, operation = remote('4090', code, 'read-original-next-frame-candidate22-no-capture', timeout=55)"
assert source.count(before) == 1
source = source.replace(before,
    "operation = HERE.parent / 'full-history-gui-development-20261109-23/operations/1794233414211342100-read-original-next-frame-candidate22-no-capture'\n"
    "    preserved = HERE / 'followup22-export-failure-preservation-1794233467678236900' / operation.name\n"
    "    assert sha(operation / 'stdout.txt') == sha(preserved / 'stdout.txt')\n"
    "    assert json.loads((operation / 'receipt.json').read_bytes())['returncode'] == 0\n"
    "    output = (operation / 'stdout.txt').read_text(encoding='utf8')")
before = "images=[{k:v for k,v in im.items() if k in ['sha256','size','role','decoded']}for im in payload['view']['images']]"
assert source.count(before) == 1
source = source.replace(before,
    "import base64,struct\nimages=[]\nfor im in payload['view']['images']:\n"
    " raw=base64.b64decode(im['raw_base64'],validate=True)\n"
    " assert raw[:8]==b'\\x89PNG\\r\\n\\x1a\\n'\n"
    " images.append({'sha256':hashlib.sha256(raw).hexdigest(),'size':list(struct.unpack('>II',raw[16:24])),'role':im['role'],'original_wire_bytes_bound':True})")
before = "judge['remote_operation'] = str(operation2)"
assert source.count(before) == 1
source = source.replace(before, before + "\n    judge['linked_metadata_only_repair_of'] = str(HERE / 'followup22-export-failure-preservation-1794233467678236900')\n    judge['no_reexport_or_new_GUI_capture'] = True")
exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
