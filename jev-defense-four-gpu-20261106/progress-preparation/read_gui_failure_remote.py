import hashlib
import json
from pathlib import Path
base = Path('/data/researcher/jev-defense-four-gpu-20261106')
paths = [base / 'gui-batch-image-observer-01/uncaught-failure.json',
    base / 'gui-outer-control-01/wrapper-failure.json',
    base / 'gui-outer-control-01/finalization.json']
rows = {}
for path in paths:
    if path.exists():
        value = json.loads(path.read_bytes())
        rows[str(path)] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            **{key: value[key] for key in ('traceback', 'exit_code', 'execution_completed',
                'all_four_complete', 'phase', 'no_automatic_retry') if key in value}}
print(json.dumps({'failures': rows, 'model_HTTP_GUI_calls': 0, 'files_written': 0}))
