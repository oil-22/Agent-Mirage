"""Linked local reporter repair; do not reexecute any model request."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
original = HERE / 'audit_new_replies_03_once.py'
preserved = HERE / ('reply-audit03-local-failure-preservation-' + str(time.time_ns()))
preserved.mkdir()
(preserved / original.name).write_bytes(original.read_bytes())
failure = {
    'failed_original_auditor': str(original),
    'observed_failure': 'AssertionError: new-replies-02-audit-created.json',
    'cause': 'Local source-transform guard expected one pointer-name occurrence, but the original has both a once-only guard and the final pointer write.',
    'failed_before_remote_dispatch': True,
    'new_model_GUI_scorer_paid_calls': 0,
    'repair': 'Require exactly two occurrences for that pointer only; all other source replacements still require exactly one.',
}
(preserved / 'failure.json').write_text(json.dumps(failure, indent=2), encoding='utf8')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
(preserved / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in preserved.iterdir() if p.is_file()}, indent=2), encoding='utf8')
source = original.read_text(encoding='utf8')
before = 'assert source.count(before) == 1, before'
assert source.count(before) == 1
source = source.replace(before, "assert source.count(before) == (2 if before == 'new-replies-02-audit-created.json' else 1), before")
exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
