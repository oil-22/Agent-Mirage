"""Preserve a local audit path error; no experiment source or calls changed."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = HERE / ('audit-path-failure-preservation-' + str(time.time_ns()))
out.mkdir()
source = HERE / 'audit_terminal.py'
(out / 'audit_terminal.py').write_bytes(source.read_bytes())
failure = {'type': 'FileNotFoundError',
           'observed_message': 'runtime-package/image_evidence.py does not exist; the frozen module is release/image_evidence.py',
           'stage': 'local audit, comparison of frozen source paths; before per-call loop',
           'original_source_sha256': sha(source), 'new_model_GPU_GUI_scorer_paid_calls': 0,
           'original_terminal_files_modified': False,
           'correction': 'only the audit relative path; add sealed sequence prefix verification'}
(out / 'failure.json').write_text(json.dumps(failure, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
repaired = source.read_text(encoding='utf8')
old = "'stateless_boundary.py', 'image_evidence.py', 'bounded_schema.py', 'native_format_bridge.py'"
new = "'stateless_boundary.py', 'release/image_evidence.py', 'bounded_schema.py', 'native_format_bridge.py'"
assert repaired.count(old) == 1
repaired = repaired.replace(old, new)
old = "        prefix_ids = read(target / 'sequence_ids.json')\n        # The runtime additionally seals each selected prefix hash and choice set.\n        for token, step in zip(ids, mask['steps']):\n            assert token == step['selected_id'] and step['selected_allowed']"
new = "        sequence = read(target / 'sequence_ids.json')\n        assert len(sequence) == 1\n        sequence = sequence[0]\n        assert sequence[actual['input_tokens']:] == ids\n        input_ids = sequence[:actual['input_tokens']]\n        packed = b''.join(int(token).to_bytes(8, 'little', signed=True) for token in input_ids)\n        assert digest(packed) == prepared['input_ids']['sha256']\n        for index, (token, step) in enumerate(zip(ids, mask['steps'])):\n            assert token == step['selected_id'] and step['selected_allowed']\n            assert step['prefix_length'] == len(input_ids) + index\n            assert step['prefix_sha256'] == digest(canonical(input_ids + ids[:index]))"
assert repaired.count(old) == 1
repaired = repaired.replace(old, new)
linked = HERE / 'audit_terminal_linked02.py'
with linked.open('x', encoding='utf8') as stream:
    stream.write(repaired)
(out / 'linked-audit.json').write_text(json.dumps({'path': str(linked), 'sha256': sha(linked)}, indent=2) + '\n', encoding='utf8')
(out / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in out.iterdir() if p.is_file()}, indent=2) + '\n', encoding='utf8')
print(json.dumps({'preserved': str(out), 'seal_sha256': sha(out / 'seal.json'), 'linked': str(linked)}))
