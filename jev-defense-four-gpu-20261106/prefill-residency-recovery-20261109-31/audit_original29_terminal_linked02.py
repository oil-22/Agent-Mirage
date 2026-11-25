"""Preserve the reporter assumption failure, then handle native text-only calls."""
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
old = HERE / 'audit_original29_terminal_once.py'
root = HERE / ('audit-schema-failure-preservation-' + str(time.time_ns()))
root.mkdir()
shutil.copyfile(old, root / 'source.py')
failure = {'type':'KeyError','key':'image_grid_thw',
           'cause':'Native relation judge0008 is text-only; complete shape inventory has no image tensor',
           'unchanged_model_GUI_or_validator':True,'new_experiment_calls':0}
(root / 'failure.json').write_bytes((json.dumps(failure,ensure_ascii=False,indent=2)+'\n').encode())
seal = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}
(root / 'seal.json').write_bytes((json.dumps(seal,indent=2)+'\n').encode())
source = old.read_text(encoding='utf8')
before = "'complete_images':prepared['image_grid_thw']['shape'][0],"
assert source.count(before) == 1
source = source.replace(before,"'complete_images':prepared.get('image_grid_thw', {'shape':[0]})['shape'][0],")
# The native contract, not a fabricated image tensor, determines zero-image calls.
before = "        row = {'request':folder.name,'operation':op,'decision_index':wire['decision_index'],"
assert source.count(before) == 1
source = source.replace(before,
    "        assert ('image_grid_thw' in prepared) == bool(payload['view']['images']) if op == 'judge' else True\n" + before)
exec(compile(source,str(Path(__file__).resolve()),'exec'),{'__name__':'__main__','__file__':str(Path(__file__).resolve())})
