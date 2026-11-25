"""Reporter-only syntax repair; original source/failure and model data retained."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
old = HERE / 'audit_first_nine_sealed_once.py'
operation = HERE.parent / 'full-history-gui-development-20261109-23/operations/1794227553383656300-audit-frozen29-first9-request-wire-native-tensors-EOS-once'
out = HERE / ('prefix-audit-syntax-failure-preservation-' + str(time.time_ns())); out.mkdir()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
with (out / 'receipt.json').open('x', encoding='utf8') as stream:
    json.dump({'original_auditor': str(old), 'original_auditor_sha256': sha(old),
        'operation': str(operation), 'operation_files_SHA': {p.name: sha(p) for p in operation.iterdir() if p.is_file()},
        'failure': 'Missing whitespace between else and4096 in new read-only reporter source; remote Python rejected source before execution.',
        'actual_model_GPU_GUI_scorer_calls': 0, 'originals_unchanged': True}, stream, indent=2)
source = old.read_text(encoding='utf8')
assert source.count("operation=='actor'else4096") == 1
source = source.replace("operation=='actor'else4096", "operation=='actor' else 4096")
before = "output, operation = remote('3090', code,"
assert source.count(before) == 1
source = source.replace(before, "compile(code, 'new29-read-only-prefix-auditor', 'exec')\n    " + before)
exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
