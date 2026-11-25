"""Admit only the 28 never-started entries of the unchanged original32 plan."""
import copy
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PLAN_SHA256 = '51e35415fc7df2d0309e67f117310de8ecffd59b51ece6bcfdda176e5ae4f98c'
FINISHED = [
    'fullhistory23-T000-clean-noaux',
    'fullhistory23-T000-clean-aux',
    'fullhistory23-T000-stale_replace-aux',
    'fullhistory23-T000-stale_replace-noaux',
]


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source():
    source = json.loads((HERE / 'continuation.json').read_bytes())
    assert source['excluded_run_ids'] == FINISHED
    assert source['unchanged_full32_plan_sha256'] == PLAN_SHA256
    assert source['remaining_tracks'] == 28
    assert source['initial_transport_counts'] == {'actor': 0, 'judge': 0, 'evidence': 0}
    assert _sha(HERE / 'plan.json') == PLAN_SHA256
    plan = json.loads((HERE / 'plan.json').read_bytes())
    assert len(plan['queue']) == len({x['run_id'] for x in plan['queue']}) == 32
    assert [x['run_id'] for x in plan['queue'][:4]] == FINISHED
    assert [x['run_id'] for x in source['terminal_copies']] == FINISHED
    for row in source['terminal_copies']:
        path = HERE / row['copy']
        assert path.resolve().is_relative_to(HERE.resolve())
        assert _sha(path) == row['sha256']
        terminal = json.loads(path.read_bytes())
        item = next(x for x in plan['queue'] if x['run_id'] == row['run_id'])
        assert terminal['run'] == item
        assert terminal['scoring_status'] == 'complete'
    return source, plan


def remaining_queue(plan):
    source, frozen = _source()
    assert plan == frozen, 'Full original plan, inputs and budgets must remain unchanged'
    queue = [x for x in frozen['queue'] if x['run_id'] not in FINISHED]
    assert len(queue) == 28
    assert [x['run_id'] for x in queue] == source['remaining_run_ids']
    assert all(x['arm'] == 'joint' for x in queue)
    return copy.deepcopy(queue)


def completed_request_ids():
    source, _ = _source()
    path = HERE / 'completed-request-exclusions.json'
    assert _sha(path) == source['completed_request_exclusions_sha256']
    values = json.loads(path.read_bytes())['unique_request_ids']
    assert len(values) == len(set(values)) == 437
    assert all(isinstance(x, str) and len(x) == 32 and
               all(c in '0123456789abcdef' for c in x) for x in values)
    return set(values)
