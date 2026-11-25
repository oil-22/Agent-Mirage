"""Admit exactly the 31 unstarted entries of the unchanged original32 plan."""
import copy
import hashlib
import json
from pathlib import Path

from terminal_outcome_classification import classify_run_termination


HERE = Path(__file__).resolve().parent
ORIGINAL = 'fullhistory23-T000-clean-noaux'
ORIGINAL_MANIFEST = 'c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1'


def remaining_queue(plan):
    source = json.loads((HERE / 'predecessor.json').read_bytes())
    assert source['original_manifest_sha256'] == ORIGINAL_MANIFEST
    assert source['excluded_run_ids'] == [ORIGINAL]
    assert hashlib.sha256((HERE / 'plan.json').read_bytes()).hexdigest() == source['unchanged_full_plan_sha256']
    assert plan == json.loads((HERE / 'plan.json').read_bytes())
    raw = (HERE / 'predecessor/original-technical-failure.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == source['original_terminal_sha256']
    terminal = json.loads(raw)
    assert terminal['run'] == plan['queue'][0] and terminal['run']['run_id'] == ORIGINAL
    assert terminal['technical_status'] == 'verifier_failure' and terminal['semantic_mirage'] is None
    assert terminal['scoring_status'] == 'complete' and terminal['official_reward'] == 0.0
    assert (terminal['actor_calls'], terminal['verifier_calls'], terminal['auxiliary_calls']) == (38, 140, 0)
    revised = classify_run_termination(terminal['outcome'], terminal['blocked_reason'],
        terminal['scoring_status'], terminal['verifier_calls'], 140)
    assert revised == source['replayed_classification']
    assert revised['local_verifier_budget_exhausted'] and revised['new_calls_or_retries_granted'] == 0
    assert len(plan['queue']) == 32 and len({q['run_id'] for q in plan['queue']}) == 32
    queue = copy.deepcopy(plan['queue'][1:])
    assert len(queue) == 31 and queue[0]['run_id'] == 'fullhistory23-T000-clean-aux'
    assert all(q['run_id'] != ORIGINAL and q['arm'] == 'joint' for q in queue)
    return queue


def completed_request_ids():
    source = json.loads((HERE / 'predecessor.json').read_bytes())
    values = source['disallowed_completed_model_request_ids']
    assert len(values) == 111 and len(set(values)) == 111
    assert all(isinstance(value, str) and len(value) == 32 for value in values)
    return set(values)
