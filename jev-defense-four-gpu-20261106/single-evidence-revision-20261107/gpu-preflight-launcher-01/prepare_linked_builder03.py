"""Linked metadata-only correction to source-reference count; no builder runs here."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
prior = HERE / 'prepare_linked_builder02.py'
failure = {'type': 'local_source_builder_preparation_assertion_failure',
           'source_path': str(prior), 'source_SHA256': hashlib.sha256(prior.read_bytes()).hexdigest(),
           'error': 'Expected 2 resource_gate source references but actual draft contains 3.',
           'failure_before_creating_any_linked_builder_or_output': True,
           'diagnostic_quote_attempt': 'One local python -c diagnostic had SyntaxError before any file or remote action.',
           'model_GPU_GUI_network_or_stage_submit_calls': 0,
           'repair': 'Only expected source-reference count 2 -> 3; original source retained.'}
with (HERE / 'builder-preparation-failure-02.json').open('x', encoding='utf-8') as stream:
    json.dump(failure, stream, ensure_ascii=False, indent=2)
code = prior.read_text(encoding='utf-8')
old = 'assert text.count("HERE / \'resource_gate.py\'") == 2'
new = 'assert text.count("HERE / \'resource_gate.py\'") == 3'
assert code.count(old) == 1
exec(compile(code.replace(old, new), str(prior), 'exec'), globals())
