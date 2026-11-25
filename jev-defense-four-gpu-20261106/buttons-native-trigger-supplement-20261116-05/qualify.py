"""Qualify only new task/package bindings; reuse unchanged tested routing source.

Does not repeat completed CPU routing controls, generate model replies or use GUI.
"""
import ast
import json
import time
from pathlib import Path

from prepare import HERE, PARENT, VERSION, pointer, save, sha, verify


def main():
    assert not (HERE / 'CPU-routing-current.json').exists()
    prepared = json.loads((HERE / 'preparation-current.json').read_bytes())
    root = verify(prepared['root'])
    package = Path(prepared['package'])
    assert sha(root / 'seal.json') == prepared['seal_sha256']
    assert sha(package / 'manifest.json') == prepared['manifest_sha256']
    current = json.loads((package / 'manifest.json').read_bytes())
    previous = Path(json.loads((PARENT / 'preparation-current.json').read_bytes())['package'])
    old = json.loads((previous / 'manifest.json').read_bytes())
    parent_qualification = json.loads((PARENT / 'CPU-routing-current.json').read_bytes())
    parent_root = verify(parent_qualification['root'])
    assert sha(parent_root / 'seal.json') == parent_qualification['seal_sha256']
    assert parent_qualification['passed'] and parent_qualification['tests'] == 11
    assert parent_qualification['manifest_sha256'] == sha(previous / 'manifest.json')
    declaration = json.loads((HERE / 'source-plan.json').read_bytes())
    plan = json.loads((package / 'plan.json').read_bytes())
    assert plan['version'] == VERSION and plan['tasks'] == declaration['tasks']
    assert plan['expected_trajectories'] == current['trajectories'] == len(plan['queue']) == 2
    assert plan['queue'] == current['remaining_queue']
    assert [v['task_id'] for v in plan['queue']] == [114, 125]
    assert all(v['condition'] == 'buttons_only' and v['gate_enabled'] for v in plan['queue'])
    orchestration = (HERE / 'control.py').read_text('utf8')
    assert "h['expected']==2" in orchestration and "h['expected']==8" not in orchestration
    assert "'expected_trajectories':2" in orchestration
    changed = {'plan.json', 'analysis-plan.json', 'user-current-authorization.json',
               'prior-3090.json', 'prior-4090.json', 'continuation_guard.py'}
    same = []
    assert set(current['files']) == set(old['files'])
    for name, expected in current['files'].items():
        assert sha(package / name) == expected
        if name not in changed:
            assert sha(package / name) == sha(previous / name) == old['files'][name], name
            same.append(name)
        if name.endswith('.py'):
            ast.parse((package / name).read_text('utf8'))
    guard = (previous / 'continuation_guard.py').read_text('utf8')
    for before, after in [
        ("manifest['study'] == 'four-native-injection-presence-Flash-development-v1'", f"manifest['study'] == '{VERSION}'"),
        ("manifest['trajectories'] == 8", "manifest['trajectories'] == 2"),
        ("['expected'] == 12", "['expected'] == 8"),
    ]:
        assert guard.count(before) == 1
        guard = guard.replace(before, after)
    assert (package / 'continuation_guard.py').read_text('utf8') == guard
    group = pointer(PARENT, 'completed-group-audit-current.json')
    result = {
        'passed': True, 'manifest_sha256': sha(package / 'manifest.json'),
        'new_CPU_behavior_tests_executed': 0,
        'parent_11_completed_routing_tests_not_reexecuted': True,
        'parent_qualification_seal_sha256': sha(parent_root / 'seal.json'),
        'parent_full_group_audit_seal_sha256': sha(group / 'seal.json'),
        'identical_source_members': same,
        'new_task_source_queue_budget_and_guard_binding_checks': True,
        'GUI_helper_health_and_output_count_match_two_new_trajectories': True,
        'real_model_calls': 0, 'real_GUI_calls': 0,
        'static_binding_qualification_is_not_new_inference_or_defense_efficacy': True,
    }
    out = HERE / ('CPU-source-binding-' + str(time.time_ns()))
    out.mkdir()
    (out / 'source.py').write_bytes(Path(__file__).read_bytes())
    (out / 'control-source.py').write_bytes((HERE / 'control.py').read_bytes())
    save(out / 'result.json', result)
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    save(HERE / 'CPU-routing-current.json', {'root': str(out),
         'seal_sha256': sha(out / 'seal.json'), **result})
    print(json.dumps({'root': str(out), 'passed': True, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
