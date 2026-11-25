"""Prepare the exact three-unstarted-trajectory collector. No network or models."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
PARENT = BASE / 'transport-preparation/ownership-proof-collector-linked-clock-1793979065673984500/collect_ownership_transport.py'
OUTPUT = BASE / 'transport-preparation/ownership-proof-collector-three-01'
PLAN = BASE / 'policy-preparation/image-observer-policy/gui-plan.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once_replace(source, before, after):
    assert source.count(before) == 1, 'Parent source boundary differs'
    return source.replace(before, after)


if __name__ == '__main__':
    plan = json.loads(PLAN.read_bytes())
    identifiers = [row['run_id'] for row in plan['queue'][1:]]
    assert len(identifiers) == 3
    raw = PARENT.read_text(encoding='utf8')
    raw = once_replace(raw, '/transport-online-01/private.token', '/transport-online-three-01/private.token')
    raw = once_replace(raw, "assert isinstance(state.get('runs'), dict) and len(state['runs']) == 4",
        "assert isinstance(state.get('runs'), dict) and list(state['runs']) == " + repr(identifiers))
    raw = once_replace(raw, "'four_unstarted_run_ids': runs", "'three_unstarted_run_ids': runs")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    target = OUTPUT / 'collect_ownership_transport.py'
    target.write_text(raw, encoding='utf8')
    module_spec = importlib.util.spec_from_file_location('three_ownership_collector', target)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    state = {'state': {'phase': 'ready', 'active': None, 'next_run_index': 0,
        'runs': {identifier: {'status': 'not_started', 'last_decision_index': 0,
        'calls': {'actor': 0, 'judge': 0, 'observe': 0}} for identifier in identifiers}}}
    assert module.fresh_state(state) == identifiers
    failures = []
    for kind in ('four_original', 'reordered', 'one_call', 'started'):
        value = copy.deepcopy(state)
        if kind == 'four_original':
            value['state']['runs'] = {plan['queue'][0]['run_id']: copy.deepcopy(next(iter(state['state']['runs'].values()))), **value['state']['runs']}
        elif kind == 'reordered':
            value['state']['runs'] = dict(reversed(list(value['state']['runs'].items())))
        elif kind == 'one_call':
            value['state']['runs'][identifiers[0]]['calls']['actor'] = 1
        else:
            value['state']['runs'][identifiers[0]]['status'] = 'active'
        try:
            module.fresh_state(value)
        except AssertionError:
            failures.append(kind)
        else:
            raise RuntimeError('Unsafe state admitted: ' + kind)
    receipt = {'stage': 'source_CPU_preparation_only', 'parent_sha256': sha(PARENT),
        'original_plan_sha256': sha(PLAN), 'collector_sha256': sha(target),
        'exact_three_run_ids': identifiers, 'changed_boundaries': ['new_remote_token_path',
        'exact_three_unstarted_ids', 'accurate_proof_key'], 'unchanged_max_age_seconds': 120,
        'three_clean_unstarted_state_passed': True, 'negative_states_rejected': failures,
        'network_model_GUI_calls': 0, 'launch_ready': False}
    (OUTPUT / 'preparation.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    (OUTPUT / 'stage-source.py').write_bytes(Path(__file__).read_bytes())
    mapping = {p.name: sha(p) for p in OUTPUT.iterdir() if p.is_file()}
    (OUTPUT / 'seal.json').write_text(json.dumps(mapping, indent=2), encoding='utf8')
    print(json.dumps({'source': str(target), 'sha256': sha(target), 'preparation_sha256': sha(OUTPUT / 'preparation.json'), 'network_model_GUI_calls': 0}))
