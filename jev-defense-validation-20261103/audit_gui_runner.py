"""Check the new entry point preserves the native trajectory's critical functions."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

base = Path(__file__).resolve().parent
release = base / 'release'
sys.path.insert(0, str(release))
from validation_launch_contract import validate_launch_inputs

parent = ast.parse((release / 'run_vwa_pilot.py').read_text(encoding='utf-8'))
current = ast.parse((release / 'run_jev_vwa_validation.py').read_text(encoding='utf-8'))


def functions(tree):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


before, after = functions(parent), functions(current)
same = ['save', 'block', 'detail', 'goto', 'public', 'actor', 'parser', 'recapture']
assert all(before[name] == after[name] for name in same)
exception_block = ast.get_source_segment((release / 'run_jev_vwa_validation.py').read_text(encoding='utf-8'), current.body[-1])
assert 'if OWNED_ROOT is not None:' in exception_block
assert 'exist_ok=True' not in exception_block
# A false staging receipt must be rejected before token, model, runtime or GUI access.
try:
    validate_launch_inputs(SimpleNamespace(readiness=base / 'launch-readiness.json'))
except RuntimeError as error:
    assert 'prerequisites are incomplete' in str(error)
else:
    raise AssertionError('Staging gate allowed launch')
plan = json.loads((base / 'gui-plan.proposed.json').read_bytes())
assert plan['limits']['wait_seconds'] == [0.5, 1.0]
# Bind the original delay directly to the saved historical plan-construction call.
rows = json.loads((base.parent / 'defense-resume-20261102/history-tool-calls.json').read_bytes())
binding = next(row for row in rows if row['timestamp'] == '2026-10-23T13:01:39.360Z')
text = binding['payload'].get('input', binding['payload'].get('arguments', ''))
assert 'wait_seconds=[0.5,1.0]' in text
result = {'critical_native_functions_ast_identical': same,
          'preexisting_terminal_root_never_written_by_outer_failure_handler': True,
          'staged_false_gate_rejected_before_token_or_model_or_GUI_access': True,
          'original_recovery_wait_seconds': [0.5, 1.0],
          'historical_plan_construction_timestamp': binding['timestamp'],
          'historical_plan_construction_sha256': hashlib.sha256(text.encode()).hexdigest(),
          'main_model_calls': 0, 'auxiliary_model_calls': 0, 'task_actions': 0,
          'not_full_runner_execution_or_semantic_validation': True}
(base / 'gui-runner-static-audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
old = (release / 'run_vwa_pilot.py').read_text(encoding='utf-8')
new = (release / 'run_jev_vwa_validation.py').read_text(encoding='utf-8')
(base / 'gui-runner-diff.patch').write_text(''.join(difflib.unified_diff(
    old.splitlines(True), new.splitlines(True), fromfile='original-run_vwa_pilot.py',
    tofile='run_jev_vwa_validation.py')), encoding='utf-8')
staging = json.loads((base / 'gui-runner-staging.json').read_bytes())
staging['new_runner_sha256'] = hashlib.sha256((release / 'run_jev_vwa_validation.py').read_bytes()).hexdigest()
staging['preexisting_root_failure_handler_preserves_terminal'] = True
(base / 'gui-runner-staging.json').write_text(json.dumps(staging, indent=2), encoding='utf-8')
print(json.dumps(result))
