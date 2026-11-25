"""Preserve the failed reporter; bind native text-only versus image forwards."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
original = HERE / 'audit_new_replies_02_once.py'
operation = HERE.parent / 'full-history-gui-development-20261109-23/operations/1794230925654456000-audit-only-new32-replies2to4-no-repeat-original-prefix-once'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
preserved = HERE / ('reply-audit02-failure-preservation-' + str(time.time_ns()))
preserved.mkdir()
(preserved / original.name).write_bytes(original.read_bytes())
for p in operation.iterdir():
    if p.is_file():
        (preserved / ('operation-' + p.name)).write_bytes(p.read_bytes())
failure = {
    'failed_original_auditor': str(original), 'auditor_sha256': sha(original),
    'operation': str(operation), 'operation_files_SHA256': {p.name: sha(p) for p in operation.iterdir() if p.is_file()},
    'failure': 'Reporter required all69groups even for native0image relation inference. Native text-only generation does not call model.visual; full69weight restoration still required.',
    'new_model_GUI_scorer_paid_calls': 0, 'original_runtime_inputs_generation_outputs_and_validator_unchanged': True}
(preserved / 'failure.json').write_text(json.dumps(failure, indent=2), encoding='utf8')
(preserved / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in preserved.iterdir() if p.is_file()}, indent=2), encoding='utf8')
body = original.read_text(encoding='utf8')
before = "assert len(item['visited_groups'])==69 and set(item['visited_groups'])==set(item['same_native_execution_device_map'])"
assert body.count(before) == 1
body = body.replace(before, "expected=set(item['same_native_execution_device_map'])\n if row['complete_supplied_images']==0:expected.remove('model.visual')\n assert set(item['visited_groups'])==expected and len(item['visited_groups'])==len(expected)\n row['actual_native_prefill_group_count']=len(expected)\n row['native_visual_forward_observed']='model.visual'in item['visited_groups']")
exec(compile(body, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
